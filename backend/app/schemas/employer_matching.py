from uuid import UUID

from pydantic import BaseModel, Field


class CandidateMatchSkill(BaseModel):
    skill_id: UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    status: str
    score: float = Field(ge=0, le=100)


class CandidateMatchGap(BaseModel):
    skill_id: UUID
    skill_name: str
    required_proficiency: str
    candidate_proficiency: str | None
    priority: str
    reason: str


class EmployerCandidateMatchResponse(BaseModel):
    candidate_profile_id: UUID
    candidate_name: str
    headline: str | None
    match_score: float = Field(ge=0, le=100)
    match_level: str
    matched_skills: list[CandidateMatchSkill]
    skill_gaps: list[CandidateMatchGap]
    explanation: str


class EmployerJobMatchesResponse(BaseModel):
    job_id: UUID
    job_title: str
    total_candidates: int
    matches: list[EmployerCandidateMatchResponse]