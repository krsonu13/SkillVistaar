from __future__ import annotations

import mimetypes
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles, get_optional_current_user
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import UserResponse
from app.services.storage_service import get_storage_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


class UserProfileUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class UsernameUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)


@router.get("/me", response_model=UserResponse)
async def get_my_user(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current logged in user details.
    """
    from app.services.user_service import resolve_user_verification_status

    user, roles = current_user_and_roles
    v_status = await resolve_user_verification_status(db, user)
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "username": user.username,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "is_suspended": user.is_suspended,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "verification_status": v_status,
        "government_unit_id": str(user.government_unit_id) if user.government_unit_id else None,
        "roles": roles,
    }


@router.patch("/me/username", response_model=UserResponse)
async def update_my_username(
    payload: UsernameUpdateRequest,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update unique username with validation and audit logging.
    """
    from app.services.username_service import is_username_available, normalize_username
    from app.services.user_service import resolve_user_verification_status
    from app.models.audit_log import AuditAction, AuditLog

    user, roles = current_user_and_roles
    clean = normalize_username(payload.username)

    if user.username and user.username.lower() == clean:
        v_status = await resolve_user_verification_status(db, user)
        return {
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "username": user.username,
            "account_type": user.account_type,
            "is_active": user.is_active,
            "is_suspended": user.is_suspended,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "verification_status": v_status,
            "government_unit_id": str(user.government_unit_id) if user.government_unit_id else None,
            "roles": roles,
        }

    is_avail, msg = await is_username_available(db, clean, exclude_user_id=user.id)
    if not is_avail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    old_username = user.username
    user.username = clean

    # Audit log
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action=AuditAction.UPDATE.value,
            resource_type="User",
            resource_id=user.id,
            description=f"Username changed from '@{old_username}' to '@{clean}'",
            metadata_json={"old_username": old_username, "new_username": clean},
        )
    )
    await db.commit()
    await db.refresh(user)

    v_status = await resolve_user_verification_status(db, user)
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "username": user.username,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "is_suspended": user.is_suspended,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "verification_status": v_status,
        "government_unit_id": str(user.government_unit_id) if user.government_unit_id else None,
        "roles": roles,
    }


@router.get("/me/verification-status")
async def get_my_verification_status(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get detailed statutory verification status, application info, submitted documents, and review milestones.
    """
    from app.services.user_service import resolve_user_verification_status
    from app.models.verification_application import VerificationApplication
    from app.models.organization import Organization
    from app.models.organization_document import OrganizationDocument
    from app.models.government_unit import GovernmentUnit

    user, roles = current_user_and_roles
    v_status = await resolve_user_verification_status(db, user)

    app_stmt = (
        select(VerificationApplication)
        .where(VerificationApplication.applicant_user_id == user.id)
        .order_by(VerificationApplication.created_at.desc())
        .limit(1)
    )
    app_res = await db.execute(app_stmt)
    application = app_res.scalar_one_or_none()

    org_stmt = select(Organization).where(Organization.owner_user_id == user.id).limit(1)
    org_res = await db.execute(org_stmt)
    org = org_res.scalar_one_or_none()

    documents = []
    if org:
        docs_stmt = (
            select(OrganizationDocument)
            .where(OrganizationDocument.organization_id == org.id)
            .order_by(OrganizationDocument.created_at.desc())
        )
        docs_res = await db.execute(docs_stmt)
        for doc in docs_res.scalars().all():
            documents.append({
                "id": str(doc.id),
                "document_type": doc.document_type,
                "document_name": doc.document_name,
                "document_url": doc.document_url,
                "status": doc.status,
                "remarks": doc.remarks,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
            })

    unit = None
    if user.government_unit_id:
        unit = await db.get(GovernmentUnit, user.government_unit_id)

    return {
        "user_id": str(user.id),
        "username": user.username,
        "account_type": user.account_type,
        "verification_status": v_status,
        "application_id": str(application.id) if application else None,
        "application_type": application.application_type if application else user.account_type,
        "submitted_at": application.created_at.isoformat() if application and application.created_at else (user.created_at.isoformat() if user.created_at else None),
        "reviewed_at": application.reviewed_at.isoformat() if application and application.reviewed_at else None,
        "remarks": application.remarks if application else None,
        "rejection_reason": application.rejection_reason if application else None,
        "can_update_documents": v_status in ("PENDING", "MORE_INFORMATION_REQUIRED"),
        "documents": documents,
        "organization": {
            "id": str(org.id),
            "legal_name": org.legal_name,
            "display_name": org.display_name,
            "status": org.verification_status,
        } if org else None,
        "government_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "code": unit.code,
            "level": unit.level,
            "status": unit.status,
        } if unit else None,
    }


@router.put("/me", response_model=UserResponse)
async def update_my_user(
    payload: UserProfileUpdate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update email or phone for current user.
    """
    user, roles = current_user_and_roles

    if payload.email:
        # Check duplicate
        res = await db.execute(
            select(User).where(User.email == payload.email, User.id != user.id)
        )
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address is already in use by another account.",
            )
        user.email = payload.email.lower().strip()

    if payload.phone:
        res = await db.execute(
            select(User).where(User.phone == payload.phone, User.id != user.id)
        )
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number is already in use by another account.",
            )
        user.phone = payload.phone.strip()

    await db.commit()
    await db.refresh(user)

    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "is_suspended": user.is_suspended,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "government_unit_id": str(user.government_unit_id) if user.government_unit_id else None,
        "roles": roles,
    }


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upload and update profile photo for current user.
    """
    user, roles = current_user_and_roles
    content_type = file.content_type or ""
    if not (content_type.startswith("image/") or file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a valid image (PNG, JPG, WebP).")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    path_key = f"avatars/{user.id}_{int(time.time())}.{ext}"

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image size exceeds maximum 5MB limit.")

    storage = get_storage_service()
    await storage.store_file(path_key, content, mime_type=content_type or "image/jpeg")

    file_url = f"/api/v1/users/media/{path_key}"

    if user.account_type == "CANDIDATE":
        from app.models.candidate_profile import CandidateProfile
        res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        cp = res.scalar_one_or_none()
        if cp:
            cp.profile_photo_path = file_url
            from app.api.v1.endpoints.candidates import compute_completion_percentage
            from app.models.candidate_skill import CandidateSkill
            sk_res = await db.execute(select(func.count(CandidateSkill.id)).where(CandidateSkill.candidate_profile_id == cp.id))
            sk_count = sk_res.scalar() or 0
            cp.profile_completion_percentage = compute_completion_percentage(cp, sk_count)
    elif user.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
        from app.models.organization import Organization
        res = await db.execute(select(Organization).where(Organization.owner_user_id == user.id))
        org = res.scalars().first()
        if org:
            org.logo_path = file_url

    await db.commit()
    return {"success": True, "url": file_url, "avatar_url": file_url}


@router.post("/me/cover")
async def upload_my_cover(
    file: UploadFile = File(...),
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upload and update cover/banner image for current user.
    """
    user, roles = current_user_and_roles
    content_type = file.content_type or ""
    if not (content_type.startswith("image/") or file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a valid image (PNG, JPG, WebP).")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    path_key = f"covers/{user.id}_{int(time.time())}.{ext}"

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cover image size exceeds maximum 10MB limit.")

    storage = get_storage_service()
    await storage.store_file(path_key, content, mime_type=content_type or "image/jpeg")

    file_url = f"/api/v1/users/media/{path_key}"

    if user.account_type == "CANDIDATE":
        from app.models.candidate_profile import CandidateProfile
        res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        cp = res.scalar_one_or_none()
        if cp:
            cp.cover_photo_path = file_url
            from app.api.v1.endpoints.candidates import compute_completion_percentage
            from app.models.candidate_skill import CandidateSkill
            sk_res = await db.execute(select(func.count(CandidateSkill.id)).where(CandidateSkill.candidate_profile_id == cp.id))
            sk_count = sk_res.scalar() or 0
            cp.profile_completion_percentage = compute_completion_percentage(cp, sk_count)
    elif user.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
        from app.models.organization import Organization
        res = await db.execute(select(Organization).where(Organization.owner_user_id == user.id))
        org = res.scalars().first()
        if org:
            org.cover_photo_path = file_url

    await db.commit()
    return {"success": True, "url": file_url, "cover_url": file_url}


@router.get("/media/{file_path:path}")
async def get_media_file(file_path: str) -> Response:
    """
    Serve uploaded avatar, cover, or document media securely.
    """
    storage = get_storage_service()
    try:
        content = await storage.read_file(file_path)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.") from exc

    content_type, _ = mimetypes.guess_type(file_path)
    return Response(content=content, media_type=content_type or "application/octet-stream")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get public user information by user ID.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    roles_res = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, UserRole.revoked_at.is_(None))
    )
    roles = list(roles_res.scalars().all())

    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "is_suspended": user.is_suspended,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "government_unit_id": str(user.government_unit_id) if user.government_unit_id else None,
        "roles": roles,
    }


