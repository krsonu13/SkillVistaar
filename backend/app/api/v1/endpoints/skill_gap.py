from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.user import User
from app.services.skill_gap_service import (
    SkillGapNotFoundError,
    SkillGapService,
)


router = APIRouter(
    prefix="/candidate/skill-gaps",
    tags=["Candidate Skill Gap Analysis"],
)


class SkillGapResponse(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    required_proficiency: str
    requirement_type: str
    is_mandatory: bool
    candidate_proficiency: str | None
    status: str


class CourseRecommendationResponse(BaseModel):
    course_id: uuid.UUID
    course_title: str
    institution_profile_id: uuid.UUID
    matched_skill_ids: list[uuid.UUID]
    matched_skill_names: list[str]
    coverage_percentage: float


class SkillGapAnalysisResponse(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    matched_skills: list[str]
    missing_required_skills: list[SkillGapResponse]
    missing_preferred_skills: list[SkillGapResponse]
    total_required_gaps: int
    total_preferred_gaps: int
    recommendations: list[CourseRecommendationResponse]


@router.get(
    "/job/{job_id}",
    response_model=SkillGapAnalysisResponse,
)
async def analyze_current_candidate_skill_gap(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillGapAnalysisResponse:
    """Analyze the logged-in candidate against a published job."""

    if current_user.account_type != "CANDIDATE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can use skill-gap analysis.",
        )

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
        analysis = await SkillGapService.analyze(
            db,
            candidate_id,
            job_id,
        )

        return SkillGapAnalysisResponse(
            candidate_id=analysis.candidate_id,
            job_id=analysis.job_id,
            job_title=analysis.job_title,
            matched_skills=analysis.matched_skills,
            missing_required_skills=[
                SkillGapResponse(
                    skill_id=item.skill_id,
                    skill_name=item.skill_name,
                    required_proficiency=item.required_proficiency,
                    requirement_type=item.requirement_type,
                    is_mandatory=item.is_mandatory,
                    candidate_proficiency=item.candidate_proficiency,
                    status=item.status,
                )
                for item in analysis.missing_required_skills
            ],
            missing_preferred_skills=[
                SkillGapResponse(
                    skill_id=item.skill_id,
                    skill_name=item.skill_name,
                    required_proficiency=item.required_proficiency,
                    requirement_type=item.requirement_type,
                    is_mandatory=item.is_mandatory,
                    candidate_proficiency=item.candidate_proficiency,
                    status=item.status,
                )
                for item in analysis.missing_preferred_skills
            ],
            total_required_gaps=analysis.total_required_gaps,
            total_preferred_gaps=analysis.total_preferred_gaps,
            recommendations=[
                CourseRecommendationResponse(
                    course_id=item.course_id,
                    course_title=item.course_title,
                    institution_profile_id=(
                        item.institution_profile_id
                    ),
                    matched_skill_ids=item.matched_skill_ids,
                    matched_skill_names=item.matched_skill_names,
                    coverage_percentage=item.coverage_percentage,
                )
                for item in analysis.recommendations
            ],
        )

    except SkillGapNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc