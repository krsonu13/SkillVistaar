from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import SUPER_ADMIN
from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorization,
    GovernmentDataAccessAuthorizationStatus,
)
from app.models.government_unit import GovernmentUnit
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.models.verifier_authorization import VerifierAuthorization


class GovernmentJurisdictionError(Exception):
    """Base error for government jurisdiction operations."""


class GovernmentJurisdictionNotFoundError(
    GovernmentJurisdictionError
):
    """Raised when a government unit cannot be found."""


class GovernmentJurisdictionAccessDeniedError(
    GovernmentJurisdictionError
):
    """Raised when a user cannot access a government unit."""


class GovernmentJurisdictionService:
    """
    Service for recursive government-jurisdiction access.

    Government hierarchy is data-driven:

        Central
          └── State
                └── District
                      └── Local

    No Indian state/district hierarchy is hard-coded.

    Normal government users receive access through their
    authorized government jurisdictions.

    SUPER_ADMIN is the platform-level exception and has
    global government jurisdiction access.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_unit(
        self,
        government_unit_id: UUID,
    ) -> GovernmentUnit:
        result = await self.db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == government_unit_id
            )
        )

        unit = result.scalar_one_or_none()

        if unit is None:
            raise GovernmentJurisdictionNotFoundError(
                "Government unit not found."
            )

        return unit

    async def is_super_admin(
        self,
        user_id: UUID,
    ) -> bool:
        result = await self.db.execute(
            select(User.id)
            .join(
                UserRole,
                UserRole.user_id == User.id,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .where(
                User.id == user_id,
                User.is_active.is_(True),
                User.is_suspended.is_(False),
                UserRole.revoked_at.is_(None),
                Role.code == SUPER_ADMIN,
                Role.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none() is not None

    async def is_descendant_or_same(
        self,
        ancestor_unit_id: UUID,
        target_unit_id: UUID,
    ) -> bool:
        """
        Return True when target_unit_id is the same as,
        or a descendant of, ancestor_unit_id.
        """

        if ancestor_unit_id == target_unit_id:
            return True

        current_id: UUID | None = target_unit_id
        visited: set[UUID] = set()

        while current_id is not None:
            if current_id in visited:
                raise GovernmentJurisdictionError(
                    "Circular government-unit hierarchy detected."
                )

            visited.add(current_id)

            unit = await self.get_unit(current_id)

            if unit.parent_id is None:
                return False

            if unit.parent_id == ancestor_unit_id:
                return True

            current_id = unit.parent_id

        return False

    async def get_descendant_unit_ids(
        self,
        government_unit_id: UUID,
    ) -> list[UUID]:
        """
        Return the requested government unit and all
        active/inactive descendants.

        Filtering for active units is performed by callers
        where appropriate.
        """

        await self.get_unit(government_unit_id)

        result = await self.db.execute(
            select(
                GovernmentUnit.id,
                GovernmentUnit.parent_id,
            )
        )

        rows = result.all()

        children: dict[UUID, list[UUID]] = {}

        for unit_id, parent_id in rows:
            if parent_id is not None:
                children.setdefault(
                    parent_id,
                    [],
                ).append(unit_id)

        descendants: list[UUID] = [
            government_unit_id
        ]

        visited: set[UUID] = {
            government_unit_id
        }

        queue: list[UUID] = [
            government_unit_id
        ]

        while queue:
            parent_id = queue.pop(0)

            for child_id in children.get(
                parent_id,
                [],
            ):
                if child_id in visited:
                    continue

                visited.add(child_id)
                descendants.append(child_id)
                queue.append(child_id)

        return descendants

    async def get_authorized_units(
        self,
        user_id: UUID,
    ) -> list[GovernmentUnit]:
        """
        Return government units directly associated with
        the user's authority.

        SUPER_ADMIN receives all active government units.

        Normal users can receive authority through:
        1. Explicit government data-access authorization.
        2. Verifier authorization.
        3. An approved government verification application.

        This method establishes jurisdiction only.
        It does not itself grant VIEW/ANALYZE/MANAGE permissions.
        """

        if await self.is_super_admin(user_id):
            result = await self.db.execute(
                select(GovernmentUnit)
                .where(
                    GovernmentUnit.is_active.is_(True)
                )
                .order_by(
                    GovernmentUnit.level,
                    GovernmentUnit.name,
                )
            )

            return list(result.scalars().all())

        unit_ids: set[UUID] = set()

        # ---------------------------------------------------------
        # Explicit government data-access authorization
        # ---------------------------------------------------------
        data_access_result = await self.db.execute(
            select(
                GovernmentDataAccessAuthorization.government_unit_id
            ).where(
                GovernmentDataAccessAuthorization.user_id
                == user_id,
                GovernmentDataAccessAuthorization.status
                == GovernmentDataAccessAuthorizationStatus.ACTIVE,
            )
        )

        for unit_id in data_access_result.scalars().all():
            unit_ids.add(unit_id)

        # ---------------------------------------------------------
        # Verifier authorization
        # ---------------------------------------------------------
        verifier_result = await self.db.execute(
            select(
                VerifierAuthorization.government_unit_id
            ).where(
                VerifierAuthorization.verifier_user_id
                == user_id,
                VerifierAuthorization.is_active.is_(True),
                VerifierAuthorization.government_unit_id.is_not(None),
            )
        )

        for unit_id in verifier_result.scalars().all():
            if unit_id is not None:
                unit_ids.add(unit_id)

        # ---------------------------------------------------------
        # Approved government verification application
        # ---------------------------------------------------------
        verification_result = await self.db.execute(
            select(
                VerificationApplication.government_unit_id
            ).where(
                VerificationApplication.applicant_user_id
                == user_id,
                VerificationApplication.status
                == VerificationStatus.APPROVED.value,
                VerificationApplication.government_unit_id.is_not(
                    None
                ),
            )
        )

        for unit_id in verification_result.scalars().all():
            if unit_id is not None:
                unit_ids.add(unit_id)

        if not unit_ids:
            return []

        result = await self.db.execute(
            select(GovernmentUnit)
            .where(
                GovernmentUnit.id.in_(unit_ids),
                GovernmentUnit.is_active.is_(True),
            )
            .order_by(
                GovernmentUnit.level,
                GovernmentUnit.name,
            )
        )

        return list(result.scalars().all())

    async def can_access_unit(
        self,
        user_id: UUID,
        target_unit_id: UUID,
    ) -> bool:
        """
        Check whether a user has jurisdictional access
        to the target unit or one of its descendants.
        """

        target_unit = await self.get_unit(
            target_unit_id
        )

        if not target_unit.is_active:
            return False

        if await self.is_super_admin(user_id):
            return True

        authorized_units = await self.get_authorized_units(
            user_id
        )

        for authorized_unit in authorized_units:
            if await self.is_descendant_or_same(
                ancestor_unit_id=authorized_unit.id,
                target_unit_id=target_unit_id,
            ):
                return True

        return False

    async def require_unit_access(
        self,
        user_id: UUID,
        target_unit_id: UUID,
    ) -> GovernmentUnit:
        """
        Require jurisdictional access or raise an explicit
        access-denied error.
        """

        target_unit = await self.get_unit(
            target_unit_id
        )

        if not target_unit.is_active:
            raise GovernmentJurisdictionAccessDeniedError(
                "This government unit is inactive."
            )

        if not await self.can_access_unit(
            user_id=user_id,
            target_unit_id=target_unit_id,
        ):
            raise GovernmentJurisdictionAccessDeniedError(
                "You do not have jurisdictional access "
                "to this government unit."
            )

        return target_unit

    async def get_accessible_units(
        self,
        user_id: UUID,
    ) -> list[GovernmentUnit]:
        """
        Return all active government units that the user
        can access through their authorized hierarchy.
        """

        if await self.is_super_admin(user_id):
            result = await self.db.execute(
                select(GovernmentUnit)
                .where(
                    GovernmentUnit.is_active.is_(True)
                )
                .order_by(
                    GovernmentUnit.level,
                    GovernmentUnit.name,
                )
            )

            return list(result.scalars().all())

        authorized_units = await self.get_authorized_units(
            user_id
        )

        accessible_ids: set[UUID] = set()

        for authorized_unit in authorized_units:
            descendant_ids = (
                await self.get_descendant_unit_ids(
                    authorized_unit.id
                )
            )

            accessible_ids.update(
                descendant_ids
            )

        if not accessible_ids:
            return []

        result = await self.db.execute(
            select(GovernmentUnit)
            .where(
                GovernmentUnit.id.in_(accessible_ids),
                GovernmentUnit.is_active.is_(True),
            )
            .order_by(
                GovernmentUnit.level,
                GovernmentUnit.name,
            )
        )

        return list(result.scalars().all())

    async def get_accessible_unit_ids(
        self,
        user_id: UUID,
    ) -> list[UUID]:
        """
        Return accessible government-unit IDs.
        """

        units = await self.get_accessible_units(
            user_id
        )

        return [
            unit.id
            for unit in units
        ]