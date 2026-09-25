from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.candidate_credential import CandidateCredential, CredentialStatus
from app.models.job import Job, JobStatus
from app.models.organization import Organization, OrganizationType
from app.models.user import User

router = APIRouter(
    prefix="/public",
    tags=["Public Platform Statistics"],
)


@router.get("/platform-stats")
async def get_public_platform_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns real aggregate counts from the PostgreSQL database for the public landing page.
    If no data has been created yet, actual counts (e.g. 0) are returned with zero fabrication.
    """
    # 1. Verified Candidates
    cand_stmt = select(func.count(User.id)).where(
        User.account_type == "CANDIDATE",
        User.is_active == True,
        (User.email_verified == True) | (User.phone_verified == True),
    )
    verified_candidates = (await db.execute(cand_stmt)).scalar() or 0

    # 2. Hiring Employers
    emp_stmt = select(func.count(Organization.id)).where(
        Organization.organization_type == OrganizationType.EMPLOYER.value,
        Organization.is_active == True,
    )
    employers_count = (await db.execute(emp_stmt)).scalar() or 0

    # 3. Training Institutes
    inst_stmt = select(func.count(Organization.id)).where(
        Organization.organization_type == OrganizationType.TRAINING_INSTITUTE.value,
        Organization.is_active == True,
    )
    institutes_count = (await db.execute(inst_stmt)).scalar() or 0

    # 4. Verified Credentials
    cred_stmt = select(func.count(CandidateCredential.id)).where(
        CandidateCredential.status == CredentialStatus.VERIFIED.value,
    )
    verified_credentials_count = (await db.execute(cred_stmt)).scalar() or 0

    # 5. Active Jobs
    jobs_stmt = select(func.count(Job.id)).where(
        Job.status == JobStatus.PUBLISHED.value,
        Job.is_active == True,
    )
    active_jobs_count = (await db.execute(jobs_stmt)).scalar() or 0

    return {
        "success": True,
        "metrics": {
            "verified_candidates": verified_candidates,
            "hiring_employers": employers_count,
            "training_institutes": institutes_count,
            "verified_credentials": verified_credentials_count,
            "active_jobs": active_jobs_count,
        },
    }


@router.get("/platform-config/{config_key}")
async def get_public_platform_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Publicly accessible endpoint for landing page, signup, and login pages
    to fetch the currently active customized platform content and form configurations.
    """
    from app.models.platform_config import PlatformConfig
    from app.api.v1.endpoints.admin import DEFAULT_PLATFORM_CONFIGS

    res = await db.execute(
        select(PlatformConfig)
        .where(PlatformConfig.config_key == config_key, PlatformConfig.is_active.is_(True))
        .order_by(PlatformConfig.version.desc())
    )
    cfg = res.scalars().first()

    if not cfg:
        default_data = DEFAULT_PLATFORM_CONFIGS.get(config_key, {})
        return {
            "config_key": config_key,
            "version": 0,
            "config_data": default_data,
        }

    return {
        "config_key": cfg.config_key,
        "version": cfg.version,
        "config_data": cfg.config_data,
    }
