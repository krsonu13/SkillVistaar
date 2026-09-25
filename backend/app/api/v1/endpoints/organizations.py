from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile, InstitutionVerificationStatus
from app.models.job import Job
from app.models.job_application import JobApplication
from app.models.organization import (
    Organization,
    OrganizationType,
    OrganizationVerificationStatus,
)
from app.models.user import User
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationReview,
)
from app.services.audit_log_service import AuditLogService
from app.services.jurisdiction_service import (
    enforce_jurisdiction_access,
    enforce_verification_authority,
    get_authorized_unit_ids,
)

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Register a new Organization (Employer or Training Institute).
    Initial status is always PENDING_VERIFICATION.
    """
    user, roles = current_user_and_roles

    # Verify government unit exists if specified
    if data.government_unit_id:
        govt_unit = await db.get(GovernmentUnit, data.government_unit_id)
        if not govt_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specified government unit '{data.government_unit_id}' does not exist.",
            )

    org = Organization(
        owner_user_id=user.id,
        government_unit_id=data.government_unit_id,
        organization_type=data.organization_type,
        legal_name=data.legal_name,
        display_name=data.display_name or data.legal_name,
        registration_number=data.registration_number,
        email=data.email,
        phone=data.phone,
        website=data.website,
        address=data.address,
        description=data.description,
        verification_status=OrganizationVerificationStatus.PENDING.value,
        is_active=True,
    )
    db.add(org)
    await db.flush()

    # If Training Institute, create InstitutionProfile
    if data.organization_type == OrganizationType.TRAINING_INSTITUTE.value:
        inst_profile = InstitutionProfile(
            organization_id=org.id,
            institution_code=data.institution_code,
            accreditation_body=data.accreditation_body,
            accreditation_number=data.accreditation_number,
            city=data.city,
            state=data.state,
            verification_status=InstitutionVerificationStatus.PENDING.value,
            is_active=True,
        )
        db.add(inst_profile)

    # Automatically create a VerificationApplication routed to jurisdiction
    ver_app = VerificationApplication(
        applicant_user_id=user.id,
        government_unit_id=data.government_unit_id,
        application_type=f"{data.organization_type}_REGISTRATION",
        status=VerificationStatus.PENDING.value,
        submitted_data=str({
            "organization_id": str(org.id),
            "legal_name": org.legal_name,
            "registration_number": org.registration_number,
            "organization_type": org.organization_type,
        }),
    )
    db.add(ver_app)

    # Log audit
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.CREATE,
        resource_type="organization",
        resource_id=org.id,
        description=f"Organization {org.legal_name} registered; status set to PENDING_VERIFICATION.",
        metadata_json={
            "organization_type": org.organization_type,
            "government_unit_id": str(data.government_unit_id) if data.government_unit_id else None,
        },
    )

    await db.commit()
    await db.refresh(org)
    return org


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    organization_type: str | None = Query(None, description="EMPLOYER or TRAINING_INSTITUTE"),
    verification_status: str | None = Query(None, description="PENDING, APPROVED, REJECTED, etc."),
    government_unit_id: UUID | None = Query(None, description="Filter by government unit"),
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[Organization]:
    """
    List organizations. If caller is a government verifier, restricts to authorized jurisdiction.
    """
    user, roles = current_user_and_roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_govt = user.account_type == "GOVERNMENT" or any("GOVERNMENT" in r for r in roles)

    query = select(Organization).where(Organization.is_active.is_(True))

    if is_govt and not is_admin:
        authorized_units = await get_authorized_unit_ids(db, user, roles)
        query = query.where(Organization.government_unit_id.in_(authorized_units))

    if organization_type:
        query = query.where(Organization.organization_type == organization_type)
    if verification_status:
        query = query.where(Organization.verification_status == verification_status)
    if government_unit_id:
        query = query.where(Organization.government_unit_id == government_unit_id)

    query = query.order_by(Organization.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/pending", response_model=list[OrganizationResponse])
async def list_pending_organizations(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[Organization]:
    """
    List organizations awaiting government verification in caller's jurisdiction.
    """
    return await list_organizations(
        organization_type=None,
        verification_status=OrganizationVerificationStatus.PENDING.value,
        government_unit_id=None,
        current_user_and_roles=current_user_and_roles,
        db=db,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Get organization by ID.
    """
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found.",
        )
    return org


