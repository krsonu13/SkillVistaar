from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.government_unit import GovernmentUnit
from app.models.user import User
from app.models.verifier_authorization import VerifierAuthorization
from app.services.government_unit_service import (
    InvalidGovernmentHierarchyError,
    is_same_or_descendant,
)


class VerifierAuthorizationError(Exception):
    pass


class VerifierAuthorizationNotFoundError(VerifierAuthorizationError):
    pass


class InvalidVerifierAuthorizationError(VerifierAuthorizationError):
    pass


VALID_APPLICATION_TYPES = {
    "GOVERNMENT",
    "EMPLOYER",
    "TRAINING_INSTITUTE",
    "CANDIDATE",
}


async def grant_authorization(
    db: AsyncSession,
    verifier_user: User,
    granted_by_user: User,
    application_type: str,
    government_unit_id: UUID | None = None,
) -> VerifierAuthorization:
    """
    Grant verification authority.

    The granting user must be handled by the API permission layer.
    This service additionally validates the target jurisdiction.
    """

    if verifier_user.id == granted_by_user.id:
        raise InvalidVerifierAuthorizationError(
            "A user cannot grant verification authority to themselves."
        )

    if application_type not in VALID_APPLICATION_TYPES:
        raise InvalidVerifierAuthorizationError(
            "Invalid verification application type."
        )

    if application_type in {"GOVERNMENT", "TRAINING_INSTITUTE"}:
        if government_unit_id is None:
            raise InvalidVerifierAuthorizationError(
                "A government jurisdiction is required for this application type."
            )

    if application_type in {"EMPLOYER", "CANDIDATE"}:
        # These can later be linked to organization/institution scopes.
        # Government jurisdiction is not mandatory here.
        pass

    if government_unit_id is not None:
        government_unit = await db.get(
            GovernmentUnit,
            government_unit_id,
        )

        if government_unit is None:
            raise InvalidVerifierAuthorizationError(
                "Government unit not found."
            )

        if not government_unit.is_active:
            raise InvalidVerifierAuthorizationError(
                "The government unit is inactive."
            )

    existing_result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.verifier_user_id == verifier_user.id,
            VerifierAuthorization.government_unit_id == government_unit_id,
            VerifierAuthorization.application_type == application_type,
            VerifierAuthorization.is_active.is_(True),
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise InvalidVerifierAuthorizationError(
            "An active authorization already exists."
        )

    authorization = VerifierAuthorization(
        verifier_user_id=verifier_user.id,
        government_unit_id=government_unit_id,
        application_type=application_type,
        granted_by_user_id=granted_by_user.id,
        is_active=True,
    )

    db.add(authorization)
    await db.commit()
    await db.refresh(authorization)

    return authorization


async def revoke_authorization(
    db: AsyncSession,
    authorization_id: UUID,
    revoked_by_user: User,
) -> VerifierAuthorization:
    authorization = await db.get(
        VerifierAuthorization,
        authorization_id,
    )

    if authorization is None:
        raise VerifierAuthorizationNotFoundError(
            "Verifier authorization not found."
        )

    if not authorization.is_active:
        raise InvalidVerifierAuthorizationError(
            "Authorization is already inactive."
        )

    if authorization.verifier_user_id == revoked_by_user.id:
        raise InvalidVerifierAuthorizationError(
            "A verifier cannot revoke their own authorization."
        )

    authorization.is_active = False

    from datetime import datetime, timezone

    authorization.revoked_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(authorization)

    return authorization


async def list_authorizations_for_verifier(
    db: AsyncSession,
    verifier_user_id: UUID,
) -> list[VerifierAuthorization]:
    result = await db.execute(
        select(VerifierAuthorization)
        .where(
            VerifierAuthorization.verifier_user_id == verifier_user_id,
        )
        .order_by(
            VerifierAuthorization.created_at.desc()
        )
    )

    return list(result.scalars().all())


async def verifier_can_review(
    db: AsyncSession,
    verifier_user_id: UUID,
    application_type: str,
    government_unit_id: UUID | None = None,
) -> bool:
    """
    Check whether a verifier has active authority for the requested
    application and jurisdiction.

    For government-scoped applications:

        authorization jurisdiction
                    ↓
             same or ancestor
                    ↓
        application jurisdiction

    Example:

        State verifier → State + all descendants
        District verifier → District + Local descendants
        Local verifier → Local only
    """

    if application_type not in VALID_APPLICATION_TYPES:
        return False

    result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.verifier_user_id == verifier_user_id,
            VerifierAuthorization.application_type == application_type,
            VerifierAuthorization.is_active.is_(True),
        )
    )

    authorizations = list(result.scalars().all())

    if not authorizations:
        return False

    # Non-government-scoped verification.
    if government_unit_id is None:
        return any(
            authorization.government_unit_id is None
            for authorization in authorizations
        )

    # Government-scoped verification.
    for authorization in authorizations:
        if authorization.government_unit_id is None:
            continue

        try:
            if await is_same_or_descendant(
                db,
                government_unit_id,
                authorization.government_unit_id,
            ):
                return True

        except (
            InvalidGovernmentHierarchyError,
        ):
            return False

    return False