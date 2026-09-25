from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    GOVERNMENT_ADMIN,
    GOVERNMENT_VERIFIER,
    MANAGE_VERIFIERS,
    REVIEW_VERIFICATION,
    SUPER_ADMIN,
    has_role,
    require_permissions,
)
from app.db.session import get_db
from app.models.government_unit import GovernmentUnit
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.verifier_authorization import VerifierAuthorization
from app.schemas.verifier_authorization import (
    VerifierAuthorizationCreate,
    VerifierAuthorizationResponse,
)
from app.services.audit_log_service import AuditLogService
from app.services.government_jurisdiction_service import (
    GovernmentJurisdictionService,
)


router = APIRouter(
    prefix="/verifier-authorizations",
    tags=["Verifier Authorizations"],
)


async def _is_super_admin(
    current_user: User,
    roles: list[str],
) -> bool:
    return (
        current_user.is_active
        and not current_user.is_suspended
        and has_role(roles, SUPER_ADMIN)
    )


async def _validate_government_unit(
    db: AsyncSession,
    government_unit_id: UUID,
) -> GovernmentUnit:
    result = await db.execute(
        select(GovernmentUnit).where(
            GovernmentUnit.id == government_unit_id,
            GovernmentUnit.is_active.is_(True),
        )
    )

    unit = result.scalar_one_or_none()

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Government unit not found or inactive.",
        )

    return unit


async def _get_authorized_unit_ids(
    db: AsyncSession,
    current_user: User,
    roles: list[str],
) -> set[UUID]:
    service = GovernmentJurisdictionService(db)

    return set(
        await service.get_accessible_unit_ids(
            current_user.id,
            roles,
        )
    )


async def _can_manage_unit(
    db: AsyncSession,
    current_user: User,
    roles: list[str],
    government_unit_id: UUID,
) -> bool:
    if await _is_super_admin(current_user, roles):
        return True

    authorized_units = await _get_authorized_unit_ids(
        db,
        current_user,
        roles,
    )

    return government_unit_id in authorized_units


async def _validate_verifier_role(
    db: AsyncSession,
    verifier_user_id: UUID,
) -> None:
    result = await db.execute(
        select(Role.code)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == verifier_user_id,
            UserRole.is_active.is_(True),
            Role.is_active.is_(True),
            Role.code.in_(
                [
                    GOVERNMENT_ADMIN,
                    GOVERNMENT_VERIFIER,
                ]
            ),
        )
    )

    roles = set(result.scalars().all())

    if not roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected user must have an active "
                "GOVERNMENT_ADMIN or GOVERNMENT_VERIFIER role."
            ),
        )


async def _record_audit(
    db: AsyncSession,
    *,
    current_user: User,
    authorization: VerifierAuthorization,
    action: str,
    description: str,
) -> None:
    await AuditLogService.record(
        db,
        actor_user_id=current_user.id,
        action=action,
        resource_type="VerifierAuthorization",
        resource_id=authorization.id,
        description=description,
        metadata={
            "verifier_user_id": str(authorization.verifier_user_id),
            "government_unit_id": str(
                authorization.government_unit_id
            ),
            "application_type": authorization.application_type,
            "is_active": authorization.is_active,
        },
    )


@router.post(
    "",
    response_model=VerifierAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verifier_authorization(
    data: VerifierAuthorizationCreate,
    current_user_and_roles=Depends(
        require_permissions(MANAGE_VERIFIERS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    if data.verifier_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user cannot authorize themselves as a verifier.",
        )

    await _validate_government_unit(
        db,
        data.government_unit_id,
    )

    if not await _can_manage_unit(
        db,
        current_user,
        roles,
        data.government_unit_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized to manage verifier "
                "authorizations for this government jurisdiction."
            ),
        )

    verifier_result = await db.execute(
        select(User).where(
            User.id == data.verifier_user_id,
            User.is_active.is_(True),
            User.is_suspended.is_(False),
        )
    )

    verifier = verifier_result.scalar_one_or_none()

    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verifier user not found or inactive.",
        )

    await _validate_verifier_role(
        db,
        data.verifier_user_id,
    )

    duplicate_result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.verifier_user_id
            == data.verifier_user_id,
            VerifierAuthorization.government_unit_id
            == data.government_unit_id,
            VerifierAuthorization.application_type
            == data.application_type,
            VerifierAuthorization.is_active.is_(True),
        )
    )

    if duplicate_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An active verifier authorization already exists "
                "for this user, government unit, and application type."
            ),
        )

    authorization = VerifierAuthorization(
        verifier_user_id=data.verifier_user_id,
        government_unit_id=data.government_unit_id,
        application_type=data.application_type,
        granted_by_user_id=current_user.id,
        is_active=True,
    )

    db.add(authorization)

    await db.flush()

    await _record_audit(
        db,
        current_user=current_user,
        authorization=authorization,
        action="GRANT_ACCESS",
        description=(
            "Verifier authorization granted for a government jurisdiction."
        ),
    )

    await db.commit()
    await db.refresh(authorization)

    return authorization


