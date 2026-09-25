from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.services.assessment_service import (
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentService,
    AssessmentServiceError,
    AssessmentValidationError,
)


router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
)


def handle_service_error(
    exc: AssessmentServiceError,
) -> HTTPException:
    if isinstance(exc, AssessmentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, AssessmentAccessDeniedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, AssessmentValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


# ----------------------------------------------------------------------
# CREATE
# ----------------------------------------------------------------------


@router.get(
    "",
    response_model=AssessmentListResponse,
)
@router.get(
    "/",
    response_model=AssessmentListResponse,
    include_in_schema=False,
)
async def list_assessments_root(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
):
    """List assessments for the current user's organization, or published assessments."""
    from app.models.organization import Organization
    from app.models.organization_member import OrganizationMember

    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == current_user.id)
    )
    org = org_res.scalars().first()
    if not org:
        member_res = await db.execute(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == current_user.id
            ).limit(1)
        )
        member_org_id = member_res.scalar_one_or_none()
        if member_org_id:
            org = await db.get(Organization, member_org_id)

    service = AssessmentService(db)
    try:
        if org:
            assessments = await service.list_organization_assessments(
                user=current_user,
                organization_id=org.id,
                include_archived=include_archived,
            )
        else:
            assessments = await service.list_published_assessments()

        return AssessmentListResponse(
            items=assessments,
            total=len(assessments),
        )
    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_assessment(
    data: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new employer assessment in DRAFT state."""

    service = AssessmentService(db)

    try:
        return await service.create_assessment(
            user=current_user,
            data=data,
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# LIST ORGANIZATION ASSESSMENTS
# ----------------------------------------------------------------------


@router.get(
    "/organization/{organization_id}",
    response_model=AssessmentListResponse,
)
async def list_organization_assessments(
    organization_id: UUID,
    include_archived: bool = Query(
        default=False
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List assessments managed by the current user's organization."""

    service = AssessmentService(db)

    try:
        assessments = (
            await service.list_organization_assessments(
                user=current_user,
                organization_id=organization_id,
                include_archived=include_archived,
            )
        )

        return AssessmentListResponse(
            items=assessments,
            total=len(assessments),
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# GET ONE
# ----------------------------------------------------------------------


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
async def get_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get an assessment.

    Access is limited to authorized managers of the
    assessment's employer organization.
    """

    service = AssessmentService(db)

    try:
        assessment = await service.get_assessment(
            assessment_id
        )

        await service.ensure_assessment_access(
            user=current_user,
            assessment=assessment,
        )

        return assessment

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------


@router.patch(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
async def update_assessment(
    assessment_id: UUID,
    data: AssessmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an assessment."""

    service = AssessmentService(db)

    try:
        return await service.update_assessment(
            user=current_user,
            assessment_id=assessment_id,
            data=data,
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# SUBMIT FOR REVIEW
# ----------------------------------------------------------------------


@router.post(
    "/{assessment_id}/submit-review",
    response_model=AssessmentResponse,
)
async def submit_assessment_for_review(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a completed draft assessment for review."""

    service = AssessmentService(db)

    try:
        return await service.submit_for_review(
            user=current_user,
            assessment_id=assessment_id,
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# PUBLISH
# ----------------------------------------------------------------------


@router.post(
    "/{assessment_id}/publish",
    response_model=AssessmentResponse,
)
async def publish_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish an assessment.

    In the current MVP, authorized assessment managers
    can publish assessments that are pending review.
    """

    service = AssessmentService(db)

    try:
        return await service.publish_assessment(
            user=current_user,
            assessment_id=assessment_id,
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc


# ----------------------------------------------------------------------
# ARCHIVE
# ----------------------------------------------------------------------


@router.post(
    "/{assessment_id}/archive",
    response_model=AssessmentResponse,
)
async def archive_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive an assessment."""

    service = AssessmentService(db)

    try:
        return await service.archive_assessment(
            user=current_user,
            assessment_id=assessment_id,
        )

    except AssessmentServiceError as exc:
        raise handle_service_error(exc) from exc