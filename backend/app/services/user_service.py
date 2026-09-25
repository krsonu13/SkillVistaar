from uuid import UUID
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.government_unit import GovernmentUnit
from app.models.organization import Organization
from app.models.user import User
from app.models.verification_application import VerificationApplication


async def resolve_user_verification_status(db: AsyncSession, user: User) -> str:
    """
    Resolves the canonical verification status for any user account:
    - SUPER_ADMIN: "APPROVED"
    - CANDIDATE: "APPROVED" if (user.email_verified or user.phone_verified) else "PENDING"
    - EMPLOYER / TRAINING_INSTITUTE: checks linked Organization.verification_status
    - GOVERNMENT: checks linked GovernmentUnit.status and any VerificationApplication
    """
    if user.account_type == "SUPER_ADMIN":
        return "APPROVED"

    if user.account_type == "CANDIDATE":
        return "APPROVED" if (user.email_verified or user.phone_verified) else "PENDING"

    if user.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
        org_stmt = (
            select(Organization.verification_status)
            .where(Organization.owner_user_id == user.id)
            .limit(1)
        )
        res = await db.execute(org_stmt)
        org_status = res.scalar_one_or_none()
        if org_status:
            return org_status

        app_stmt = (
            select(VerificationApplication.status)
            .where(VerificationApplication.applicant_user_id == user.id)
            .limit(1)
        )
        app_res = await db.execute(app_stmt)
        app_status = app_res.scalar_one_or_none()
        return app_status or "PENDING"

    if user.account_type == "GOVERNMENT":
        app_stmt = (
            select(VerificationApplication.status)
            .where(VerificationApplication.applicant_user_id == user.id)
            .limit(1)
        )
        app_res = await db.execute(app_stmt)
        app_status = app_res.scalar_one_or_none()
        if app_status:
            return app_status

        if user.government_unit_id:
            unit_stmt = (
                select(GovernmentUnit.status)
                .where(GovernmentUnit.id == user.government_unit_id)
                .limit(1)
            )
            unit_res = await db.execute(unit_stmt)
            unit_status = unit_res.scalar_one_or_none()
            if unit_status == "ACTIVE":
                return "APPROVED"

        return "PENDING"

    return "PENDING"
