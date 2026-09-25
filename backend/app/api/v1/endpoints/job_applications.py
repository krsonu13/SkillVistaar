from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    APPLY_FOR_JOB,
    MANAGE_JOB_APPLICATIONS,
    VIEW_JOB_APPLICATIONS,
    VIEW_OWN_APPLICATIONS,
    require_permissions,
)
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.organization import Organization
from app.models.user import User
from app.schemas.job_application import (
    JobApplicationCreate,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationStatusUpdate,
)
from app.services.job_application_service import (
    JobApplicationAccessDeniedError,
    JobApplicationNotFoundError,
    JobApplicationService,
    JobApplicationServiceError,
    JobApplicationValidationError,
)

router = APIRouter(
    prefix="/applications",
    tags=["Job Applications"],
)


def _request_metadata(
    request: Request,
) -> tuple[str | None, str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
        request.headers.get("x-request-id"),
    )


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobApplicationNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, JobApplicationAccessDeniedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, JobApplicationValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


# ============================================================
# Candidate
# ============================================================

@router.post(
    "/jobs/{job_id}",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_for_job(
    job_id: UUID,
    payload: JobApplicationCreate,
    request: Request,
    current_user_data=Depends(
        require_permissions(APPLY_FOR_JOB)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    ip_address, user_agent, request_id = (
        _request_metadata(request)
    )

    service = JobApplicationService(db)

    try:
        return await service.create_application(
            job_id=job_id,
            candidate_user_id=current_user.id,
            cover_letter=payload.cover_letter,
            resume_document_id=payload.resume_document_id,
            consent_to_share_profile=(
                payload.consent_to_share_profile
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.get(
    "/mine",
    response_model=JobApplicationListResponse,
)
async def list_my_applications(
    current_user_data=Depends(
        require_permissions(VIEW_OWN_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobApplicationService(db)

    try:
        applications = (
            await service.list_candidate_applications(
                current_user.id
            )
        )

        return {
            "applications": applications,
            "items": applications,
            "total": len(applications),
            "page": 1,
            "page_size": len(applications) or 50,
            "pages": 1,
        }

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.get(
    "/{application_id}",
    response_model=JobApplicationResponse,
)
async def get_my_application(
    application_id: UUID,
    current_user_data=Depends(
        require_permissions(VIEW_OWN_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobApplicationService(db)

    try:
        return await service.get_candidate_application(
            application_id=application_id,
            candidate_user_id=current_user.id,
        )

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.post(
    "/{application_id}/withdraw",
    response_model=JobApplicationResponse,
)
async def withdraw_application(
    application_id: UUID,
    request: Request,
    current_user_data=Depends(
        require_permissions(VIEW_OWN_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    ip_address, user_agent, request_id = (
        _request_metadata(request)
    )

    service = JobApplicationService(db)

    try:
        return await service.withdraw_application(
            application_id=application_id,
            candidate_user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


# ============================================================
# Employer
# ============================================================

@router.get(
    "/job/{job_id}",
    response_model=JobApplicationListResponse,
)
async def list_job_applications(
    job_id: UUID,
    current_user_data=Depends(
        require_permissions(VIEW_JOB_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobApplicationService(db)

    try:
        applications = (
            await service.list_job_applications(
                job_id=job_id,
                manager_user_id=current_user.id,
            )
        )

        return {
            "applications": applications,
            "items": applications,
            "total": len(applications),
            "page": 1,
            "page_size": len(applications) or 50,
            "pages": 1,
        }

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.get(
    "/employer/{application_id}",
    response_model=JobApplicationResponse,
)
async def get_job_application(
    application_id: UUID,
    current_user_data=Depends(
        require_permissions(VIEW_JOB_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    service = JobApplicationService(db)

    try:
        return await service.get_job_application(
            application_id=application_id,
            manager_user_id=current_user.id,
        )

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.patch(
    "/{application_id}/status",
    response_model=JobApplicationResponse,
)
async def update_application_status(
    application_id: UUID,
    payload: JobApplicationStatusUpdate,
    request: Request,
    current_user_data=Depends(
        require_permissions(MANAGE_JOB_APPLICATIONS)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _roles = current_user_data

    ip_address, user_agent, request_id = (
        _request_metadata(request)
    )

    service = JobApplicationService(db)

    try:
        return await service.update_application_status(
            application_id=application_id,
            manager_user_id=current_user.id,
            new_status=payload.status,
            reason=payload.reason,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    except JobApplicationServiceError as exc:
        raise _handle_service_error(exc) from exc


@router.get("/organization/mine")
async def list_employer_organization_applications(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List all candidate job applications submitted to jobs posted by the employer's organization.
    """
    user, _ = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        return []

    stmt = (
        select(
            JobApplication,
            Job.title,
            CandidateProfile.first_name,
            CandidateProfile.last_name,
            CandidateProfile.headline,
            User.email,
        )
        .join(Job, Job.id == JobApplication.job_id)
        .join(CandidateProfile, CandidateProfile.id == JobApplication.candidate_profile_id)
        .join(User, User.id == JobApplication.candidate_user_id)
        .where(Job.organization_id == org.id)
        .order_by(JobApplication.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    result = []
    for app, job_title, fn, ln, headline, email in rows:
        name = f"{fn} {ln or ''}".strip() or (email.split("@")[0] if email else "Candidate").capitalize()
        result.append({
            "id": str(app.id),
            "candidateName": name,
            "candidateRole": headline or "Verified Professional",
            "appliedFor": job_title,
            "nsqfLevel": 5,
            "isVerified": True,
            "matchScore": 90,
            "status": app.status,
            "appliedDate": app.created_at.strftime("%b %d, %Y") if app.created_at else "Recently",
        })
    return result

