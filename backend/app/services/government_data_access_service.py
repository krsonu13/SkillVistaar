from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorization,
    GovernmentDataAccessAuthorizationStatus,
    GovernmentDataAccessLevel,
)
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.government_jurisdiction_service import (
    GovernmentJurisdictionError,
    GovernmentJurisdictionNotFoundError,
    GovernmentJurisdictionService,
)


class GovernmentDataAccessError(Exception):
    """Base error for government data access operations."""


class GovernmentDataAccessDeniedError(GovernmentDataAccessError):
    """Raised when a user is not authorized."""


class GovernmentDataAccessNotFoundError(GovernmentDataAccessError):
    """Raised when an authorization cannot be found."""


class GovernmentDataAccessValidationError(GovernmentDataAccessError):
    """Raised when supplied data is invalid."""


class GovernmentDataAccessService:
    """
    Central service for government-data access authorization.

    Authorization is intentionally split into two layers:

    1. Government RBAC
       Determines whether the caller may perform the operation.

    2. Government jurisdiction
       Determines which government units the caller may operate on.

    Data-access level then determines the strength of access:

        VIEW < ANALYZE < MANAGE

    PostgreSQL remains the system of record.

    Administrative changes are recorded in the audit log.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.jurisdiction_service = GovernmentJurisdictionService(db)

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    async def _validate_government_unit(
        self,
        government_unit_id: UUID,
    ) -> None:
        """Verify that a government unit exists."""

        try:
            await self.jurisdiction_service.get_unit(
                government_unit_id
            )
        except GovernmentJurisdictionNotFoundError as exc:
            raise GovernmentDataAccessValidationError(
                "Government unit not found."
            ) from exc
        except GovernmentJurisdictionError as exc:
            raise GovernmentDataAccessValidationError(
                str(exc)
            ) from exc

    async def _require_unit_access(
        self,
        user_id: UUID,
        government_unit_id: UUID,
    ) -> None:
        """
        Require the caller to have jurisdictional access to a unit.
        """

        try:
            allowed = await self.jurisdiction_service.can_access_unit(
                user_id=user_id,
                target_unit_id=government_unit_id,
            )
        except GovernmentJurisdictionError as exc:
            raise GovernmentDataAccessDeniedError(
                str(exc)
            ) from exc

        if not allowed:
            raise GovernmentDataAccessDeniedError(
                "You do not have jurisdictional access "
                "to this government unit."
            )

    async def _get_target_user(
        self,
        user_id: UUID,
    ) -> User:
        """Verify that the target user exists and is active."""

        result = await self.db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            raise GovernmentDataAccessValidationError(
                "Target user not found."
            )

        if not user.is_active:
            raise GovernmentDataAccessValidationError(
                "Government data access cannot be granted "
                "to an inactive user."
            )

        if user.is_suspended:
            raise GovernmentDataAccessValidationError(
                "Government data access cannot be granted "
                "to a suspended user."
            )

        return user

    @staticmethod
    def _validate_access_level(
        access_level: GovernmentDataAccessLevel | str,
    ) -> GovernmentDataAccessLevel:
        """Validate an access level."""

        try:
            return GovernmentDataAccessLevel(access_level)
        except ValueError as exc:
            raise GovernmentDataAccessValidationError(
                "Invalid government data access level."
            ) from exc

    @staticmethod
    def _validate_status(
        status_value: (
            GovernmentDataAccessAuthorizationStatus | str
        ),
    ) -> GovernmentDataAccessAuthorizationStatus:
        """Validate an authorization status."""

        try:
            return GovernmentDataAccessAuthorizationStatus(
                status_value
            )
        except ValueError as exc:
            raise GovernmentDataAccessValidationError(
                "Invalid government data access status."
            ) from exc

    @staticmethod
    def _audit_action_for_status(
        status_value: GovernmentDataAccessAuthorizationStatus,
    ) -> tuple[str, str] | None:
        """
        Return the audit action and description for an administrative
        authorization status transition.

        EXPIRED is intentionally excluded because expiry can happen
        automatically without a human actor.
        """

        mapping = {
            GovernmentDataAccessAuthorizationStatus.ACTIVE: (
                "RESTORE",
                "Government data access authorization restored.",
            ),
            GovernmentDataAccessAuthorizationStatus.SUSPENDED: (
                "SUSPEND",
                "Government data access authorization suspended.",
            ),
            GovernmentDataAccessAuthorizationStatus.REVOKED: (
                "REVOKE_ACCESS",
                "Government data access authorization revoked.",
            ),
        }

        return mapping.get(status_value)

    async def _record_audit(
        self,
        *,
        authorization: GovernmentDataAccessAuthorization,
        actor_user_id: UUID,
        action: str,
        description: str,
        previous_status: str | None = None,
    ) -> None:
        """
        Record an administrative government-data access action.

        This is executed before the surrounding transaction commits.
        Therefore the authorization change and its audit record are
        persisted atomically.
        """

        metadata = {
            "user_id": str(authorization.user_id),
            "government_unit_id": str(
                authorization.government_unit_id
            ),
            "access_level": str(
                authorization.access_level
            ),
            "status": str(
                authorization.status
            ),
            "scope": authorization.scope,
        }

        if previous_status is not None:
            metadata["previous_status"] = previous_status

        await AuditLogService.record(
            self.db,
            actor_user_id=actor_user_id,
            action=action,
            resource_type="GovernmentDataAccessAuthorization",
            resource_id=authorization.id,
            description=description,
            metadata=metadata,
        )

    async def _expire_if_needed(
        self,
        authorization: GovernmentDataAccessAuthorization,
    ) -> bool:
        """
        Mark an expired active authorization as EXPIRED.

        Returns True when the authorization was changed.

        Automatic expiry is not written to the audit log because
        AuditLog requires an actor user and there is no human actor
        for an automatic expiry event.
        """

        now = datetime.now(timezone.utc)

        if (
            authorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE
            and authorization.expires_at is not None
            and authorization.expires_at <= now
        ):
            authorization.status = (
                GovernmentDataAccessAuthorizationStatus.EXPIRED
            )
            return True

        return False

    # ========================================================================
    # GET
    # ========================================================================

    async def get_authorization(
        self,
        authorization_id: UUID,
        requesting_user_id: UUID | None = None,
    ) -> GovernmentDataAccessAuthorization:
        """
        Retrieve an authorization.

        When requesting_user_id is supplied, jurisdiction is enforced.
        """

        result = await self.db.execute(
            select(
                GovernmentDataAccessAuthorization
            ).where(
                GovernmentDataAccessAuthorization.id
                == authorization_id
            )
        )

        authorization = result.scalar_one_or_none()

        if authorization is None:
            raise GovernmentDataAccessNotFoundError(
                "Government data access authorization not found."
            )

        changed = await self._expire_if_needed(
            authorization
        )

        if changed:
            await self.db.commit()
            await self.db.refresh(authorization)

        if requesting_user_id is not None:
            await self._require_unit_access(
                requesting_user_id,
                authorization.government_unit_id,
            )

        return authorization

    # ========================================================================
    # LIST
    # ========================================================================

    async def list_authorizations(
        self,
        requesting_user_id: UUID,
        user_id: UUID | None = None,
        government_unit_id: UUID | None = None,
        include_inactive: bool = False,
    ) -> list[GovernmentDataAccessAuthorization]:
        """
        List authorizations visible to the requesting user.

        If a government unit is supplied, the caller must have
        jurisdictional access to that unit.

        If no unit is supplied, results are restricted to the caller's
        accessible government hierarchy.

        This prevents cross-jurisdiction authorization leakage.
        """

        accessible_unit_ids = (
            await self.jurisdiction_service.get_accessible_unit_ids(
                requesting_user_id
            )
        )

        if government_unit_id is not None:
            if government_unit_id not in accessible_unit_ids:
                raise GovernmentDataAccessDeniedError(
                    "You do not have jurisdictional access "
                    "to this government unit."
                )

            allowed_unit_ids = [government_unit_id]

        else:
            allowed_unit_ids = accessible_unit_ids

        if not allowed_unit_ids:
            return []

        query = select(
            GovernmentDataAccessAuthorization
        ).where(
            GovernmentDataAccessAuthorization.government_unit_id.in_(
                allowed_unit_ids
            )
        )

        if user_id is not None:
            query = query.where(
                GovernmentDataAccessAuthorization.user_id
                == user_id
            )

        if not include_inactive:
            query = query.where(
                GovernmentDataAccessAuthorization.status
                == GovernmentDataAccessAuthorizationStatus.ACTIVE
            )

        query = query.order_by(
            GovernmentDataAccessAuthorization.created_at.desc()
        )

        result = await self.db.execute(query)

        authorizations = list(
            result.scalars().all()
        )

        changed = False

        for authorization in authorizations:
            if await self._expire_if_needed(
                authorization
            ):
                changed = True

        if changed:
            await self.db.commit()

        if not include_inactive:
            authorizations = [
                authorization
                for authorization in authorizations
                if authorization.status
                == GovernmentDataAccessAuthorizationStatus.ACTIVE
            ]

        return authorizations

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create_authorization(
        self,
        granted_by_user_id: UUID,
        data,
    ) -> GovernmentDataAccessAuthorization:
        """
        Grant government-data access to another user.

        The grantor cannot grant access to themselves.
        """

        if data.user_id == granted_by_user_id:
            raise GovernmentDataAccessValidationError(
                "A user cannot grant government data access "
                "to themselves."
            )

        await self._get_target_user(data.user_id)

        await self._validate_government_unit(
            data.government_unit_id
        )

        await self._require_unit_access(
            granted_by_user_id,
            data.government_unit_id,
        )

        access_level = self._validate_access_level(
            data.access_level
        )

        now = datetime.now(timezone.utc)

        if (
            data.expires_at is not None
            and data.expires_at <= now
        ):
            raise GovernmentDataAccessValidationError(
                "Authorization expiry must be in the future."
            )

        duplicate_query = select(
            GovernmentDataAccessAuthorization
        ).where(
            GovernmentDataAccessAuthorization.user_id
            == data.user_id,
            GovernmentDataAccessAuthorization.government_unit_id
            == data.government_unit_id,
            GovernmentDataAccessAuthorization.access_level
            == access_level,
            GovernmentDataAccessAuthorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE,
        )

        result = await self.db.execute(
            duplicate_query
        )

        existing = result.scalar_one_or_none()

        if existing is not None:
            raise GovernmentDataAccessValidationError(
                "An active authorization already exists "
                "for this user, government unit and access level."
            )

        authorization = (
            GovernmentDataAccessAuthorization(
                user_id=data.user_id,
                government_unit_id=data.government_unit_id,
                access_level=access_level,
                status=(
                    GovernmentDataAccessAuthorizationStatus.ACTIVE
                ),
                scope=data.scope,
                granted_by_user_id=granted_by_user_id,
                expires_at=data.expires_at,
                reason=data.reason,
            )
        )

        self.db.add(authorization)

        try:
            await self.db.flush()

            await self._record_audit(
                authorization=authorization,
                actor_user_id=granted_by_user_id,
                action="GRANT_ACCESS",
                description=(
                    "Government data access authorization granted."
                ),
                previous_status=None,
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(authorization)

        return authorization

    # ========================================================================
    # STATUS
    # ========================================================================

    async def update_status(
        self,
        authorization_id: UUID,
        status_value: (
            GovernmentDataAccessAuthorizationStatus | str
        ),
        requesting_user_id: UUID,
    ) -> GovernmentDataAccessAuthorization:
        """
        Update authorization status after jurisdiction validation.

        Administrative lifecycle changes are audited.
        """

        authorization = await self.get_authorization(
            authorization_id=authorization_id
        )

        await self._require_unit_access(
            requesting_user_id,
            authorization.government_unit_id,
        )

        new_status = self._validate_status(
            status_value
        )

        old_status = authorization.status

        if old_status == new_status:
            raise GovernmentDataAccessValidationError(
                f"Authorization is already in {new_status.value} status."
            )

        if (
            new_status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE
        ):
            if (
                authorization.expires_at is not None
                and authorization.expires_at
                <= datetime.now(timezone.utc)
            ):
                raise GovernmentDataAccessValidationError(
                    "An expired authorization cannot be reactivated. "
                    "Create a new authorization instead."
                )

        if (
            new_status
            == GovernmentDataAccessAuthorizationStatus.EXPIRED
        ):
            raise GovernmentDataAccessValidationError(
                "Authorization expiry is handled automatically."
            )

        audit_details = self._audit_action_for_status(
            new_status
        )

        authorization.status = new_status

        try:
            if audit_details is not None:
                action, description = audit_details

                await self._record_audit(
                    authorization=authorization,
                    actor_user_id=requesting_user_id,
                    action=action,
                    description=description,
                    previous_status=(
                        old_status.value
                        if hasattr(old_status, "value")
                        else str(old_status)
                    ),
                )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(authorization)

        return authorization

    # ========================================================================
    # SUSPEND
    # ========================================================================

    async def suspend_authorization(
        self,
        authorization_id: UUID,
        requesting_user_id: UUID,
    ) -> GovernmentDataAccessAuthorization:
        """Suspend an authorization."""

        return await self.update_status(
            authorization_id=authorization_id,
            status_value=(
                GovernmentDataAccessAuthorizationStatus.SUSPENDED
            ),
            requesting_user_id=requesting_user_id,
        )

    # ========================================================================
    # REVOKE
    # ========================================================================

    async def revoke_authorization(
        self,
        authorization_id: UUID,
        requesting_user_id: UUID,
    ) -> GovernmentDataAccessAuthorization:
        """Revoke an authorization."""

        return await self.update_status(
            authorization_id=authorization_id,
            status_value=(
                GovernmentDataAccessAuthorizationStatus.REVOKED
            ),
            requesting_user_id=requesting_user_id,
        )

    # ========================================================================
    # REACTIVATE
    # ========================================================================

    async def reactivate_authorization(
        self,
        authorization_id: UUID,
        requesting_user_id: UUID,
    ) -> GovernmentDataAccessAuthorization:
        """
        Reactivate a suspended authorization.

        Expired and revoked authorizations require a new grant.
        """

        authorization = await self.get_authorization(
            authorization_id=authorization_id
        )

        await self._require_unit_access(
            requesting_user_id,
            authorization.government_unit_id,
        )

        if (
            authorization.status
            != GovernmentDataAccessAuthorizationStatus.SUSPENDED
        ):
            raise GovernmentDataAccessValidationError(
                "Only suspended authorizations can be reactivated."
            )

        if (
            authorization.expires_at is not None
            and authorization.expires_at
            <= datetime.now(timezone.utc)
        ):
            authorization.status = (
                GovernmentDataAccessAuthorizationStatus.EXPIRED
            )

            await self.db.commit()

            raise GovernmentDataAccessValidationError(
                "This authorization has expired and cannot be "
                "reactivated."
            )

        authorization.status = (
            GovernmentDataAccessAuthorizationStatus.ACTIVE
        )

        try:
            await self._record_audit(
                authorization=authorization,
                actor_user_id=requesting_user_id,
                action="RESTORE",
                description=(
                    "Government data access authorization restored."
                ),
                previous_status=(
                    GovernmentDataAccessAuthorizationStatus.SUSPENDED.value
                ),
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(authorization)

        return authorization

    # ========================================================================
    # ACCESS LEVEL
    # ========================================================================

    @staticmethod
    def access_level_allows(
        granted_level: GovernmentDataAccessLevel | str,
        required_level: GovernmentDataAccessLevel | str,
    ) -> bool:
        """
        Determine whether a granted level satisfies a required level.
        """

        try:
            granted = GovernmentDataAccessLevel(
                granted_level
            )
            required = GovernmentDataAccessLevel(
                required_level
            )
        except ValueError:
            return False

        ranking = {
            GovernmentDataAccessLevel.VIEW: 1,
            GovernmentDataAccessLevel.ANALYZE: 2,
            GovernmentDataAccessLevel.MANAGE: 3,
        }

        return (
            ranking[granted]
            >= ranking[required]
        )

    # ========================================================================
    # CAN ACCESS
    # ========================================================================

    async def can_access(
        self,
        user_id: UUID,
        target_unit_id: UUID,
        required_level: (
            GovernmentDataAccessLevel | str
        ) = GovernmentDataAccessLevel.VIEW,
    ) -> bool:
        """
        Check whether a user has sufficient government-data access.

        Both conditions must pass:

        1. The user has jurisdictional access.
        2. The user has an active authorization for the target unit
           with sufficient access level.
        """

        try:
            await self._require_unit_access(
                user_id,
                target_unit_id,
            )
        except GovernmentDataAccessDeniedError:
            return False

        required = self._validate_access_level(
            required_level
        )

        now = datetime.now(timezone.utc)

        query = select(
            GovernmentDataAccessAuthorization
        ).where(
            GovernmentDataAccessAuthorization.user_id
            == user_id,
            GovernmentDataAccessAuthorization.government_unit_id
            == target_unit_id,
            GovernmentDataAccessAuthorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE,
        )

        result = await self.db.execute(query)

        authorizations = list(
            result.scalars().all()
        )

        changed = False

        for authorization in authorizations:
            if (
                authorization.expires_at is not None
                and authorization.expires_at <= now
            ):
                authorization.status = (
                    GovernmentDataAccessAuthorizationStatus.EXPIRED
                )
                changed = True
                continue

            if self.access_level_allows(
                authorization.access_level,
                required,
            ):
                if changed:
                    await self.db.commit()

                return True

        if changed:
            await self.db.commit()

        return False

    # ========================================================================
    # REQUIRE ACCESS
    # ========================================================================

    async def require_access(
        self,
        user_id: UUID,
        target_unit_id: UUID,
        required_level: (
            GovernmentDataAccessLevel | str
        ) = GovernmentDataAccessLevel.VIEW,
    ) -> GovernmentDataAccessAuthorization:
        """
        Require sufficient government-data access.

        Returns the matching authorization.
        """

        await self._require_unit_access(
            user_id,
            target_unit_id,
        )

        required = self._validate_access_level(
            required_level
        )

        now = datetime.now(timezone.utc)

        query = select(
            GovernmentDataAccessAuthorization
        ).where(
            GovernmentDataAccessAuthorization.user_id
            == user_id,
            GovernmentDataAccessAuthorization.government_unit_id
            == target_unit_id,
            GovernmentDataAccessAuthorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE,
        )

        result = await self.db.execute(query)

        authorizations = list(
            result.scalars().all()
        )

        changed = False

        for authorization in authorizations:
            if (
                authorization.expires_at is not None
                and authorization.expires_at <= now
            ):
                authorization.status = (
                    GovernmentDataAccessAuthorizationStatus.EXPIRED
                )
                changed = True
                continue

            if self.access_level_allows(
                authorization.access_level,
                required,
            ):
                if changed:
                    await self.db.commit()

                return authorization

        if changed:
            await self.db.commit()

        raise GovernmentDataAccessDeniedError(
            "You do not have sufficient government-data "
            "access for this government unit."
        )