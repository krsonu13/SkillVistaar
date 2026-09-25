from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import CandidateSkill, CandidateSkillStatus
from app.models.course import Course, CourseStatus
from app.models.course_skill import CourseSkill
from app.models.job import Job
from app.models.job_skill_requirement import (
    JobSkillRequirement,
    SkillRequirementType,
)
from app.models.skill import Skill


class SkillGapServiceError(Exception):
    """Base error for skill-gap analysis."""


class SkillGapNotFoundError(SkillGapServiceError):
    """Requested candidate, job, or skill was not found."""


class SkillGapValidationError(SkillGapServiceError):
    """Invalid skill-gap request."""


@dataclass
class SkillGap:
    skill_id: uuid.UUID
    skill_name: str
    required_proficiency: str
    requirement_type: str
    is_mandatory: bool
    candidate_proficiency: str | None
    status: str


@dataclass
class CourseRecommendation:
    course_id: uuid.UUID
    course_title: str
    institution_profile_id: uuid.UUID
    matched_skill_ids: list[uuid.UUID] = field(default_factory=list)
    matched_skill_names: list[str] = field(default_factory=list)
    coverage_percentage: float = 0.0


@dataclass
class SkillGapResult:
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    matched_skills: list[str]
    missing_required_skills: list[SkillGap]
    missing_preferred_skills: list[SkillGap]
    total_required_gaps: int
    total_preferred_gaps: int
    recommendations: list[CourseRecommendation]


class SkillGapService:
    """Analyze candidate skill gaps and recommend relevant courses."""

    PROFICIENCY_RANK = {
        "BEGINNER": 1,
        "INTERMEDIATE": 2,
        "ADVANCED": 3,
        "EXPERT": 4,
    }

    @classmethod
    async def get_candidate(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> CandidateProfile:
        result = await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == candidate_id
            )
        )

        candidate = result.scalar_one_or_none()

        if candidate is None:
            raise SkillGapNotFoundError(
                "Candidate profile not found."
            )

        return candidate

    @classmethod
    async def get_job(
        cls,
        db: AsyncSession,
        job_id: uuid.UUID,
    ) -> Job:
        result = await db.execute(
            select(Job)
            .options(
                selectinload(Job.skill_requirements).selectinload(
                    JobSkillRequirement.skill
                )
            )
            .where(
                Job.id == job_id,
                Job.status == "PUBLISHED",
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            raise SkillGapNotFoundError(
                "Published job not found."
            )

        return job

    @classmethod
    async def get_verified_skills(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
    ) -> dict[uuid.UUID, CandidateSkill]:
        result = await db.execute(
            select(CandidateSkill)
            .options(selectinload(CandidateSkill.skill))
            .where(
                CandidateSkill.candidate_profile_id == candidate_id,
                CandidateSkill.status
                == CandidateSkillStatus.VERIFIED.value,
            )
        )

        skills = result.scalars().all()

        return {
            item.skill_id: item
            for item in skills
        }

    @classmethod
    def proficiency_matches(
        cls,
        candidate_level: str,
        required_level: str,
    ) -> bool:
        return (
            cls.PROFICIENCY_RANK.get(candidate_level, 0)
            >= cls.PROFICIENCY_RANK.get(required_level, 0)
        )

    @classmethod
    async def recommend_courses(
        cls,
        db: AsyncSession,
        missing_skill_ids: list[uuid.UUID],
    ) -> list[CourseRecommendation]:
        if not missing_skill_ids:
            return []

        result = await db.execute(
            select(Course)
            .options(
                selectinload(Course.skill_mappings).selectinload(
                    CourseSkill.skill
                )
            )
            .where(
                Course.status == CourseStatus.PUBLISHED.value,
            )
        )

        courses = result.scalars().unique().all()

        recommendations: list[CourseRecommendation] = []

        missing_set = set(missing_skill_ids)

        for course in courses:
            matched_ids: list[uuid.UUID] = []
            matched_names: list[str] = []

            for mapping in course.skill_mappings:
                if mapping.skill_id not in missing_set:
                    continue

                matched_ids.append(mapping.skill_id)

                if mapping.skill is not None:
                    matched_names.append(mapping.skill.name)

            if not matched_ids:
                continue

            coverage = (
                len(set(matched_ids))
                / len(missing_set)
            ) * 100

            recommendations.append(
                CourseRecommendation(
                    course_id=course.id,
                    course_title=course.title,
                    institution_profile_id=course.institution_profile_id,
                    matched_skill_ids=matched_ids,
                    matched_skill_names=matched_names,
                    coverage_percentage=round(
                        coverage,
                        2,
                    ),
                )
            )

        recommendations.sort(
            key=lambda item: (
                item.coverage_percentage,
                len(item.matched_skill_ids),
            ),
            reverse=True,
        )

        return recommendations[:10]

    @classmethod
    async def analyze(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> SkillGapResult:
        candidate = await cls.get_candidate(
            db,
            candidate_id,
        )

        job = await cls.get_job(
            db,
            job_id,
        )

        verified_skills = await cls.get_verified_skills(
            db,
            candidate.id,
        )

        matched_skills: list[str] = []
        missing_required: list[SkillGap] = []
        missing_preferred: list[SkillGap] = []

        for requirement in job.skill_requirements:
            skill = requirement.skill

            if skill is None:
                continue

            candidate_skill = verified_skills.get(
                requirement.skill_id
            )

            if candidate_skill is not None:
                if cls.proficiency_matches(
                    candidate_skill.proficiency_level,
                    requirement.proficiency_level,
                ):
                    matched_skills.append(skill.name)
                    continue

            is_required = (
                requirement.requirement_type
                == SkillRequirementType.REQUIRED.value
                or requirement.is_mandatory
            )

            gap = SkillGap(
                skill_id=skill.id,
                skill_name=skill.name,
                required_proficiency=(
                    requirement.proficiency_level
                ),
                requirement_type=(
                    requirement.requirement_type
                ),
                is_mandatory=requirement.is_mandatory,
                candidate_proficiency=(
                    candidate_skill.proficiency_level
                    if candidate_skill
                    else None
                ),
                status=(
                    "INSUFFICIENT_PROFICIENCY"
                    if candidate_skill
                    else "MISSING"
                ),
            )

            if is_required:
                missing_required.append(gap)
            else:
                missing_preferred.append(gap)

        all_missing_ids = [
            item.skill_id
            for item in (
                missing_required + missing_preferred
            )
        ]

        recommendations = await cls.recommend_courses(
            db,
            all_missing_ids,
        )

        return SkillGapResult(
            candidate_id=candidate.id,
            job_id=job.id,
            job_title=job.title,
            matched_skills=matched_skills,
            missing_required_skills=missing_required,
            missing_preferred_skills=missing_preferred,
            total_required_gaps=len(missing_required),
            total_preferred_gaps=len(missing_preferred),
            recommendations=recommendations,
        )