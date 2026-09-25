from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import CandidateSkill
from app.models.job import Job
from app.models.job_skill_requirement import JobSkillRequirement
from app.models.organization_member import OrganizationMember
from app.models.skill import Skill


class EmployerMatchingError(Exception):
    pass


class EmployerMatchingNotFoundError(EmployerMatchingError):
    pass


class EmployerMatchingAccessDeniedError(EmployerMatchingError):
    pass


@dataclass
class CandidateSkillInfo:
    skill_id: UUID
    skill_name: str
    proficiency: str


class EmployerMatchingService:

    PROFICIENCY_RANK = {
        "BEGINNER": 1,
        "INTERMEDIATE": 2,
        "ADVANCED": 3,
        "EXPERT": 4,
    }

    MANAGER_ROLES = {
        "ORG_ADMIN",
        "HR",
        "JOB_POSTER",
        "ASSESSMENT_MANAGER",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    def rank(
        self,
        proficiency: str | None,
    ) -> int:
        if not proficiency:
            return 0

        return self.PROFICIENCY_RANK.get(
            proficiency.upper(),
            0,
        )

    def calculate_score(
        self,
        required: str,
        candidate: str | None,
    ) -> float:
        if not candidate:
            return 0.0

        required_rank = self.rank(required)
        candidate_rank = self.rank(candidate)

        if required_rank <= 0:
            return 0.0

        if candidate_rank >= required_rank:
            return 100.0

        return round(
            candidate_rank / required_rank * 100,
            2,
        )

    async def get_job(
        self,
        job_id: UUID,
    ) -> Job:
        result = await self.db.execute(
            select(Job).where(
                Job.id == job_id
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            raise EmployerMatchingNotFoundError(
                "Job not found."
            )

        return job

    async def verify_employer_access(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        result = await self.db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id
                == organization_id,
                OrganizationMember.is_active.is_(True),
                OrganizationMember.role.in_(
                    self.MANAGER_ROLES
                ),
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            raise EmployerMatchingAccessDeniedError(
                "You do not have permission to view "
                "candidate matches for this organization."
            )

    async def get_job_requirements(
        self,
        job_id: UUID,
    ):
        result = await self.db.execute(
            select(
                JobSkillRequirement,
                Skill,
            )
            .join(
                Skill,
                Skill.id == JobSkillRequirement.skill_id,
            )
            .where(
                JobSkillRequirement.job_id == job_id
            )
        )

        return result.all()

    async def get_candidate_skills(
        self,
        profile_id: UUID,
    ) -> dict[UUID, CandidateSkillInfo]:
        result = await self.db.execute(
            select(
                CandidateSkill,
                Skill,
            )
            .join(
                Skill,
                Skill.id == CandidateSkill.skill_id,
            )
            .where(
                CandidateSkill.candidate_profile_id
                == profile_id,
                CandidateSkill.status == "VERIFIED",
                Skill.is_active.is_(True),
            )
        )

        skills = {}

        for candidate_skill, skill in result.all():
            skills[skill.id] = CandidateSkillInfo(
                skill_id=skill.id,
                skill_name=skill.name,
                proficiency=(
                    candidate_skill.proficiency_level
                ),
            )

        return skills

    async def match_candidate(
        self,
        profile: CandidateProfile,
        requirements,
    ):
        candidate_skills = await self.get_candidate_skills(
            profile.id
        )

        matched_skills = []
        skill_gaps = []

        total_weight = 0.0
        weighted_score = 0.0

        for requirement, skill in requirements:
            required_level = (
                requirement.proficiency_level
                or "INTERMEDIATE"
            )

            candidate_skill = candidate_skills.get(
                skill.id
            )

            candidate_level = (
                candidate_skill.proficiency
                if candidate_skill
                else None
            )

            score = self.calculate_score(
                required_level,
                candidate_level,
            )

            weight = (
                2.0
                if requirement.is_mandatory
                else 1.0
            )

            total_weight += weight
            weighted_score += score * weight

            if candidate_skill:
                status = (
                    "MATCHED"
                    if score >= 100
                    else "PARTIAL"
                )

                matched_skills.append(
                    {
                        "skill_id": skill.id,
                        "skill_name": skill.name,
                        "required_proficiency": (
                            required_level
                        ),
                        "candidate_proficiency": (
                            candidate_level
                        ),
                        "status": status,
                        "score": score,
                    }
                )

            if not candidate_skill or score < 100:
                priority = (
                    "HIGH"
                    if requirement.is_mandatory
                    else "MEDIUM"
                )

                skill_gaps.append(
                    {
                        "skill_id": skill.id,
                        "skill_name": skill.name,
                        "required_proficiency": (
                            required_level
                        ),
                        "candidate_proficiency": (
                            candidate_level
                        ),
                        "priority": priority,
                        "reason": (
                            f"{skill.name} requires "
                            f"{required_level} proficiency."
                        ),
                    }
                )

        if total_weight == 0:
            return None

        match_score = round(
            weighted_score / total_weight,
            2,
        )

        if match_score >= 85:
            match_level = "EXCELLENT"
        elif match_score >= 70:
            match_level = "STRONG"
        elif match_score >= 55:
            match_level = "POTENTIAL"
        else:
            match_level = "LOW"

        candidate_name = (
            " ".join(
                part
                for part in [
                    profile.first_name,
                    profile.last_name,
                ]
                if part
            )
            or "Candidate"
        )

        explanation = (
            f"{candidate_name} matches "
            f"{match_score}% of the job's "
            "skill requirements based on "
            "verified skills."
        )

        if skill_gaps:
            explanation += (
                f" {len(skill_gaps)} skill gap(s) "
                "remain."
            )

        return {
            "candidate_profile_id": profile.id,
            "candidate_name": candidate_name,
            "headline": profile.headline,
            "match_score": match_score,
            "match_level": match_level,
            "matched_skills": matched_skills,
            "skill_gaps": skill_gaps,
            "explanation": explanation,
        }

    async def find_candidates(
        self,
        user_id: UUID,
        job_id: UUID,
        limit: int = 50,
        minimum_score: float = 0,
    ):
        job = await self.get_job(job_id)

        await self.verify_employer_access(
            user_id,
            job.organization_id,
        )

        if job.status != "PUBLISHED":
            raise EmployerMatchingError(
                "Candidate matching is available "
                "only for published jobs."
            )

        requirements = await self.get_job_requirements(
            job.id
        )

        if not requirements:
            return {
                "job_id": job.id,
                "job_title": job.title,
                "total_candidates": 0,
                "matches": [],
            }

        result = await self.db.execute(
            select(CandidateProfile).where(
                CandidateProfile.status == "ACTIVE",
                CandidateProfile.is_public.is_(True),
            )
            .limit(500)
        )

        candidates = list(
            result.scalars().all()
        )

        matches = []

        for candidate in candidates:
            match = await self.match_candidate(
                candidate,
                requirements,
            )

            if match is None:
                continue

            if match["match_score"] < minimum_score:
                continue

            matches.append(match)

        matches.sort(
            key=lambda item: item["match_score"],
            reverse=True,
        )

        return {
            "job_id": job.id,
            "job_title": job.title,
            "total_candidates": len(matches),
            "matches": matches[:limit],
        }