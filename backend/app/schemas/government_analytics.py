from uuid import UUID

from pydantic import BaseModel, Field


class DemandSupplyOverview(BaseModel):
    records: int
    total_demand: int
    total_supply: int
    demand_supply_gap: int


class OccupationDemandItem(BaseModel):
    occupation_name: str
    demand: int
    supply: int
    gap: int


class EmergingSkillItem(BaseModel):
    skill_id: UUID
    skill_name: str
    growth_rate: float
    demand_count: int


class PlacementOverview(BaseModel):
    total_learners: int
    placed_learners: int
    placement_rate: float


class CourseAlignmentOverview(BaseModel):
    total: int
    by_status: dict[str, int]


class GovernmentDashboardResponse(BaseModel):
    government_unit_id: UUID | None
    demand_supply: DemandSupplyOverview
    top_occupations: list[OccupationDemandItem]
    emerging_skills: list[EmergingSkillItem]
    placement: PlacementOverview
    course_alignment: CourseAlignmentOverview