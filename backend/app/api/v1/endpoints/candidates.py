from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.candidate_credential import CandidateCredential, CredentialStatus
from app.models.candidate_profile import CandidateProfile, CandidateProfileStatus
from app.models.candidate_skill import CandidateSkill, CandidateSkillStatus
from app.models.skill import Skill
from app.models.user import User
from app.schemas.candidate_credential import (
    CandidateCredentialCreate,
    CandidateCredentialResponse,
)
from app.schemas.candidate_skill import CandidateSkillResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)


class SkillTransitionRequest(BaseModel):
    status: str = Field(
        ...,
        pattern="^(SELF_DECLARED|PENDING|VERIFIED|REJECTED|EXPIRED|REVOKED)$",
    )
    notes: str | None = Field(default=None, max_length=1000)
    expires_at: datetime | None = None


class CredentialTransitionRequest(BaseModel):
    status: str = Field(
        ...,
        pattern="^(UPLOADED|PENDING_VERIFICATION|VERIFIED|REJECTED|MORE_INFORMATION_REQUIRED|EXPIRED|REVOKED)$",
    )
    notes: str | None = Field(default=None, max_length=1000)


def require_candidate(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
) -> tuple[User, list[str]]:
    user, roles = current_user_and_roles
    is_candidate = user.account_type == "CANDIDATE" or "CANDIDATE" in roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    if not is_candidate and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Candidates.",
        )
    return current_user_and_roles


class CandidateProfileUpdatePayload(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    current_occupation: str | None = None
    years_of_experience: float | None = None
    highest_qualification: str | None = None
    preferred_location: str | None = None
    preferred_job_type: str | None = None
    preferred_workplace_type: str | None = None
    profile_photo_path: str | None = None
    cover_photo_path: str | None = None
    education: list[dict[str, Any]] | None = None
    experience: list[dict[str, Any]] | None = None
    projects: list[dict[str, Any]] | None = None
    certifications: list[dict[str, Any]] | None = None
    courses_completed: list[dict[str, Any]] | None = None
    achievements: list[dict[str, Any]] | None = None
    languages: list[dict[str, Any]] | None = None
    career_preferences: dict[str, Any] | None = None


def compute_completion_percentage(profile: CandidateProfile, skills_count: int = 0) -> int:
    score = 0
    if profile.first_name and profile.first_name.strip():
        score += 10
    if profile.headline and profile.headline.strip():
        score += 10
    if profile.bio and profile.bio.strip():
        score += 10
    if profile.preferred_location and profile.preferred_location.strip():
        score += 10
    if profile.profile_photo_path and profile.profile_photo_path.strip():
        score += 10
    if profile.cover_photo_path and profile.cover_photo_path.strip():
        score += 5
    if skills_count > 0 or (profile.languages and len(profile.languages) > 0):
        score += 15
    if profile.education and len(profile.education) > 0:
        score += 10
    if profile.experience and len(profile.experience) > 0:
        score += 10
    if (profile.projects and len(profile.projects) > 0) or (profile.certifications and len(profile.certifications) > 0):
        score += 10
    if profile.career_preferences and len(profile.career_preferences) > 0:
        score += 10
    return min(100, score)


def format_candidate_profile_dict(profile: CandidateProfile, user: User) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "username": user.username,
        "email": user.email,
        "first_name": profile.first_name,
        "middle_name": profile.middle_name,
        "last_name": profile.last_name,
        "full_name": f"{profile.first_name} {profile.last_name or ''}".strip(),
        "headline": profile.headline,
        "bio": profile.bio,
        "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
        "gender": profile.gender,
        "current_occupation": profile.current_occupation,
        "years_of_experience": profile.years_of_experience,
        "highest_qualification": profile.highest_qualification,
        "preferred_location": profile.preferred_location,
        "preferred_job_type": profile.preferred_job_type,
        "preferred_workplace_type": profile.preferred_workplace_type,
        "profile_photo_path": profile.profile_photo_path,
        "cover_photo_path": profile.cover_photo_path,
        "resume_path": profile.resume_path,
        "profile_completion_percentage": profile.profile_completion_percentage,
        "status": profile.status,
        "is_public": profile.is_public,
        "education": profile.education or [],
        "experience": profile.experience or [],
        "projects": profile.projects or [],
        "certifications": profile.certifications or [],
        "courses_completed": profile.courses_completed or [],
        "achievements": profile.achievements or [],
        "languages": profile.languages or [],
        "career_preferences": profile.career_preferences or {},
        "government_unit_id": str(profile.government_unit_id) if profile.government_unit_id else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("/me/profile")
async def get_candidate_profile(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current logged in candidate's complete profile.
    """
    user, roles = current_user_and_roles
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        name_part = (user.email.split("@")[0] if user.email else "Candidate").capitalize()
        profile = CandidateProfile(
            user_id=user.id,
            first_name=name_part,
            status=CandidateProfileStatus.ACTIVE.value,
            is_public=True,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    # Count skills for completion calculation
    sk_res = await db.execute(
        select(func.count(CandidateSkill.id)).where(CandidateSkill.candidate_profile_id == profile.id)
    )
    sk_count = sk_res.scalar() or 0
    calculated_pct = compute_completion_percentage(profile, sk_count)
    if profile.profile_completion_percentage != calculated_pct:
        profile.profile_completion_percentage = calculated_pct
        await db.commit()
        await db.refresh(profile)

    return format_candidate_profile_dict(profile, user)


@router.put("/me/profile")
async def update_candidate_profile(
    payload: CandidateProfileUpdatePayload,
    current_user_and_roles: tuple[User, list[str]] = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update candidate's profile, including bio, headline, education, experience,
    projects, certifications, languages, and recalculate completion percentage.
    """
    user, roles = current_user_and_roles
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=user.id,
            first_name=user.email.split("@")[0].capitalize() if user.email else "Candidate",
            status=CandidateProfileStatus.ACTIVE.value,
            is_public=True,
        )
        db.add(profile)
        await db.flush()

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, val)

    # Recalculate profile completion percentage
    sk_res = await db.execute(
        select(func.count(CandidateSkill.id)).where(CandidateSkill.candidate_profile_id == profile.id)
    )
    sk_count = sk_res.scalar() or 0
    profile.profile_completion_percentage = compute_completion_percentage(profile, sk_count)

    await db.commit()
    await db.refresh(profile)

    return format_candidate_profile_dict(profile, user)


