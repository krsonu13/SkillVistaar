from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationType,
    OrganizationVerificationStatus,
)
from app.models.organization_member import (
    OrganizationMember,
    OrganizationMemberRole,
)
from app.models.user import User


class OrganizationMemberError(Exception):
    """Raised when an organization membership operation is invalid."""


EMPLOYER_ROLES = {
    OrganizationMemberRole.ORG_ADMIN.value,
    OrganizationMemberRole.HR.value,
    OrganizationMemberRole.JOB_POSTER.value,
    OrganizationMemberRole.ASSESSMENT_MANAGER.value,
}

INSTITUTION_ROLES = {
    OrganizationMemberRole.ORG_ADMIN.value,
    OrganizationMemberRole.INSTITUTION_ADMIN.value,
}


async def get_organization(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Organization:
    organization = await db.get(Organization, organization_id)

    if organization is None:
        raise OrganizationMemberError("Organization not found.")

    return organization


async def get_active_membership(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role_code: str | None = None,
) -> OrganizationMember | None:
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.is_active.is_(True),
    )

    if role_code is not None:
        stmt = stmt.where(
            OrganizationMember.role_code == role_code
        )

    result = await db.execute(stmt)
    return result.scalars().first()


async def require_org_admin(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> OrganizationMember:
    membership = await get_active_membership(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        role_code=OrganizationMemberRole.ORG_ADMIN.value,
    )

    if membership is None:
        raise OrganizationMemberError(
            "You do not have ORG_ADMIN permission for this organization."
        )

    return membership


async def validate_organization_for_membership(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Organization:
    organization = await get_organization(
        db,
        organization_id,
    )

    if not organization.is_active:
        raise OrganizationMemberError(
            "Organization is inactive."
        )

    if (
        organization.verification_status
        != OrganizationVerificationStatus.APPROVED.value
    ):
        raise OrganizationMemberError(
            "Organization must be approved before managing members."
        )

    return organization


def validate_role_for_organization(
    organization: Organization,
    role_code: str,
) -> None:
    valid_roles: set[str]

    if (
        organization.organization_type
        == OrganizationType.EMPLOYER.value
    ):
        valid_roles = EMPLOYER_ROLES

    elif (
        organization.organization_type
        == OrganizationType.TRAINING_INSTITUTE.value
    ):
        valid_roles = INSTITUTION_ROLES

    else:
        raise OrganizationMemberError(
            "Unsupported organization type."
        )

    if role_code not in valid_roles:
        raise OrganizationMemberError(
            f"Role '{role_code}' cannot be assigned to this organization."
        )


async def add_member(
    db: AsyncSession,
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role_code: str,
    invited_by_user_id: uuid.UUID,
) -> OrganizationMember:
    organization = await validate_organization_for_membership(
        db,
        organization_id,
    )

    await require_org_admin(
        db=db,
        organization_id=organization_id,
        user_id=invited_by_user_id,
    )

    validate_role_for_organization(
        organization,
        role_code,
    )

    target_user = await db.get(User, target_user_id)

    if target_user is None:
        raise OrganizationMemberError(
            "Target user not found."
        )

    if not target_user.is_active or target_user.is_suspended:
        raise OrganizationMemberError(
            "Target user is inactive or suspended."
        )

    existing = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == target_user_id,
            OrganizationMember.role_code == role_code,
        )
    )

    existing_member = existing.scalars().first()

    if existing_member is not None:
        if existing_member.is_active:
            raise OrganizationMemberError(
                "User already has this organization role."
            )

        existing_member.is_active = True
        existing_member.revoked_at = None
        existing_member.joined_at = datetime.now(timezone.utc)
        existing_member.invited_by_user_id = invited_by_user_id

        await db.commit()
        await db.refresh(existing_member)

        return existing_member

    member = OrganizationMember(
        organization_id=organization_id,
        user_id=target_user_id,
        role_code=role_code,
        invited_by_user_id=invited_by_user_id,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )

    db.add(member)

    await db.commit()
    await db.refresh(member)

    return member


async def revoke_member(
    db: AsyncSession,
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role_code: str,
    revoked_by_user_id: uuid.UUID,
) -> OrganizationMember:
    await validate_organization_for_membership(
        db,
        organization_id,
    )

    await require_org_admin(
        db=db,
        organization_id=organization_id,
        user_id=revoked_by_user_id,
    )

    membership = await get_active_membership(
        db=db,
        organization_id=organization_id,
        user_id=target_user_id,
        role_code=role_code,
    )

    if membership is None:
        raise OrganizationMemberError(
            "Active organization membership not found."
        )

    if target_user_id == revoked_by_user_id:
        raise OrganizationMemberError(
            "You cannot revoke your own organization membership."
        )

    membership.is_active = False
    membership.revoked_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(membership)

    return membership


async def list_organization_members(
    db: AsyncSession,
    organization_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
) -> list[OrganizationMember]:
    await validate_organization_for_membership(
        db,
        organization_id,
    )

    await require_org_admin(
        db=db,
        organization_id=organization_id,
        user_id=requesting_user_id,
    )

    result = await db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active.is_(True),
        )
        .order_by(
            OrganizationMember.created_at.asc()
        )
    )

    return list(result.scalars().all())


async def user_has_organization_role(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role_code: str,
) -> bool:
    membership = await get_active_membership(
        db=db,
        organization_id=organization_id,
        user_id=user_id,
        role_code=role_code,
    )

    return membership is not None