@router.get("/public/{identifier}")
async def get_public_profile(
    identifier: str,
    optional_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch a real public profile for any stakeholder from PostgreSQL.
    Identifier can be a username (@username or username), user UUID, or organization name.
    Unverified, pending, rejected, suspended, and administrative accounts are strictly excluded.
    """
    from app.models.candidate_credential import CandidateCredential, CredentialStatus
    from app.models.candidate_profile import CandidateProfile
    from app.models.candidate_skill import CandidateSkill, CandidateSkillStatus
    from app.models.course import Course
    from app.models.following import Following
    from app.models.government_unit import GovernmentUnit
    from app.models.institution_profile import InstitutionProfile
    from app.models.job import Job, JobStatus
    from app.models.organization import Organization
    from app.models.skill import Skill

    user: User | None = None
    clean_id = identifier.strip().lower().replace("@", "")

    # 1. Try username lookup (Top priority)
    stmt_user = select(User).where(func.lower(User.username) == clean_id).limit(1)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    # 2. Try UUID lookup
    if not user:
        try:
            parsed_uuid = UUID(identifier)
            user = await db.get(User, parsed_uuid)
        except (ValueError, AttributeError):
            pass

    # 3. Try organization lookup by legal_name or display_name
    org: Organization | None = None
    if not user:
        stmt_org = select(Organization).where(
            (func.lower(Organization.display_name) == clean_id)
            | (func.lower(Organization.legal_name) == clean_id)
            | (Organization.display_name.ilike(f"%{clean_id}%"))
            | (Organization.legal_name.ilike(f"%{clean_id}%"))
        ).limit(1)
        res_org = await db.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        if org and org.owner_user_id:
            user = await db.get(User, org.owner_user_id)

    # 4. Try GovernmentUnit lookup by code or name
    if not user:
        stmt_unit = select(GovernmentUnit).where(
            (func.lower(GovernmentUnit.code) == clean_id)
            | (GovernmentUnit.name.ilike(f"%{clean_id}%"))
        ).limit(1)
        res_unit = await db.execute(stmt_unit)
        found_unit = res_unit.scalar_one_or_none()
        if found_unit:
            stmt_guser = select(User).where(User.government_unit_id == found_unit.id).limit(1)
            res_guser = await db.execute(stmt_guser)
            user = res_guser.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{identifier}' not found in SkillVistaar.",
        )

    # Strict Security Rules:
    # 1. Administrative accounts must NEVER be returned in public profiles
    if user.account_type in ("SUPER_ADMIN", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{identifier}' not found.",
        )

    # 2. Inactive or suspended accounts return 404
    if not user.is_active or user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{identifier}' is not available.",
        )

    # 3. Verify stakeholder statutory status
    if user.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
        if not org:
            org_res = await db.execute(
                select(Organization).where(Organization.owner_user_id == user.id).limit(1)
            )
            org = org_res.scalar_one_or_none()
        if not org or org.verification_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization profile is pending statutory verification.",
            )

    elif user.account_type == "GOVERNMENT":
        unit = None
        if user.government_unit_id:
            unit = await db.get(GovernmentUnit, user.government_unit_id)
        if not unit or unit.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Government agency profile is not active.",
            )

    elif user.account_type == "CANDIDATE":
        if not (user.email_verified or user.phone_verified):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile is unverified.",
            )

    # Followers / Following count from live DB
    f_stmt = select(func.count(Following.id)).where(
        Following.target_id == user.id,
        Following.is_active == True,
    )
    followers_count = (await db.execute(f_stmt)).scalar() or 0

    fing_stmt = select(func.count(Following.id)).where(
        Following.user_id == user.id,
        Following.is_active == True,
    )
    following_count = (await db.execute(fing_stmt)).scalar() or 0

    # Following status for viewer
    is_following = False
    is_self = False
    if isinstance(optional_user, User):
        if optional_user.id == user.id:
            is_self = True
        else:
            f_check = await db.execute(
                select(Following.id).where(
                    Following.user_id == optional_user.id,
                    Following.target_id == user.id,
                    Following.is_active == True,
                ).limit(1)
            )
            is_following = f_check.scalar_one_or_none() is not None

    base_profile: dict[str, Any] = {
        "id": str(user.id),
        "username": user.username or clean_id,
        "handle": f"@{user.username}" if user.username else f"@{clean_id}",
        "account_type": user.account_type,
        "is_verified": True,
        "is_following": is_following,
        "is_self": is_self,
        "followers_count": followers_count,
        "following_count": following_count,
        "avatar": None,
        "cover_image": None,
        "profile_completion_percentage": 0,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

    if is_self:
        base_profile["email"] = user.email
        base_profile["phone"] = user.phone
        base_profile["private_details"] = {
            "official_email": user.email,
            "phone": user.phone,
        }

    if user.account_type == "CANDIDATE":
        cand_res = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        c_prof = cand_res.scalar_one_or_none()
        full_name = (
            f"{c_prof.first_name} {c_prof.last_name or ''}".strip()
            if c_prof
            else (user.email.split("@")[0] if user.email else "Candidate").capitalize()
        )

        # Verified & self-declared skills
        skills_res = await db.execute(
            select(CandidateSkill, Skill.name)
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_profile_id == (c_prof.id if c_prof else None))
        )
        skills_data = skills_res.all()
        verified_skills = [
            {"id": str(cs.id), "name": skill_name, "status": cs.status, "proficiency": cs.proficiency_level}
            for cs, skill_name in skills_data if cs.status == CandidateSkillStatus.VERIFIED.value
        ]
        self_skills = [
            {"id": str(cs.id), "name": skill_name, "status": cs.status, "proficiency": cs.proficiency_level}
            for cs, skill_name in skills_data if cs.status != CandidateSkillStatus.VERIFIED.value
        ]

        # Credentials
        creds_res = await db.execute(
            select(CandidateCredential).where(
                CandidateCredential.candidate_profile_id == (c_prof.id if c_prof else None),
                CandidateCredential.is_public == True,
            )
        )
        credentials = [
            {
                "id": str(c.id),
                "title": c.title,
                "issuer": c.issuing_organization_name,
                "type": c.credential_type,
                "status": c.status,
                "credential_number": c.credential_number,
            }
            for c in creds_res.scalars().all()
        ]

        base_profile.update({
            "name": full_name,
            "headline": c_prof.headline if c_prof and c_prof.headline else "Verified Professional",
            "bio": c_prof.bio if c_prof and c_prof.bio else "",
            "location": c_prof.preferred_location if c_prof else None,
            "avatar": c_prof.profile_photo_path if c_prof else None,
            "cover_image": c_prof.cover_photo_path if c_prof else None,
            "profile_completion_percentage": c_prof.profile_completion_percentage if c_prof else 0,
            "candidate_details": {
                "verified_skills": verified_skills,
                "self_declared_skills": self_skills,
                "credentials": credentials,
                "education": c_prof.education or [] if c_prof else [],
                "experience": c_prof.experience or [] if c_prof else [],
                "projects": c_prof.projects or [] if c_prof else [],
                "certifications": c_prof.certifications or [] if c_prof else [],
                "courses_completed": c_prof.courses_completed or [] if c_prof else [],
                "achievements": c_prof.achievements or [] if c_prof else [],
                "languages": c_prof.languages or [] if c_prof else [],
                "career_preferences": c_prof.career_preferences or {} if c_prof else {},
            },
        })

    elif user.account_type == "EMPLOYER":
        if not org:
            org_res = await db.execute(
                select(Organization).where(Organization.owner_user_id == user.id)
            )
            org = org_res.scalars().first()

        # Fetch open jobs
        jobs_res = await db.execute(
            select(Job).where(
                Job.organization_id == (org.id if org else None),
                Job.status == JobStatus.PUBLISHED.value,
                Job.is_active == True,
            )
        )
        open_jobs = [
            {
                "id": str(j.id),
                "title": j.title,
                "location": j.location,
                "work_mode": j.work_mode,
                "employment_type": j.employment_type,
                "min_salary": float(j.min_salary) if j.min_salary else None,
                "max_salary": float(j.max_salary) if j.max_salary else None,
            }
            for j in jobs_res.scalars().all()
        ]

        base_profile.update({
            "name": (org.display_name or org.legal_name) if org else "Employer Organization",
            "headline": "Industrial Employer",
            "bio": org.description if org else "",
            "location": org.address if org else None,
            "website": org.website if org else None,
            "avatar": org.logo_path if org else None,
            "cover_image": org.cover_photo_path if org else None,
            "email": org.email if org and org.email else user.email,
            "employer_details": {
                "legal_name": org.legal_name if org else "",
                "verification_status": org.verification_status if org else "PENDING",
                "open_jobs": open_jobs,
            },
        })

    elif user.account_type == "TRAINING_INSTITUTE":
        if not org:
            org_res = await db.execute(
                select(Organization).where(Organization.owner_user_id == user.id)
            )
            org = org_res.scalars().first()

        inst_prof = None
        if org:
            ip_res = await db.execute(
                select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
            )
            inst_prof = ip_res.scalar_one_or_none()

        courses_res = await db.execute(
            select(Course).where(
                Course.institution_profile_id == (inst_prof.id if inst_prof else None),
                Course.is_active == True,
            )
        )
        courses = [
            {
                "id": str(c.id),
                "title": c.title,
                "course_code": c.course_code,
                "duration_hours": c.duration_hours,
                "nsqf_level": c.nsqf_level,
                "fee_amount": float(c.fee_amount) if c.fee_amount else None,
            }
            for c in courses_res.scalars().all()
        ]

        base_profile.update({
            "name": (org.display_name or org.legal_name) if org else "Training Institute",
            "headline": "Accredited Training Institute",
            "bio": org.description if org else "",
            "location": f"{inst_prof.city}, {inst_prof.state}" if inst_prof and inst_prof.city else None,
            "avatar": org.logo_path if org else None,
            "cover_image": org.cover_photo_path if org else None,
            "email": org.email if org and org.email else user.email,
            "institute_details": {
                "institution_code": inst_prof.institution_code if inst_prof else None,
                "accreditation_body": inst_prof.accreditation_body if inst_prof else None,
                "courses_offered": courses,
            },
        })

    elif user.account_type == "GOVERNMENT":
        unit = None
        if user.government_unit_id:
            unit = await db.get(GovernmentUnit, user.government_unit_id)

        base_profile.update({
            "name": unit.name if unit else "Government Authority",
            "headline": f"{unit.unit_type.replace('_', ' ').title() if unit else 'Government Official'}",
            "bio": unit.description if unit else "Official administrative jurisdiction.",
            "location": unit.jurisdiction if unit else "India",
            "government_details": {
                "code": unit.code if unit else None,
                "level": unit.level if unit else None,
                "unit_type": unit.unit_type if unit else None,
                "jurisdiction": unit.jurisdiction if unit else None,
            },
        })

    else:
        base_profile.update({
            "name": "Super Administrator",
            "headline": "Platform System Administrator",
            "bio": "Central platform operations and governance authority.",
            "location": "Central Operations",
        })

    return {"success": True, "profile": base_profile, **base_profile}


class AccountDeleteRequest(BaseModel):
    password: str
    reason: str | None = None


@router.post("/me/delete-account")
async def delete_my_account(
    payload: AccountDeleteRequest,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Permanently deactivate and delete user account after server-side password verification.
    Invalidates all auth sessions, clears sensitive data, and records audit trail.
    """
    from datetime import datetime, timezone
    from sqlalchemy import update
    from app.core.security import verify_password
    from app.models.auth_session import AuthSession
    from app.models.audit_log import AuditAction, AuditLog

    user, _ = current_user_and_roles

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Account deletion aborted.",
        )

    # Invalidate all active authentication sessions
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id)
        .values(is_active=False, revoked_at=now)
    )

    # Anonymize and deactivate user
    orig_email = user.email
    orig_username = user.username
    user.is_active = False
    user.is_suspended = True
    user.email = f"deleted_{user.id}@skillvistaar.deleted"
    user.phone = None
    user.username = f"deleted_{str(user.id)[:8]}"

    # Audit log
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action=AuditAction.DELETE.value,
            resource_type="User",
            resource_id=user.id,
            description=f"User requested account deletion. Reason: {payload.reason or 'User requested deletion'}",
            metadata_json={
                "orig_email": orig_email,
                "orig_username": orig_username,
                "reason": payload.reason,
            },
        )
    )

    await db.commit()

    return {
        "success": True,
        "message": "Account successfully deleted. All sessions have been terminated.",
    }


@router.get("/{identifier}/followers")
async def get_user_followers(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch real followers list from PostgreSQL for a given user or organization.
    """
    from app.services.following_service import FollowingService
    from app.models.organization import Organization

    clean_id = identifier.strip().lower().replace("@", "")
    target_id: UUID | None = None

    try:
        target_id = UUID(identifier)
    except (ValueError, AttributeError):
        pass

    if not target_id:
        res = await db.execute(select(User.id).where(func.lower(User.username) == clean_id).limit(1))
        target_id = res.scalar_one_or_none()

    if not target_id:
        res_org = await db.execute(
            select(Organization.id).where(
                (func.lower(Organization.display_name) == clean_id)
                | (func.lower(Organization.legal_name) == clean_id)
            ).limit(1)
        )
        target_id = res_org.scalar_one_or_none()

    if not target_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

    service = FollowingService(db)
    items = await service.list_followers(target_id)
    return {"items": items, "total": len(items)}


@router.get("/{identifier}/following")
async def get_user_following(
    identifier: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch real following list from PostgreSQL for a given user.
    """
    from app.services.following_service import FollowingService

    clean_id = identifier.strip().lower().replace("@", "")
    user_id: UUID | None = None

    try:
        user_id = UUID(identifier)
    except (ValueError, AttributeError):
        pass

    if not user_id:
        res = await db.execute(select(User.id).where(func.lower(User.username) == clean_id).limit(1))
        user_id = res.scalar_one_or_none()

    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    service = FollowingService(db)
    items = await service.list_following_users(user_id)
    return {"items": items, "total": len(items)}

