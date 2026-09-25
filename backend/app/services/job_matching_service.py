from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import CandidateSkill, CandidateSkillStatus
from app.models.job import Job
from app.models.job_skill_requirement import (
    JobSkillRequirement,
    SkillProficiencyLevel,
    SkillRequirementType,
)


class JobMatchingServiceError(Exception):
    """Base error for job matching."""


class JobMatchingNotFoundError(JobMatchingServiceError):
    """Candidate or job was not found."""


class JobMatchingValidationError(JobMatchingServiceError):
    """Invalid matching request."""


@dataclass
class SkillMatch:
    skill_id: uuid.UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    requirement_type: str
    is_verified: bool
    matched: bool


@dataclass
class JobMatchResult:
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
    skill_matches: list[SkillMatch]


class JobMatchingService:
    """Explainable candidate-to-job matching."""

    PROFICIENCY_RANK = {
        SkillProficiencyLevel.BEGINNER.value: 1,
        SkillProficiencyLevel.INTERMEDIATE.value: 2,
        SkillProficiencyLevel.ADVANCED.value: 3,
        SkillProficiencyLevel.EXPERT.value: 4,
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
            raise JobMatchingNotFoundError(
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
            raise JobMatchingNotFoundError(
                "Published job not found."
            )

        return job

    @classmethod
    async def get_verified_candidate_skills(
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
            candidate_skill.skill_id: candidate_skill
            for candidate_skill in skills
        }

    @classmethod
    def calculate_score(
        cls,
        required_total: int,
        required_matched: int,
        preferred_total: int,
        preferred_matched: int,
    ) -> float:
        """
        Required skills carry 80% of the score.
        Preferred skills carry 20%.
        """

        required_score = (
            required_matched / required_total
            if required_total
            else 1.0
        )

        preferred_score = (
            preferred_matched / preferred_total
            if preferred_total
            else 1.0
        )

        score = (
            (required_score * 80.0)
            + (preferred_score * 20.0)
        )

        return round(min(score, 100.0), 2)

    @classmethod
    def proficiency_matches(
        cls,
        candidate_level: str,
        required_level: str,
    ) -> bool:
        candidate_rank = cls.PROFICIENCY_RANK.get(
            candidate_level,
            0,
        )

        required_rank = cls.PROFICIENCY_RANK.get(
            required_level,
            0,
        )

        return candidate_rank >= required_rank

    @classmethod
    async def match_candidate_to_job(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> JobMatchResult:
        candidate = await cls.get_candidate(
            db,
            candidate_id,
        )

        job = await cls.get_job(
            db,
            job_id,
        )

        candidate_skills = await cls.get_verified_candidate_skills(
            db,
            candidate.id,
        )

        required_total = 0
        required_matched = 0

        preferred_total = 0
        preferred_matched = 0

        missing_required: list[str] = []
        missing_preferred: list[str] = []
        matched_skills: list[str] = []
        skill_matches: list[SkillMatch] = []

        for requirement in job.skill_requirements:
            skill = requirement.skill

            if skill is None:
                continue

            requirement_type = requirement.requirement_type

            is_required = (
                requirement_type
                == SkillRequirementType.REQUIRED.value
                or requirement.is_mandatory
            )

            if is_required:
                required_total += 1
            else:
                preferred_total += 1

            candidate_skill = candidate_skills.get(
                requirement.skill_id
            )

            candidate_proficiency = (
                candidate_skill.proficiency_level
                if candidate_skill
                else None
            )

            is_verified = candidate_skill is not None

            matched = False

            if candidate_skill is not None:
                matched = cls.proficiency_matches(
                    candidate_skill.proficiency_level,
                    requirement.proficiency_level,
                )

            skill_name = skill.name

            skill_matches.append(
                SkillMatch(
                    skill_id=skill.id,
                    skill_name=skill_name,
                    required_proficiency=(
                        requirement.proficiency_level
                    ),
                    candidate_proficiency=candidate_proficiency,
                    requirement_type=requirement_type,
                    is_verified=is_verified,
                    matched=matched,
                )
            )

            if matched:
                matched_skills.append(skill_name)

                if is_required:
                    required_matched += 1
                else:
                    preferred_matched += 1

            else:
                if is_required:
                    missing_required.append(skill_name)
                else:
                    missing_preferred.append(skill_name)

        score = cls.calculate_score(
            required_total=required_total,
            required_matched=required_matched,
            preferred_total=preferred_total,
            preferred_matched=preferred_matched,
        )

        return JobMatchResult(
            job_id=job.id,
            candidate_id=candidate.id,
            score=score,
            required_skills=required_total,
            matched_required_skills=required_matched,
            preferred_skills=preferred_total,
            matched_preferred_skills=preferred_matched,
            missing_required_skills=missing_required,
            missing_preferred_skills=missing_preferred,
            matched_skills=matched_skills,
            skill_matches=skill_matches,
        )

    @classmethod
    async def match_candidate_to_published_jobs(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        minimum_score: float = 0.0,
        limit: int = 20,
    ) -> list[JobMatchResult]:
        if not 0 <= minimum_score <= 100:
            raise JobMatchingValidationError(
                "Minimum score must be between 0 and 100."
            )

        if not 1 <= limit <= 100:
            raise JobMatchingValidationError(
                "Limit must be between 1 and 100."
            )

        candidate = await cls.get_candidate(
            db,
            candidate_id,
        )

        candidate_skills = await cls.get_verified_candidate_skills(
            db,
            candidate.id,
        )

        result = await db.execute(
            select(Job)
            .options(
                selectinload(Job.skill_requirements).selectinload(
                    JobSkillRequirement.skill
                )
            )
            .where(Job.status == "PUBLISHED")
        )

        jobs = result.scalars().unique().all()

        matches: list[JobMatchResult] = []

        for job in jobs:
            required_total = 0
            required_matched = 0
            preferred_total = 0
            preferred_matched = 0

            missing_required: list[str] = []
            missing_preferred: list[str] = []
            matched_skills: list[str] = []
            skill_matches: list[SkillMatch] = []

            for requirement in job.skill_requirements:
                skill = requirement.skill

                if skill is None:
                    continue

                is_required = (
                    requirement.requirement_type
                    == SkillRequirementType.REQUIRED.value
                    or requirement.is_mandatory
                )

                if is_required:
                    required_total += 1
                else:
                    preferred_total += 1

                candidate_skill = candidate_skills.get(
                    requirement.skill_id
                )

                candidate_proficiency = (
                    candidate_skill.proficiency_level
                    if candidate_skill
                    else None
                )

                matched = False

                if candidate_skill:
                    matched = cls.proficiency_matches(
                        candidate_skill.proficiency_level,
                        requirement.proficiency_level,
                    )

                skill_matches.append(
                    SkillMatch(
                        skill_id=skill.id,
                        skill_name=skill.name,
                        required_proficiency=(
                            requirement.proficiency_level
                        ),
                        candidate_proficiency=candidate_proficiency,
                        requirement_type=(
                            requirement.requirement_type
                        ),
                        is_verified=candidate_skill is not None,
                        matched=matched,
                    )
                )

                if matched:
                    matched_skills.append(skill.name)

                    if is_required:
                        required_matched += 1
                    else:
                        preferred_matched += 1
                else:
                    if is_required:
                        missing_required.append(skill.name)
                    else:
                        missing_preferred.append(skill.name)

            score = cls.calculate_score(
                required_total=required_total,
                required_matched=required_matched,
                preferred_total=preferred_total,
                preferred_matched=preferred_matched,
            )

            if score < minimum_score:
                continue

            matches.append(
                JobMatchResult(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    score=score,
                    required_skills=required_total,
                    matched_required_skills=required_matched,
                    preferred_skills=preferred_total,
                    matched_preferred_skills=preferred_matched,
                    missing_required_skills=missing_required,
                    missing_preferred_skills=missing_preferred,
                    matched_skills=matched_skills,
                    skill_matches=skill_matches,
                )
            )

        matches.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return matches[:limit]