@router.get(
    "",
    response_model=list[VerifierAuthorizationResponse],
)
async def list_verifier_authorizations(
    verifier_user_id: UUID | None = None,
    government_unit_id: UUID | None = None,
    include_inactive: bool = False,
    current_user_and_roles=Depends(
        require_permissions(REVIEW_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    if government_unit_id is not None:
        await _validate_government_unit(
            db,
            government_unit_id,
        )

        if not await _can_manage_unit(
            db,
            current_user,
            roles,
            government_unit_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You are not authorized to view verifier "
                    "authorizations for this government jurisdiction."
                ),
            )

        query = select(VerifierAuthorization).where(
            VerifierAuthorization.government_unit_id
            == government_unit_id
        )

    elif await _is_super_admin(current_user, roles):
        query = select(VerifierAuthorization)

    else:
        accessible_units = await _get_authorized_unit_ids(
            db,
            current_user,
            roles,
        )

        if not accessible_units:
            return []

        query = select(VerifierAuthorization).where(
            VerifierAuthorization.government_unit_id.in_(
                accessible_units
            )
        )

    if verifier_user_id is not None:
        query = query.where(
            VerifierAuthorization.verifier_user_id
            == verifier_user_id
        )

    if not include_inactive:
        query = query.where(
            VerifierAuthorization.is_active.is_(True)
        )

    query = query.order_by(
        VerifierAuthorization.created_at.desc()
    )

    result = await db.execute(query)

    return list(result.scalars().all())


@router.get(
    "/{authorization_id}",
    response_model=VerifierAuthorizationResponse,
)
async def get_verifier_authorization(
    authorization_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(REVIEW_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.id == authorization_id
        )
    )

    authorization = result.scalar_one_or_none()

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verifier authorization not found.",
        )

    if not await _can_manage_unit(
        db,
        current_user,
        roles,
        authorization.government_unit_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized to view this verifier "
                "authorization."
            ),
        )

    return authorization


@router.post(
    "/{authorization_id}/revoke",
    response_model=VerifierAuthorizationResponse,
)
async def revoke_verifier_authorization(
    authorization_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(MANAGE_VERIFIERS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.id == authorization_id
        )
    )

    authorization = result.scalar_one_or_none()

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verifier authorization not found.",
        )

    if not await _can_manage_unit(
        db,
        current_user,
        roles,
        authorization.government_unit_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized to revoke verifier "
                "authorizations for this government jurisdiction."
            ),
        )

    if not authorization.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verifier authorization is already inactive.",
        )

    authorization.is_active = False

    await _record_audit(
        db,
        current_user=current_user,
        authorization=authorization,
        action="REVOKE",
        description="Verifier authorization revoked.",
    )

    await db.commit()
    await db.refresh(authorization)

    return authorization


@router.post(
    "/{authorization_id}/activate",
    response_model=VerifierAuthorizationResponse,
)
async def activate_verifier_authorization(
    authorization_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(MANAGE_VERIFIERS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerifierAuthorization).where(
            VerifierAuthorization.id == authorization_id
        )
    )

    authorization = result.scalar_one_or_none()

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verifier authorization not found.",
        )

    if not await _can_manage_unit(
        db,
        current_user,
        roles,
        authorization.government_unit_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized to activate verifier "
                "authorizations for this government jurisdiction."
            ),
        )

    verifier_result = await db.execute(
        select(User).where(
            User.id == authorization.verifier_user_id,
            User.is_active.is_(True),
            User.is_suspended.is_(False),
        )
    )

    verifier = verifier_result.scalar_one_or_none()

    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The verifier user is inactive or suspended and "
                "cannot be reactivated."
            ),
        )

    await _validate_verifier_role(
        db,
        authorization.verifier_user_id,
    )

    if authorization.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verifier authorization is already active.",
        )

    authorization.is_active = True

    await _record_audit(
        db,
        current_user=current_user,
        authorization=authorization,
        action="RESTORE",
        description="Verifier authorization reactivated.",
    )

    await db.commit()
    await db.refresh(authorization)

    return authorization