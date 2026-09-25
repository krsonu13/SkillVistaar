from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    get_current_user,
    get_current_user_with_roles,
    get_optional_current_user,
)
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.course import Course
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile
from app.models.organization import Organization
from app.models.placement_outcome import PlacementOutcome
from app.models.user import User
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdate,
)
from app.services.audit_log_service import AuditLogService
from app.services.institution_service import (
    InstitutionAccessDeniedError,
    InstitutionNotFoundError,
    InstitutionService,
    InstitutionValidationError,
)


router = APIRouter(
    prefix="/institutions",
    tags=["Institutions"],
)


def _handle_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InstitutionNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, InstitutionAccessDeniedError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, InstitutionValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected institution service error occurred.",
    )


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_institution(
    data: InstitutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await InstitutionService.create_institution(
            db=db,
            current_user=current_user,
            data=data,
        )
    except (
        InstitutionNotFoundError,
        InstitutionAccessDeniedError,
        InstitutionValidationError,
    ) as exc:
        raise _handle_service_error(exc) from exc


@router.get(
    "",
    response_model=InstitutionListResponse,
)
async def list_institutions(
    keyword: str | None = Query(
        default=None,
        max_length=255,
    ),
    institution_type: str | None = Query(
        default=None,
        max_length=100,
    ),
    city: str | None = Query(
        default=None,
        max_length=100,
    ),
    state: str | None = Query(
        default=None,
        max_length=100,
    ),
    verification_status: str | None = Query(
        default=None,
        max_length=50,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: AsyncSession = Depends(get_db),
):
    try:
        items, total = await InstitutionService.list_institutions(
            db=db,
            keyword=keyword,
            institution_type=institution_type,
            city=city,
            state=state,
            verification_status=verification_status,
            page=page,
            page_size=page_size,
        )

        pages = InstitutionService.calculate_pages(
            total,
            page_size,
        )

        return InstitutionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except InstitutionValidationError as exc:
        raise _handle_service_error(exc) from exc


@router.get(
    "/{institution_profile_id}",
    response_model=InstitutionResponse,
)
async def get_institution(
    institution_profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return await InstitutionService.get_for_user(
            db=db,
            current_user=current_user,
            institution_profile_id=institution_profile_id,
        )
    except InstitutionNotFoundError as exc:
        raise _handle_service_error(exc) from exc
    except InstitutionAccessDeniedError as exc:
        raise _handle_service_error(exc) from exc
    except InstitutionValidationError as exc:
        raise _handle_service_error(exc) from exc


@router.patch(
    "/{institution_profile_id}",
    response_model=InstitutionResponse,
)
async def update_institution(
    institution_profile_id: uuid.UUID,
    data: InstitutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await InstitutionService.update_institution(
            db=db,
            current_user=current_user,
            institution_profile_id=institution_profile_id,
            data=data,
        )
    except (
        InstitutionNotFoundError,
        InstitutionAccessDeniedError,
        InstitutionValidationError,
    ) as exc:
        raise _handle_service_error(exc) from exc


async def require_institution(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, list[str]]:
    user, roles = current_user_and_roles
    is_inst = user.account_type == "TRAINING_INSTITUTE" or "INSTITUTION_ADMIN" in roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    if not is_inst and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Training Institutes.",
        )
    if not is_admin:
        from app.services.user_service import resolve_user_verification_status
        v_status = await resolve_user_verification_status(db, user)
        if v_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "VERIFICATION_REQUIRED",
                    "message": f"Training Institute verification status is {v_status}. Dashboard access requires APPROVED verification.",
                    "verification_status": v_status,
                },
            )
    return current_user_and_roles


@router.get("/me/dashboard")
async def get_institution_dashboard(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_institution),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get real, database-backed dashboard metrics and organizational state for the authenticated institute.
    """
    user, roles = current_user_and_roles

    # Retrieve user's organization
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()

    inst_profile = None
    jurisdiction_info = None

    if org:
        inst_res = await db.execute(
            select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
        )
        inst_profile = inst_res.scalars().first()

        if org.government_unit_id:
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

    # Query real courses
    courses = []
    if inst_profile:
        courses_res = await db.execute(
            select(Course).where(Course.institution_profile_id == inst_profile.id)
        )
        courses = list(courses_res.scalars().all())

    affiliated_courses = len(courses)
    active_batches = sum(1 for c in courses if c.status == "PUBLISHED")
    enrolled_students = sum((c.seats or 0) for c in courses)

    # Query real placement outcomes
    placement_rate = 0.0
    total_placed = 0
    if inst_profile:
        placements_res = await db.execute(
            select(PlacementOutcome).where(
                PlacementOutcome.institution_profile_id == inst_profile.id
            )
        )
        placements = list(placements_res.scalars().all())
        if placements:
            total_placed = sum(p.placed_learners for p in placements)
            rates = [p.employment_rate for p in placements if p.employment_rate is not None]
            if rates:
                placement_rate = round(sum(rates) / len(rates), 1)

    return {
        "success": True,
        "organization": {
            "id": str(org.id) if org else None,
            "profile_id": str(inst_profile.id) if inst_profile else None,
            "legal_name": org.legal_name if org else user.email.split("@")[0].capitalize(),
            "display_name": (org.display_name or org.legal_name) if org else "Training Institute",
            "verification_status": org.verification_status if org else "PENDING",
            "institution_code": inst_profile.institution_code if inst_profile else None,
            "accreditation_body": inst_profile.accreditation_body if inst_profile else None,
            "accreditation_number": inst_profile.accreditation_number if inst_profile else None,
            "affiliation": inst_profile.affiliation if inst_profile else None,
            "ownership_type": inst_profile.ownership_type if inst_profile else None,
            "established_year": inst_profile.established_year if inst_profile else None,
            "jurisdiction": jurisdiction_info,
            "address": org.address if org else None,
            "city": inst_profile.city if inst_profile else None,
            "state": inst_profile.state if inst_profile else None,
        },
        "stats": {
            "enrolled_students": enrolled_students,
            "active_batches": active_batches,
            "placement_rate_percent": placement_rate,
            "affiliated_courses": affiliated_courses,
            "total_placed_graduates": total_placed,
        },
    }


@router.get("/me/profile")
async def get_my_institution_profile(
    current_user_and_roles: tuple[User, list[str]] = Depends(require_institution),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get full institutional profile including faculty, infrastructure, partnerships, and jurisdiction hierarchy.
    """
    user, roles = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Institution organization not registered.")

    inst_res = await db.execute(
        select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
    )
    inst_profile = inst_res.scalars().first()

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
        "profile_id": str(inst_profile.id) if inst_profile else None,
        "legal_name": org.legal_name,
        "display_name": org.display_name or org.legal_name,
        "registration_number": org.registration_number,
        "email": org.email,
        "phone": org.phone,
        "website": org.website,
        "address": org.address,
        "description": org.description,
        "verification_status": org.verification_status,
        "institution_code": inst_profile.institution_code if inst_profile else None,
        "accreditation_body": inst_profile.accreditation_body if inst_profile else None,
        "accreditation_number": inst_profile.accreditation_number if inst_profile else None,
        "institution_type": inst_profile.institution_type if inst_profile else None,
        "affiliation": inst_profile.affiliation if inst_profile else None,
        "ownership_type": inst_profile.ownership_type if inst_profile else None,
        "established_year": inst_profile.established_year if inst_profile else None,
        "city": inst_profile.city if inst_profile else None,
        "state": inst_profile.state if inst_profile else None,
        "country": inst_profile.country if inst_profile else "India",
        "trainers": inst_profile.trainers if inst_profile and inst_profile.trainers else [],
        "infrastructure": inst_profile.infrastructure if inst_profile and inst_profile.infrastructure else [],
        "partnerships": inst_profile.partnerships if inst_profile and inst_profile.partnerships else [],
        "curriculum_alignment": inst_profile.curriculum_alignment if inst_profile and inst_profile.curriculum_alignment else {},
        "government_unit_id": str(org.government_unit_id) if org.government_unit_id else None,
        "jurisdiction_hierarchy": jurisdiction_hierarchy,
    }


@router.patch("/me/profile")
async def update_my_institution_profile(
    payload: dict,
    current_user_and_roles: tuple[User, list[str]] = Depends(require_institution),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update institutional operational details: faculty, infrastructure, partnerships, curriculum alignment.
    Audits changes to ensure institutional integrity.
    """
    user, roles = current_user_and_roles
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_res.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Institution organization not found.")

    inst_res = await db.execute(
        select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
    )
    inst_profile = inst_res.scalars().first()
    if not inst_profile:
        inst_profile = InstitutionProfile(organization_id=org.id)
        db.add(inst_profile)

    # Updatable org fields
    for f in ("display_name", "phone", "website", "address", "description"):
        if f in payload and payload[f] is not None:
            setattr(org, f, payload[f])

    # Updatable profile fields
    for f in (
        "institution_code",
        "accreditation_body",
        "accreditation_number",
        "institution_type",
        "affiliation",
        "ownership_type",
        "established_year",
        "city",
        "state",
        "trainers",
        "infrastructure",
        "partnerships",
        "curriculum_alignment",
    ):
        if f in payload and payload[f] is not None:
            setattr(inst_profile, f, payload[f])

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.UPDATE,
        resource_type="institution_profile",
        resource_id=inst_profile.id,
        description=f"Institution profile updated by {user.email}.",
        metadata_json={
            "updated_fields": list(payload.keys()),
        },
    )

    await db.commit()
    return {"success": True, "message": "Institutional profile updated successfully."}