@router.post("/{org_id}/review", response_model=OrganizationResponse)
async def review_organization(
    org_id: UUID,
    review: OrganizationReview,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Review organization verification application.
    Enforces strict jurisdiction checking: Verifier cannot review cross-district orgs.
    """
    user, roles = current_user_and_roles

    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found.",
        )

    # Enforce strict multi-tier jurisdiction verification authority
    await enforce_verification_authority(
        db=db,
        verifier_user=user,
        verifier_roles=roles,
        target_entity_type=org.organization_type,
        target_unit_id=org.government_unit_id,
        action_label=f"review verification for organization '{org.legal_name}'",
    )

    now = datetime.now(timezone.utc)
    old_status = org.verification_status
    org.verification_status = review.status

    if review.status == OrganizationVerificationStatus.APPROVED.value:
        org.verified_at = now
    elif review.status == OrganizationVerificationStatus.SUSPENDED.value:
        org.suspended_at = now
    elif review.status == OrganizationVerificationStatus.REVOKED.value:
        org.revoked_at = now

    # Also update institution profile if applicable
    inst_result = await db.execute(
        select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
    )
    inst_profile = inst_result.scalar_one_or_none()
    if inst_profile:
        inst_profile.verification_status = review.status
        if review.status == OrganizationVerificationStatus.APPROVED.value:
            inst_profile.verified_at = now
        elif review.status == OrganizationVerificationStatus.SUSPENDED.value:
            inst_profile.suspended_at = now
        elif review.status == OrganizationVerificationStatus.REVOKED.value:
            inst_profile.revoked_at = now

    # Update associated VerificationApplication if found
    ver_app_result = await db.execute(
        select(VerificationApplication)
        .where(
            VerificationApplication.applicant_user_id == org.owner_user_id,
            VerificationApplication.status == VerificationStatus.PENDING.value,
        )
        .order_by(VerificationApplication.created_at.desc())
    )
    ver_app = ver_app_result.scalar_one_or_none()
    if ver_app:
        ver_app.status = review.status
        ver_app.verifier_user_id = user.id
        ver_app.reviewed_at = now
        ver_app.remarks = review.remarks
        ver_app.rejection_reason = review.rejection_reason

    # Audit log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.APPROVE if review.status == "APPROVED" else AuditAction.REJECT,
        resource_type="organization",
        resource_id=org.id,
        description=f"Organization {org.legal_name} status updated from {old_status} to {review.status}.",
        metadata_json={
            "verifier_user_id": str(user.id),
            "old_status": old_status,
            "new_status": review.status,
            "remarks": review.remarks,
            "rejection_reason": review.rejection_reason,
            "government_unit_id": str(org.government_unit_id) if org.government_unit_id else None,
        },
    )

    await db.commit()
    await db.refresh(org)
    return org


async def require_employer(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, list[str]]:
    user, roles = current_user_and_roles
    is_employer = user.account_type == "EMPLOYER" or any(r in ("ORG_ADMIN", "HR", "JOB_POSTER") for r in roles)
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    if not is_employer and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Employers.",
        )
    if not is_admin:
        from app.services.user_service import resolve_user_verification_status
        v_status = await resolve_user_verification_status(db, user)
        if v_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "VERIFICATION_REQUIRED",
                    "message": f"Employer verification status is {v_status}. Dashboard access requires APPROVED verification.",
                    "verification_status": v_status,
                },
            )
    return current_user_and_roles


@router.get("/me/dashboard")
async def get_employer_dashboard(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_employer),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get real, database-backed dashboard metrics and organizational state for the authenticated employer.
    """
    user, roles = current_user_and_roles
    res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = res.scalars().first()

    jurisdiction_info = None
    if org and org.government_unit_id:
        g_unit = await db.get(GovernmentUnit, org.government_unit_id)
        if g_unit:
            jurisdiction_info = {
                "id": str(g_unit.id),
                "name": g_unit.name,
                "code": g_unit.code,
                "level": g_unit.level,
                "unit_type": g_unit.unit_type,
                "jurisdiction": g_unit.jurisdiction,
            }

    active_postings = 0
    total_applicants = 0
    interviews_scheduled = 0
    verified_hires = 0

    if org:
        jobs_res = await db.execute(
            select(Job.id, Job.status).where(Job.organization_id == org.id)
        )
        job_rows = jobs_res.all()
        active_postings = sum(1 for _, st in job_rows if st == "PUBLISHED")
        job_ids = [j_id for j_id, _ in job_rows]

        if job_ids:
            apps_res = await db.execute(
                select(JobApplication.status).where(JobApplication.job_id.in_(job_ids))
            )
            app_statuses = list(apps_res.scalars().all())
            total_applicants = len(app_statuses)
            interviews_scheduled = sum(1 for st in app_statuses if st in ("INTERVIEW", "ASSESSMENT"))
            verified_hires = sum(1 for st in app_statuses if st == "SELECTED")

    return {
        "success": True,
        "organization": {
            "id": str(org.id) if org else None,
            "name": org.legal_name if org else user.email.split("@")[0].capitalize(),
            "legal_name": org.legal_name if org else user.email.split("@")[0].capitalize(),
            "display_name": (org.display_name or org.legal_name) if org else "Employer Organization",
            "verification_status": org.verification_status if org else "PENDING",
            "registration_number": org.registration_number if org else None,
            "sector": org.sector if org else None,
            "company_size": org.company_size if org else None,
            "address": org.address if org else None,
            "website": org.website if org else None,
            "jurisdiction": jurisdiction_info,
        },
        "stats": {
            "active_postings": active_postings,
            "total_applicants": total_applicants,
            "interviews_scheduled": interviews_scheduled,
            "verified_hires": verified_hires,
        },
    }


@router.get("/me/profile")
async def get_my_employer_profile(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_employer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get full employer organization profile including sector, size, locations, contact persons, and jurisdiction hierarchy.
    """
    user, roles = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Employer organization not registered.")

    jurisdiction_hierarchy = []
    if org.government_unit_id:
        current_u = await db.get(GovernmentUnit, org.government_unit_id)
        while current_u:
            jurisdiction_hierarchy.insert(0, {
                "id": str(current_u.id),
                "name": current_u.name,
                "code": current_u.code,
                "level": current_u.level,
                "unit_type": current_u.unit_type,
                "jurisdiction": current_u.jurisdiction,
            })
            if current_u.parent_id:
                current_u = await db.get(GovernmentUnit, current_u.parent_id)
            else:
                break

    return {
        "organization_id": str(org.id),
        "legal_name": org.legal_name,
        "display_name": org.display_name or org.legal_name,
        "registration_number": org.registration_number,
        "organization_type": org.organization_type,
        "email": org.email,
        "phone": org.phone,
        "website": org.website,
        "address": org.address,
        "description": org.description,
        "sector": org.sector,
        "company_size": org.company_size,
        "branches": org.branches or [],
        "contact_persons": org.contact_persons or [],
        "industry_skills": org.industry_skills or [],
        "verification_status": org.verification_status,
        "government_unit_id": str(org.government_unit_id) if org.government_unit_id else None,
        "jurisdiction_hierarchy": jurisdiction_hierarchy,
    }


@router.patch("/me/profile")
async def update_my_employer_profile(
    payload: dict,
    current_user_and_roles: tuple[User, list[str]] = Depends(require_employer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update employer operational details: sector, company size, branches, contact persons, industry skills.
    Audited for regulatory compliance.
    """
    user, roles = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Employer organization not found.")

    for f in (
        "display_name",
        "phone",
        "website",
        "address",
        "description",
        "sector",
        "company_size",
        "branches",
        "contact_persons",
        "industry_skills",
    ):
        if f in payload and payload[f] is not None:
            setattr(org, f, payload[f])

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.UPDATE,
        resource_type="organization",
        resource_id=org.id,
        description=f"Employer organization profile updated by {user.email}.",
        metadata_json={
            "updated_fields": list(payload.keys()),
        },
    )

    await db.commit()
    return {"success": True, "message": "Employer profile updated successfully."}


