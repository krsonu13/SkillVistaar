from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.job_matching_service import (
    JobMatchResult,
    JobMatchingNotFoundError,
    JobMatchingService,
    JobMatchingValidationError,
)

router = APIRouter(
    prefix="/candidate/matching",
    tags=["Candidate Job Matching"],
)


class SkillMatchResponse(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    requirement_type: str
    is_verified: bool
    matched: bool


class JobMatchResponse(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    score: float
    required_skills: int
    matched_required_skills: int
    preferred_skills: int
    matched_preferred_skills: int
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    matched_skills: list[str]
    skill_matches: list[SkillMatchResponse]


def serialize_match(
    result: JobMatchResult,
) -> JobMatchResponse:
    return JobMatchResponse(
        job_id=result.job_id,
        candidate_id=result.candidate_id,
        score=result.score,
        required_skills=result.required_skills,
        matched_required_skills=result.matched_required_skills,
        preferred_skills=result.preferred_skills,
        matched_preferred_skills=result.matched_preferred_skills,
        missing_required_skills=result.missing_required_skills,
        missing_preferred_skills=result.missing_preferred_skills,
        matched_skills=result.matched_skills,
        skill_matches=[
            SkillMatchResponse(
                skill_id=item.skill_id,
                skill_name=item.skill_name,
                required_proficiency=item.required_proficiency,
                candidate_proficiency=item.candidate_proficiency,
                requirement_type=item.requirement_type,
                is_verified=item.is_verified,
                matched=item.matched,
            )
            for item in result.skill_matches
        ],
    )


@router.get(
    "/job/{job_id}",
    response_model=JobMatchResponse,
)
async def match_current_candidate_to_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobMatchResponse:
    """
    Match the logged-in candidate against one published job.
    """

    if current_user.account_type != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can use job matching.",
        )

    from app.models.candidate_profile import CandidateProfile

    result = await db.execute(
        select(CandidateProfile.id).where(
            CandidateProfile.user_id == current_user.id
        )
    )

    candidate_id = result.scalar_one_or_none()

    if candidate_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    try:
        match = await JobMatchingService.match_candidate_to_job(
            db,
            candidate_id,
            job_id,
        )

        return serialize_match(match)

    except JobMatchingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except JobMatchingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/jobs",
    response_model=list[JobMatchResponse],
)
async def match_current_candidate_to_jobs(
    minimum_score: float = Query(
        default=0.0,
        ge=0.0,
        le=100.0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobMatchResponse]:
    """
    Return published jobs ranked by the candidate's
    verified-skill match score.
    """

    if current_user.account_type != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can use job matching.",
        )

    from app.models.candidate_profile import CandidateProfile

    result = await db.execute(
        select(CandidateProfile.id).where(
            CandidateProfile.user_id == current_user.id
        )
    )

    candidate_id = result.scalar_one_or_none()

    if candidate_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )

    try:
        matches = (
            await JobMatchingService.match_candidate_to_published_jobs(
                db,
                candidate_id,
                minimum_score,
                limit,
            )
        )

        return [
            serialize_match(match)
            for match in matches
        ]

    except JobMatchingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc