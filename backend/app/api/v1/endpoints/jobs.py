from __future__ import annotations

from uuid import UUID

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    CREATE_JOB,
    UPDATE_JOB,
    PUBLISH_JOB,
    CLOSE_JOB,
    VIEW_JOBS,
    require_permissions,
)
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.organization import Organization
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
)
from app.services.job_service import (
    JobService,
    JobServiceError,
    JobNotFoundError,
    JobAccessDeniedError,
    JobValidationError,
)


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


def _request_metadata(request: Request) -> dict:
    return {
        "ip_address": request.client.host
        if request.client
        else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.headers.get("x-request-id"),
    }


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    payload: JobCreate,
    request: Request,
    current_user=Depends(
        require_permissions(CREATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        metadata = _request_metadata(request)

        return await service.create_job(
            user_id=current_user.id,
            organization_id=payload.organization_id,
            data=payload.model_dump(
                exclude={"organization_id"},
                exclude_unset=True,
            ),
            **metadata,
        )

    except JobAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        )
    except JobValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except JobServiceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get(
    "/public",
    response_model=dict,
)
@router.get(
    "",
    response_model=dict,
)
async def list_public_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    eff_limit = limit if limit is not None else page_size
    eff_offset = offset if offset is not None else (page - 1) * page_size

    jobs = await service.list_public_jobs(
        limit=eff_limit,
        offset=eff_offset,
    )

    return {
        "items": [JobResponse.model_validate(job) for job in jobs],
        "total": len(jobs),
        "page": page,
        "page_size": eff_limit,
    }


@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
async def get_job(
    job_id: UUID,
    current_user=Depends(
        require_permissions(VIEW_JOBS)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        job = await service.get_job(
            job_id=job_id,
        )

        if job.status != "PUBLISHED" and not await service._is_manager(
            current_user.id,
            job.organization_id,
        ):
            raise JobAccessDeniedError(
                "This job is not publicly available."
            )

        return job

    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    except JobAccessDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        )


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
)
async def update_job(
    job_id: UUID,
    payload: JobUpdate,
    request: Request,
    current_user=Depends(
        require_permissions(UPDATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.update_job(
            job_id=job_id,
            user_id=current_user.id,
            data=payload.model_dump(
                exclude_unset=True
            ),
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/submit-review",
    response_model=JobResponse,
)
async def submit_for_review(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(UPDATE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.submit_for_review(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/publish",
    response_model=JobResponse,
)
async def publish_job(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(PUBLISH_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.publish_job(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/pause",
    response_model=JobResponse,
)
async def pause_job(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(CLOSE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.pause_job(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/resume",
    response_model=JobResponse,
)
async def resume_job(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(CLOSE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.resume_job(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/close",
    response_model=JobResponse,
)
async def close_job(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(CLOSE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.close_job(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.post(
    "/{job_id}/archive",
    response_model=JobResponse,
)
async def archive_job(
    job_id: UUID,
    request: Request,
    current_user=Depends(
        require_permissions(CLOSE_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)

    try:
        return await service.archive_job(
            job_id=job_id,
            user_id=current_user.id,
            **_request_metadata(request),
        )

    except JobNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except JobAccessDeniedError as exc:
        raise HTTPException(403, str(exc))
    except JobValidationError as exc:
        raise HTTPException(400, str(exc))


@router.get("/me/organization")
async def get_my_organization_jobs(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get all jobs posted by the authenticated employer's organization with live applicant counts.
    """
    user, _ = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        return []

    jobs_res = await db.execute(
        select(Job).where(Job.organization_id == org.id).order_by(Job.created_at.desc())
    )
    jobs = jobs_res.scalars().all()

    result = []
    for j in jobs:
        cnt_res = await db.execute(
            select(func.count(JobApplication.id)).where(JobApplication.job_id == j.id)
        )
        applicants_cnt = cnt_res.scalar() or 0
        salary_str = "Competitive"
        if j.min_salary and j.max_salary:
            salary_str = f"₹{float(j.min_salary)/100000:.1f} - {float(j.max_salary)/100000:.1f} LPA"
        elif j.min_salary:
            salary_str = f"₹{float(j.min_salary)/100000:.1f}+ LPA"

        result.append({
            "id": str(j.id),
            "title": j.title,
            "type": j.employment_type or "Full-time",
            "location": j.location or "On-site",
            "salary": salary_str,
            "nsqfRequirement": f"NSQF Level {j.target_nsqf_level or 5}",
            "applicantsCount": applicants_cnt,
            "status": j.status,
            "postedAt": j.created_at.strftime("%b %d, %Y") if j.created_at else "Recently",
            "description": j.description or "",
            "skills": [s.strip() for s in j.required_skills.split(",")] if j.required_skills else [],
        })
    return result

