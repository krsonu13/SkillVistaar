from uuid import UUID

from pydantic import BaseModel, Field


class SkillMatchItem(BaseModel):
    skill_id: UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    status: str
    contribution: float


class SkillGapItem(BaseModel):
    skill_id: UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    priority: str
    reason: str


class JobRecommendationResponse(BaseModel):
    job_id: UUID
    job_title: str
    organization_id: UUID
    organization_name: str
    match_score: float = Field(ge=0, le=100)
    match_level: str
    skill_matches: list[SkillMatchItem]
    skill_gaps: list[SkillGapItem]
    explanation: str


class CourseRecommendationResponse(BaseModel):
    course_id: UUID
    course_title: str
    institution_name: str
    match_score: float = Field(ge=0, le=100)
    skills_covered: list[str]
    skills_addressed: list[str]
    explanation: str


class CandidateRecommendationDashboard(BaseModel):
    candidate_profile_id: UUID
    recommended_jobs: list[JobRecommendationResponse]
    recommended_courses: list[CourseRecommendationResponse]