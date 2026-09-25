from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import (
    CandidateRecommendationDashboard,
    CourseRecommendationResponse,
    JobRecommendationResponse,
)
from app.services.recommendation_service import (
    CandidateNotFoundError,
    RecommendationService,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


@router.get(
    "/jobs",
    response_model=list[JobRecommendationResponse],
)
async def recommended_jobs(
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecommendationService(db)

    try:
        return await service.recommend_jobs(
            user.id,
            limit=limit,
        )
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/courses",
    response_model=list[CourseRecommendationResponse],
)
async def recommended_courses(
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecommendationService(db)

    try:
        return await service.recommend_courses(
            user.id,
            limit=limit,
        )
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/dashboard",
    response_model=CandidateRecommendationDashboard,
)
async def recommendation_dashboard(
    job_limit: int = Query(10, ge=1, le=30),
    course_limit: int = Query(10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecommendationService(db)

    try:
        return await service.dashboard(
            user.id,
            job_limit=job_limit,
            course_limit=course_limit,
        )
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc