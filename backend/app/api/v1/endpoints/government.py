from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.candidate_credential import CandidateCredential, CredentialStatus
from app.models.candidate_skill import CandidateSkill, CandidateSkillStatus
from app.models.course import Course
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile
from app.models.job import Job
from app.models.organization import Organization, OrganizationVerificationStatus
from app.models.organization_document import OrgDocumentStatus, OrganizationDocument
from app.models.placement_outcome import PlacementOutcome
from app.models.user import User
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.services.jurisdiction_service import (
    get_ancestor_unit_ids,
    get_authorized_unit_ids,
    get_descendant_unit_ids,
)

router = APIRouter(
    prefix="/government",
    tags=["Government"],
)


@router.get("/dashboard")
async def get_government_dashboard(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get government dashboard analytics filtered by the authenticated user's jurisdiction.
    """
    user, roles = current_user_and_roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_govt = user.account_type == "GOVERNMENT" or any("GOVERNMENT" in r for r in roles)

    if not is_admin and not is_govt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Government officials and Administrators.",
        )

    if not is_admin:
        from app.services.user_service import resolve_user_verification_status
        v_status = await resolve_user_verification_status(db, user)
        if v_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "VERIFICATION_REQUIRED",
                    "message": f"Government account verification status is {v_status}. Dashboard access requires APPROVED verification.",
                    "verification_status": v_status,
                },
            )

    authorized_units = await get_authorized_unit_ids(db, user, roles)

    # Unit info
    unit_info = None
    if user.government_unit_id:
        unit = await db.get(GovernmentUnit, user.government_unit_id)
        if unit:
            unit_info = {
                "id": str(unit.id),
                "name": unit.name,
                "code": unit.code,
                "level": unit.level,
                "unit_type": unit.unit_type,
                "status": unit.status,
                "jurisdiction": unit.jurisdiction,
            }

    # Count organizations in jurisdiction
    org_query = select(
        Organization.organization_type,
        Organization.verification_status,
        func.count(Organization.id),
    )
    if not is_admin and authorized_units:
        org_query = org_query.where(Organization.government_unit_id.in_(authorized_units))
    org_query = org_query.group_by(
        Organization.organization_type, Organization.verification_status
    )
    org_counts = (await db.execute(org_query)).all()

    employers_count = 0
    institutes_count = 0
    pending_orgs = 0
    approved_orgs = 0

    for org_type, ver_status, count in org_counts:
        if org_type == "EMPLOYER":
            employers_count += count
        elif org_type == "TRAINING_INSTITUTE":
            institutes_count += count

        if ver_status == OrganizationVerificationStatus.PENDING.value:
            pending_orgs += count
        elif ver_status == OrganizationVerificationStatus.APPROVED.value:
            approved_orgs += count

    # Verification applications in jurisdiction
    app_query = select(
        VerificationApplication.status,
        func.count(VerificationApplication.id),
    )
    if not is_admin and authorized_units:
        app_query = app_query.where(
            VerificationApplication.government_unit_id.in_(authorized_units)
        )
    app_query = app_query.group_by(VerificationApplication.status)
    app_counts = dict((await db.execute(app_query)).all())

    # Candidate skills & credentials counts
    total_verified_skills = (
        await db.scalar(
            select(func.count(CandidateSkill.id)).where(
                CandidateSkill.status == CandidateSkillStatus.VERIFIED.value
            )
        )
        or 0
    )

    total_verified_credentials = (
        await db.scalar(
            select(func.count(CandidateCredential.id)).where(
                CandidateCredential.status == CredentialStatus.VERIFIED.value
            )
        )
        or 0
    )

    return {
        "unit": unit_info,
        "is_super_admin": is_admin,
        "authorized_jurisdiction_count": len(authorized_units) if authorized_units else 0,
        "statistics": {
            "total_employers": employers_count,
            "total_institutes": institutes_count,
            "pending_verifications": app_counts.get(VerificationStatus.PENDING.value, 0) + pending_orgs,
            "approved_verifications": app_counts.get(VerificationStatus.APPROVED.value, 0) + approved_orgs,
            "rejected_verifications": app_counts.get(VerificationStatus.REJECTED.value, 0),
            "verified_skills": total_verified_skills,
            "verified_credentials": total_verified_credentials,
        },
        "recent_alerts": [
            {
                "id": "alert-1",
                "title": "Quarterly Verification Drive Active",
                "level": "INFO",
                "timestamp": "2026-09-20T00:00:00Z",
            },
            {
                "id": "alert-2",
                "title": "All pending Institute submissions require review within 7 days",
                "level": "WARNING",
                "timestamp": "2026-09-19T00:00:00Z",
            },
        ],
    }


@router.get("/jurisdiction")
async def get_my_jurisdiction(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get user's assigned government unit and hierarchy chain.
    """
    user, roles = current_user_and_roles
    if not user.government_unit_id:
        return {
            "has_unit": False,
            "message": "User is not directly linked to a specific government unit.",
        }

    unit = await db.get(GovernmentUnit, user.government_unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned government unit not found.",
        )

    ancestor_ids = await get_ancestor_unit_ids(db, unit.id)
    descendant_ids = await get_descendant_unit_ids(db, unit.id)

    return {
        "has_unit": True,
        "unit": {
            "id": str(unit.id),
            "name": unit.name,
            "code": unit.code,
            "level": unit.level,
            "unit_type": unit.unit_type,
            "status": unit.status,
            "jurisdiction": unit.jurisdiction,
            "parent_id": str(unit.parent_id) if unit.parent_id else None,
        },
        "total_descendant_jurisdictions": len(descendant_ids),
        "total_ancestor_jurisdictions": len(ancestor_ids),
    }


@router.get("/drill-down")
async def government_jurisdiction_drill_down(
    unit_id: UUID | None = None,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Multi-tier data drill-down:
    Country (Level 1) -> State (Level 2) -> District (Level 3) -> Local Area (Level 4) -> Organizations.
    Enforces strict jurisdiction boundaries based on caller's government role.
    """
    user, roles = current_user_and_roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_govt = user.account_type == "GOVERNMENT" or any("GOVERNMENT" in r for r in roles)

    if not is_admin and not is_govt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Government officials and Super Admins.",
        )

    authorized_unit_ids = await get_authorized_unit_ids(db, user, roles)

    # Determine target unit
    target_unit = None
    if unit_id:
        if not is_admin and unit_id not in authorized_unit_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Specified unit is outside your authorized jurisdiction.",
            )
        target_unit = await db.get(GovernmentUnit, unit_id)
    else:
        # Default to user's assigned unit or root unit
        if user.government_unit_id:
            target_unit = await db.get(GovernmentUnit, user.government_unit_id)
        elif is_admin:
            root_res = await db.execute(
                select(GovernmentUnit)
                .where(GovernmentUnit.parent_id.is_(None), GovernmentUnit.is_active.is_(True))
            )
            target_unit = root_res.scalars().first()

    if not target_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching government unit found.",
        )

    # Query direct sub-units
    sub_units_q = (
        select(GovernmentUnit)
        .where(GovernmentUnit.parent_id == target_unit.id, GovernmentUnit.is_active.is_(True))
        .order_by(GovernmentUnit.name)
    )
    if not is_admin:
        sub_units_q = sub_units_q.where(GovernmentUnit.id.in_(authorized_unit_ids))
    sub_units = list((await db.execute(sub_units_q)).scalars().all())

    # Units covered for aggregation: target unit and its descendants within caller's authority
    descendants = await get_descendant_unit_ids(db, target_unit.id)
    effective_units = descendants if is_admin else descendants.intersection(authorized_unit_ids)

    # Query organizations in this jurisdiction
    orgs_res = await db.execute(
        select(Organization)
        .where(Organization.government_unit_id.in_(effective_units), Organization.is_active.is_(True))
        .order_by(Organization.created_at.desc())
    )
    orgs = list(orgs_res.scalars().all())

    # Aggregates across effective units
    employers_cnt = sum(1 for o in orgs if o.organization_type == "EMPLOYER")
    institutes_cnt = sum(1 for o in orgs if o.organization_type == "TRAINING_INSTITUTE")

    org_ids = [o.id for o in orgs]
    active_jobs = 0
    total_courses = 0
    total_learners_placed = 0

    if org_ids:
        # Jobs in jurisdiction
        jobs_res = await db.execute(
            select(func.count(Job.id))
            .where(Job.organization_id.in_(org_ids), Job.status == "PUBLISHED")
        )
        active_jobs = jobs_res.scalar() or 0

        # Courses in jurisdiction
        inst_prof_q = select(InstitutionProfile.id).where(InstitutionProfile.organization_id.in_(org_ids))
        inst_prof_ids = (await db.execute(inst_prof_q)).scalars().all()
        if inst_prof_ids:
            crs_res = await db.execute(
                select(func.count(Course.id)).where(Course.institution_profile_id.in_(inst_prof_ids))
            )
            total_courses = crs_res.scalar() or 0

            plc_res = await db.execute(
                select(func.sum(PlacementOutcome.placed_learners)).where(
                    PlacementOutcome.institution_profile_id.in_(inst_prof_ids)
                )
            )
            total_learners_placed = plc_res.scalar() or 0

    return {
        "current_unit": {
            "id": str(target_unit.id),
            "name": target_unit.name,
            "code": target_unit.code,
            "level": target_unit.level,
            "unit_type": target_unit.unit_type,
            "jurisdiction": target_unit.jurisdiction,
            "parent_id": str(target_unit.parent_id) if target_unit.parent_id else None,
        },
        "sub_units": [
            {
                "id": str(u.id),
                "name": u.name,
                "code": u.code,
                "level": u.level,
                "unit_type": u.unit_type,
                "jurisdiction": u.jurisdiction,
            }
            for u in sub_units
        ],
        "organizations": [
            {
                "id": str(o.id),
                "legal_name": o.legal_name,
                "display_name": o.display_name or o.legal_name,
                "organization_type": o.organization_type,
                "verification_status": o.verification_status,
                "registration_number": o.registration_number,
                "government_unit_id": str(o.government_unit_id) if o.government_unit_id else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orgs[:50]
        ],
        "aggregates": {
            "total_employers": employers_cnt,
            "total_institutes": institutes_cnt,
            "active_jobs": active_jobs,
            "total_courses": total_courses,
            "total_learners_placed": int(total_learners_placed),
        },
    }


@router.get("/documents/pending")
async def list_pending_documents_for_verifier(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List all pending and under-review organization documents within caller's government jurisdiction.
    """
    user, roles = current_user_and_roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_govt = user.account_type == "GOVERNMENT" or any("GOVERNMENT" in r for r in roles)

    if not is_admin and not is_govt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized verifiers.",
        )

    authorized_units = await get_authorized_unit_ids(db, user, roles)

    stmt = (
        select(
            OrganizationDocument,
            Organization.legal_name,
            Organization.organization_type,
            Organization.government_unit_id,
            GovernmentUnit.name.label("jurisdiction_name"),
        )
        .join(Organization, Organization.id == OrganizationDocument.organization_id)
        .outerjoin(GovernmentUnit, GovernmentUnit.id == Organization.government_unit_id)
        .where(
            OrganizationDocument.status.in_([
                OrgDocumentStatus.PENDING.value,
                OrgDocumentStatus.UNDER_REVIEW.value,
                OrgDocumentStatus.REQUEST_INFORMATION.value,
            ])
        )
        .order_by(OrganizationDocument.created_at.desc())
    )

    if not is_admin:
        stmt = stmt.where(Organization.government_unit_id.in_(authorized_units))

    rows = (await db.execute(stmt)).all()
    results = []
    for doc, org_name, org_type, unit_id, j_name in rows:
        results.append({
            "id": str(doc.id),
            "organization_id": str(doc.organization_id),
            "organization_name": org_name,
            "organization_type": org_type,
            "jurisdiction_name": j_name or "Unassigned",
            "government_unit_id": str(unit_id) if unit_id else None,
            "document_type": doc.document_type,
            "title": doc.title,
            "document_number": doc.document_number,
            "issuing_authority": doc.issuing_authority,
            "issue_date": doc.issue_date.isoformat() if doc.issue_date else None,
            "expiry_date": doc.expiry_date.isoformat() if doc.expiry_date else None,
            "file_name": doc.file_name,
            "file_url": doc.file_url,
            "status": doc.status,
            "verification_remarks": doc.verification_remarks,
            "rejection_reason": doc.rejection_reason,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })
    return results

