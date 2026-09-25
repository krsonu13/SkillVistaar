from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.models.candidate_skill import CandidateSkill
from app.models.course import Course
from app.models.course_skill import CourseSkill
from app.models.job import Job
from app.models.job_skill_requirement import JobSkillRequirement
from app.models.organization import Organization
from app.models.skill import Skill


class RecommendationServiceError(Exception):
    pass


class CandidateNotFoundError(RecommendationServiceError):
    pass


@dataclass
class CandidateSkillInfo:
    skill_id: UUID
    skill_name: str
    proficiency: str


class RecommendationService:
    PROFICIENCY_SCORE = {
        "BEGINNER": 25,
        "INTERMEDIATE": 50,
        "ADVANCED": 75,
        "EXPERT": 100,
    }

    PROFICIENCY_RANK = {
        "BEGINNER": 1,
        "INTERMEDIATE": 2,
        "ADVANCED": 3,
        "EXPERT": 4,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_candidate_profile(
        self,
        user_id: UUID,
    ) -> CandidateProfile:
        result = await self.db.execute(
            select(CandidateProfile).where(
                CandidateProfile.user_id == user_id
            )
        )

        profile = result.scalar_one_or_none()

        if profile is None:
            raise CandidateNotFoundError(
                "Candidate profile not found."
            )

        return profile

    async def get_verified_skills(
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
                CandidateSkill.candidate_profile_id == profile_id,
                CandidateSkill.status == "VERIFIED",
                Skill.is_active.is_(True),
            )
        )

        skills: dict[UUID, CandidateSkillInfo] = {}

        for candidate_skill, skill in result.all():
            skills[skill.id] = CandidateSkillInfo(
                skill_id=skill.id,
                skill_name=skill.name,
                proficiency=candidate_skill.proficiency_level,
            )

        return skills

    def proficiency_rank(
        self,
        proficiency: str | None,
    ) -> int:
        if not proficiency:
            return 0

        return self.PROFICIENCY_RANK.get(
            proficiency.upper(),
            0,
        )

    def calculate_skill_score(
        self,
        required: str,
        candidate: str | None,
    ) -> float:
        if not candidate:
            return 0.0

        required_rank = self.proficiency_rank(required)
        candidate_rank = self.proficiency_rank(candidate)

        if required_rank <= 0:
            return 0.0

        if candidate_rank >= required_rank:
            return 100.0

        return round(
            (candidate_rank / required_rank) * 100,
            2,
        )

    async def recommend_jobs(
        self,
        user_id: UUID,
        limit: int = 20,
    ):
        profile = await self.get_candidate_profile(user_id)
        candidate_skills = await self.get_verified_skills(
            profile.id
        )

        result = await self.db.execute(
            select(
                Job,
                Organization,
            )
            .join(
                Organization,
                Organization.id == Job.organization_id,
            )
            .where(
                Job.status == "PUBLISHED",
                Organization.verification_status == "APPROVED",
                Organization.is_active.is_(True),
            )
            .order_by(Job.created_at.desc())
            .limit(200)
        )

        jobs = result.all()

        recommendations = []

        for job, organization in jobs:
            requirements_result = await self.db.execute(
                select(
                    JobSkillRequirement,
                    Skill,
                )
                .join(
                    Skill,
                    Skill.id == JobSkillRequirement.skill_id,
                )
                .where(
                    JobSkillRequirement.job_id == job.id
                )
            )

            requirements = requirements_result.all()

            if not requirements:
                continue

            skill_matches = []
            skill_gaps = []

            total_weight = 0.0
            weighted_score = 0.0

            for requirement, skill in requirements:
                candidate_skill = candidate_skills.get(
                    skill.id
                )

                required_level = (
                    requirement.proficiency_level
                    or "INTERMEDIATE"
                )

                candidate_level = (
                    candidate_skill.proficiency
                    if candidate_skill
                    else None
                )

                score = self.calculate_skill_score(
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

                    skill_matches.append(
                        {
                            "skill_id": skill.id,
                            "skill_name": skill.name,
                            "required_proficiency": required_level,
                            "candidate_proficiency": candidate_level,
                            "status": status,
                            "contribution": round(
                                score,
                                2,
                            ),
                        }
                    )

                if (
                    not candidate_skill
                    or score < 100
                ):
                    priority = (
                        "HIGH"
                        if requirement.is_mandatory
                        else "MEDIUM"
                    )

                    reason = (
                        f"{skill.name} is required at "
                        f"{required_level} level."
                    )

                    skill_gaps.append(
                        {
                            "skill_id": skill.id,
                            "skill_name": skill.name,
                            "required_proficiency": required_level,
                            "candidate_proficiency": candidate_level,
                            "priority": priority,
                            "reason": reason,
                        }
                    )

            if total_weight == 0:
                continue

            match_score = round(
                weighted_score / total_weight,
                2,
            )

            if match_score >= 80:
                match_level = "EXCELLENT"
            elif match_score >= 65:
                match_level = "GOOD"
            elif match_score >= 50:
                match_level = "POTENTIAL"
            else:
                match_level = "LOW"

            explanation = (
                f"You match approximately "
                f"{match_score}% of the required skills "
                f"for this role. "
            )

            if skill_gaps:
                explanation += (
                    f"{len(skill_gaps)} skill gap(s) "
                    "should be addressed."
                )
            else:
                explanation += (
                    "Your verified skills cover all "
                    "listed requirements."
                )

            recommendations.append(
                {
                    "job_id": job.id,
                    "job_title": job.title,
                    "organization_id": organization.id,
                    "organization_name": organization.name,
                    "match_score": match_score,
                    "match_level": match_level,
                    "skill_matches": skill_matches,
                    "skill_gaps": skill_gaps,
                    "explanation": explanation,
                }
            )

        recommendations.sort(
            key=lambda item: item["match_score"],
            reverse=True,
        )

        return recommendations[:limit]

    async def recommend_courses(
        self,
        user_id: UUID,
        limit: int = 20,
    ):
        profile = await self.get_candidate_profile(user_id)

        candidate_skills = await self.get_verified_skills(
            profile.id
        )

        # Course recommendations primarily target
        # missing verified skills.
        result = await self.db.execute(
            select(Course).where(
                Course.status == "PUBLISHED"
            )
            .order_by(Course.created_at.desc())
            .limit(200)
        )

        courses = list(result.scalars().all())

        recommendations = []

        for course in courses:
            result = await self.db.execute(
                select(
                    CourseSkill,
                    Skill,
                )
                .join(
                    Skill,
                    Skill.id == CourseSkill.skill_id,
                )
                .where(
                    CourseSkill.course_id == course.id
                )
            )

            course_skills = result.all()

            if not course_skills:
                continue

            covered = []
            missing = []

            for course_skill, skill in course_skills:
                if skill.id in candidate_skills:
                    covered.append(skill.name)
                else:
                    missing.append(skill.name)

            if not missing:
                continue

            score = round(
                min(
                    100,
                    (
                        len(missing)
                        / len(course_skills)
                    )
                    * 100,
                ),
                2,
            )

            institution_name = "Training Institution"

            recommendations.append(
                {
                    "course_id": course.id,
                    "course_title": course.title,
                    "institution_name": institution_name,
                    "match_score": score,
                    "skills_covered": covered,
                    "skills_addressed": missing,
                    "explanation": (
                        "This course covers "
                        f"{len(missing)} skill(s) "
                        "that are not currently "
                        "verified in your profile."
                    ),
                }
            )

        recommendations.sort(
            key=lambda item: item["match_score"],
            reverse=True,
        )

        return recommendations[:limit]

    async def dashboard(
        self,
        user_id: UUID,
        job_limit: int = 10,
        course_limit: int = 10,
    ):
        profile = await self.get_candidate_profile(user_id)

        jobs = await self.recommend_jobs(
            user_id,
            limit=job_limit,
        )

        courses = await self.recommend_courses(
            user_id,
            limit=course_limit,
        )

        return {
            "candidate_profile_id": profile.id,
            "recommended_jobs": jobs,
            "recommended_courses": courses,
        }