@router.get("/me/skills", response_model=list[CandidateSkillResponse])
async def get_candidate_skills(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
) -> list[CandidateSkill]:
    """
    Get current candidate's declared and verified skills.
    """
    user, _ = current_user_and_roles
    profile_res = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(CandidateSkill).where(CandidateSkill.candidate_profile_id == profile.id)
    )
    return list(result.scalars().all())


@router.get("/me/credentials", response_model=list[CandidateCredentialResponse])
async def get_candidate_credentials(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_candidate),
    db: AsyncSession = Depends(get_db),
) -> list[CandidateCredential]:
    """
    Get current candidate's uploaded and verified credentials.
    """
    user, _ = current_user_and_roles
    profile_res = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(CandidateCredential).where(
            CandidateCredential.candidate_profile_id == profile.id
        )
    )
    return list(result.scalars().all())


@router.post("/me/credentials", response_model=CandidateCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_credential(
    payload: CandidateCredentialCreate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> CandidateCredential:
    """
    Candidate uploads a new credential or qualification certificate.
    """
    user, _ = current_user_and_roles
    profile_res = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=user.id,
            first_name=user.email.split("@")[0].capitalize(),
            last_name="Candidate",
            status=CandidateProfileStatus.ACTIVE.value,
        )
        db.add(profile)
        await db.flush()

    cred_type = (
        payload.credential_type.value
        if hasattr(payload.credential_type, "value")
        else str(payload.credential_type)
    )
    issuer = payload.issuing_organization_name or payload.issuer_name or "Unknown Issuer"
    issue_dt = payload.issue_date or payload.issued_date

    cred = CandidateCredential(
        candidate_profile_id=profile.id,
        credential_type=cred_type,
        title=payload.title,
        credential_number=payload.credential_number,
        issuing_organization_name=issuer,
        issue_date=issue_dt,
        expiry_date=payload.expiry_date,
        document_path=payload.document_url,
        document_hash=payload.document_hash,
        status=CredentialStatus.UPLOADED.value,
        is_public=payload.is_public,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


@router.post("/skills/{skill_id}/transition", response_model=CandidateSkillResponse)
async def transition_skill_status(
    skill_id: UUID,
    transition: SkillTransitionRequest,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> CandidateSkill:
    """
    Transition candidate skill state across verifiable lifecycle:
    SELF_DECLARED -> PENDING -> VERIFIED | REJECTED | EXPIRED | REVOKED
    """
    user, roles = current_user_and_roles

    # Check that caller has verification authority
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_verifier = (
        is_admin
        or user.account_type in ("GOVERNMENT", "EMPLOYER", "TRAINING_INSTITUTE")
        or any("VERIFIER" in r or "ADMIN" in r for r in roles)
    )

    if not is_verifier and transition.status in ("VERIFIED", "REJECTED", "REVOKED"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorized training institutes, employers, or government verifiers can verify skills.",
        )

    cand_skill = await db.get(CandidateSkill, skill_id)
    if not cand_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate skill '{skill_id}' not found.",
        )

    old_status = cand_skill.status
    cand_skill.status = transition.status
    cand_skill.verification_notes = transition.notes

    now = datetime.now(timezone.utc)
    if transition.status == CandidateSkillStatus.VERIFIED.value:
        cand_skill.verified_by_user_id = user.id
        cand_skill.verified_at = now
        cand_skill.expires_at = transition.expires_at
    elif transition.status in (CandidateSkillStatus.REVOKED.value, CandidateSkillStatus.REJECTED.value):
        cand_skill.verified_by_user_id = user.id

    # Record in Audit Log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.APPROVE if transition.status == "VERIFIED" else AuditAction.UPDATE,
        resource_type="candidate_skill",
        resource_id=cand_skill.id,
        description=f"Skill status transitioned from {old_status} to {transition.status}.",
        metadata_json={
            "old_status": old_status,
            "new_status": transition.status,
            "verifier_id": str(user.id),
            "notes": transition.notes,
        },
    )

    await db.commit()
    await db.refresh(cand_skill)
    return cand_skill


@router.post("/credentials/{credential_id}/transition", response_model=CandidateCredentialResponse)
async def transition_credential_status(
    credential_id: UUID,
    transition: CredentialTransitionRequest,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> CandidateCredential:
    """
    Transition candidate credential state across verifiable lifecycle:
    UPLOADED -> PENDING_VERIFICATION -> VERIFIED | REJECTED | EXPIRED | REVOKED
    """
    user, roles = current_user_and_roles

    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_verifier = (
        is_admin
        or user.account_type in ("GOVERNMENT", "EMPLOYER", "TRAINING_INSTITUTE")
        or any("VERIFIER" in r or "ADMIN" in r for r in roles)
    )

    if not is_verifier and transition.status in ("VERIFIED", "REJECTED", "REVOKED"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorized institutions, employers, or government verifiers can verify credentials.",
        )

    credential = await db.get(CandidateCredential, credential_id)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate credential '{credential_id}' not found.",
        )

    old_status = credential.status
    credential.status = transition.status
    credential.verification_notes = transition.notes

    now = datetime.now(timezone.utc)
    if transition.status == CredentialStatus.VERIFIED.value:
        credential.verified_by_user_id = user.id
        credential.verified_at = now
    elif transition.status in (CredentialStatus.REVOKED.value, CredentialStatus.REJECTED.value):
        credential.verified_by_user_id = user.id

    # Record in Audit Log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.APPROVE if transition.status == "VERIFIED" else AuditAction.UPDATE,
        resource_type="candidate_credential",
        resource_id=credential.id,
        description=f"Credential status transitioned from {old_status} to {transition.status}.",
        metadata_json={
            "old_status": old_status,
            "new_status": transition.status,
            "verifier_id": str(user.id),
            "notes": transition.notes,
        },
    )

    await db.commit()
    await db.refresh(credential)
    return credential
