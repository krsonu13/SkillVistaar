from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditLog
from app.models.candidate_profile import CandidateProfile
from app.models.government_unit import GovernmentUnit
from app.models.notification import Notification, NotificationPriority
from app.models.organization import Organization, OrganizationType, OrganizationVerificationStatus
from app.models.platform_config import PlatformConfig
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.user_warning import UserWarning
from app.models.verification_application import VerificationApplication, VerificationStatus
from app.schemas.auth import UserResponse
from app.services.audit_log_service import AuditLogService
from app.services.otp_delivery_service import validate_sms_configuration, validate_smtp_configuration

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
)


def require_super_admin(
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
) -> tuple[User, list[str]]:
    user, roles = current_user_and_roles
    if user.account_type != "SUPER_ADMIN" and "SUPER_ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Super Administrators.",
        )
    return current_user_and_roles


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class UserStatusUpdate(BaseModel):
    is_active: bool | None = None
    is_suspended: bool | None = None
    reason: str | None = Field(default=None, max_length=500, description="Administrative reason")


class UserWarningCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5, max_length=2000)
    reason: str = Field(..., min_length=3, max_length=500)
    severity: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH|CRITICAL)$")


class PlatformConfigPayload(BaseModel):
    config_data: dict[str, Any]
    change_reason: str = Field(..., min_length=3, max_length=500)


class VerificationActionRequest(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT|REQUEST_INFO|SUSPEND|REVOKE)$")
    reason: str | None = Field(default=None, max_length=1000)
    remarks: str | None = Field(default=None, max_length=1000)


class AssignGovtUnitRequest(BaseModel):
    government_unit_id: UUID | None


class AssignRoleRequest(BaseModel):
    role_code: str


# ---------------------------------------------------------------------------
# Default Configurations (Seed fallback when no DB record exists)
# ---------------------------------------------------------------------------

DEFAULT_PLATFORM_CONFIGS: dict[str, dict[str, Any]] = {
    "landing_content": {
        "hero_badge": "Government-Anchored Ecosystem",
        "hero_title": "India's Unified Digital Skilling & Workforce Exchange",
        "hero_subtitle": "Empowering candidates, employers, training institutes, and government nodal agencies with cryptographically verifiable skills, AI-indexed hiring, and macroeconomic labor intelligence.",
        "announcement_active": True,
        "announcement_text": "SkillVistaar 2.0 Apex Release: Digital Public Infrastructure integration live across all 38 districts.",
        "announcement_severity": "info",
        "primary_cta_text": "Join the Ecosystem",
        "primary_cta_link": "/signup",
        "secondary_cta_text": "Explore Public Directory",
        "secondary_cta_link": "/public/jobs",
        "stats_candidates_label": "Verified Candidates",
        "stats_employers_label": "Hiring Enterprises",
        "stats_institutes_label": "Accredited Colleges",
        "stats_credentials_label": "Digital Certificates",
    },
    "auth_signup_config": {
        "candidate_fields": {
            "fullName_required": True,
            "dob_required": False,
            "education_required": False,
            "domain_required": True,
        },
        "employer_fields": {
            "companyName_required": True,
            "cin_required": False,
            "industry_required": True,
            "location_required": True,
        },
        "institute_fields": {
            "instituteName_required": True,
            "aisheCode_required": False,
            "instituteType_required": True,
        },
        "government_fields": {
            "departmentName_required": True,
            "designation_required": True,
            "officialEmailOnly": True,
        },
        "general": {
            "secondaryVerificationRequired": True,
            "termsAcceptanceMandatory": True,
            "minPasswordLength": 8,
            "resendCooldownSeconds": 60,
        },
    },
    "auth_login_config": {
        "enabled_stakeholders": ["candidate", "employer", "institute", "government", "admin"],
        "disclaimer_text": "Protected Government-Affiliated Information System. Unauthorized access attempts are monitored, recorded, and prosecuted under applicable IT Acts.",
        "support_email": "support@skillvistaar.gov.in",
        "max_login_attempts": 5,
        "lockout_duration_minutes": 15,
    },
    "system_announcements": {
        "banner_enabled": True,
        "banner_title": "Scheduled Infrastructure Upgrade",
        "banner_message": "Unified National Registry synchronization is active. All services operating at full capacity.",
        "severity": "NORMAL",
        "target_audience": "ALL",
    },
}


# ---------------------------------------------------------------------------
# 1. Platform Statistics & Overview
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_system_stats(
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get comprehensive platform-wide counts, verification queue breakdown,
    user statuses, and live infrastructure telemetry.
    """
    now = datetime.now(timezone.utc)

    # Users
    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True), User.is_suspended.is_(False))) or 0
    suspended_users = await db.scalar(select(func.count(User.id)).where(User.is_suspended.is_(True))) or 0
    locked_users = await db.scalar(select(func.count(User.id)).where(User.locked_until.is_not(None), User.locked_until > now)) or 0
    unverified_users = await db.scalar(select(func.count(User.id)).where(User.email_verified.is_(False), User.phone_verified.is_(False))) or 0

    users_by_type_res = await db.execute(
        select(User.account_type, func.count(User.id)).group_by(User.account_type)
    )
    users_by_account_type = dict(users_by_type_res.all())

    # Organizations
    total_organizations = await db.scalar(select(func.count(Organization.id))) or 0
    total_employers = await db.scalar(select(func.count(Organization.id)).where(Organization.organization_type == OrganizationType.EMPLOYER.value)) or 0
    total_institutes = await db.scalar(select(func.count(Organization.id)).where(Organization.organization_type == OrganizationType.TRAINING_INSTITUTE.value)) or 0
    verified_organizations = await db.scalar(select(func.count(Organization.id)).where(Organization.verification_status == OrganizationVerificationStatus.APPROVED.value)) or 0
    pending_organizations = await db.scalar(select(func.count(Organization.id)).where(Organization.verification_status == OrganizationVerificationStatus.PENDING.value)) or 0

    # Verification Queue breakdown by 6 tiers
    total_pending_verifications = await db.scalar(
        select(func.count(VerificationApplication.id)).where(
            VerificationApplication.status == VerificationStatus.PENDING.value
        )
    ) or 0

    # Tier counts for pending
    tier_counts = {
        "central": 0,
        "state": 0,
        "district": 0,
        "local": 0,
        "employer": 0,
        "institute": 0,
    }

    pending_apps = (
        await db.execute(
            select(
                VerificationApplication.application_type,
                GovernmentUnit.level,
                GovernmentUnit.unit_type,
            )
            .outerjoin(GovernmentUnit, GovernmentUnit.id == VerificationApplication.government_unit_id)
            .where(VerificationApplication.status == VerificationStatus.PENDING.value)
        )
    ).all()

    for app_type, unit_level, unit_type in pending_apps:
        app_type_u = (app_type or "").upper()
        unit_type_u = (unit_type or "").upper()
        if "EMPLOYER" in app_type_u:
            tier_counts["employer"] += 1
        elif "INSTITUTE" in app_type_u or "COLLEGE" in app_type_u:
            tier_counts["institute"] += 1
        elif unit_level == 1 or "CENTRAL" in unit_type_u:
            tier_counts["central"] += 1
        elif unit_level == 2 or "STATE" in unit_type_u:
            tier_counts["state"] += 1
        elif unit_level == 3 or "DISTRICT" in unit_type_u:
            tier_counts["district"] += 1
        elif unit_level == 4 or "LOCAL" in unit_type_u or "BLOCK" in unit_type_u or "MUNICIPAL" in unit_type_u:
            tier_counts["local"] += 1
        else:
            tier_counts["district"] += 1

    # Warnings & Audit Logs
    total_warnings = await db.scalar(select(func.count(UserWarning.id))) or 0
    total_audit_logs = await db.scalar(select(func.count(AuditLog.id))) or 0
    total_govt_units = await db.scalar(select(func.count(GovernmentUnit.id))) or 0

    # System Health
    smtp_status = validate_smtp_configuration()
    sms_status = validate_sms_configuration()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "suspended": suspended_users,
            "locked": locked_users,
            "unverified": unverified_users,
            "by_type": users_by_account_type,
        },
        "organizations": {
            "total": total_organizations,
            "employers": total_employers,
            "institutes": total_institutes,
            "verified": verified_organizations,
            "pending": pending_organizations,
        },
        "verifications": {
            "total_pending": total_pending_verifications,
            "by_tier": tier_counts,
        },
        "government_units_count": total_govt_units,
        "organizations_count": total_organizations,
        "warnings_count": total_warnings,
        "total_audit_logs": total_audit_logs,
        "system_health": {
            "database": "connected",
            "smtp_ready": smtp_status.get("ready", False),
            "smtp_message": smtp_status.get("message", ""),
            "sms_ready": sms_status.get("ready", False),
            "sms_provider": sms_status.get("provider", "dummy"),
            "sms_message": sms_status.get("message", ""),
        },
    }


# ---------------------------------------------------------------------------
# 2. Verification Center (6 Tiers with Full Permanent Audit)
# ---------------------------------------------------------------------------

@router.get("/verifications")
async def list_admin_verifications(
    tier: str = Query("all", description="Filter by tier: all, central, state, district, local, employer, institute"),
    status: str = Query("ALL", description="Filter by status: ALL, PENDING, APPROVED, REJECTED, MORE_INFORMATION_REQUIRED, SUSPENDED, REVOKED"),
    search: str | None = Query(None, description="Search applicant email, phone, name, organization, unit"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve verification applications across all 6 administrative tiers
    with complete applicant, verifier, organization, and unit details.
    """
    query = (
        select(
            VerificationApplication,
            User.email.label("applicant_email"),
            User.phone.label("applicant_phone"),
            User.account_type.label("applicant_account_type"),
            GovernmentUnit.name.label("unit_name"),
            GovernmentUnit.code.label("unit_code"),
            GovernmentUnit.level.label("unit_level"),
            GovernmentUnit.unit_type.label("unit_type"),
        )
        .join(User, User.id == VerificationApplication.applicant_user_id)
        .outerjoin(GovernmentUnit, GovernmentUnit.id == VerificationApplication.government_unit_id)
    )

    # Status filter
    if status and status != "ALL":
        query = query.where(VerificationApplication.status == status.upper())

    # Tier filter
    tier_l = tier.lower()
    if tier_l == "employer":
        query = query.where(VerificationApplication.application_type.ilike("%EMPLOYER%"))
    elif tier_l in ("institute", "training_institute", "college"):
        query = query.where(
            or_(
                VerificationApplication.application_type.ilike("%INSTITUTE%"),
                VerificationApplication.application_type.ilike("%COLLEGE%"),
            )
        )
    elif tier_l == "central":
        query = query.where(
            or_(
                GovernmentUnit.level == 1,
                GovernmentUnit.unit_type.ilike("%CENTRAL%"),
                VerificationApplication.application_type.ilike("%CENTRAL%"),
            )
        )
    elif tier_l == "state":
        query = query.where(
            or_(
                GovernmentUnit.level == 2,
                GovernmentUnit.unit_type.ilike("%STATE%"),
                VerificationApplication.application_type.ilike("%STATE%"),
            )
        )
    elif tier_l == "district":
        query = query.where(
            or_(
                GovernmentUnit.level == 3,
                GovernmentUnit.unit_type.ilike("%DISTRICT%"),
                VerificationApplication.application_type.ilike("%DISTRICT%"),
            )
        )
    elif tier_l == "local":
        query = query.where(
            or_(
                GovernmentUnit.level == 4,
                GovernmentUnit.unit_type.ilike("%LOCAL%"),
                GovernmentUnit.unit_type.ilike("%BLOCK%"),
                GovernmentUnit.unit_type.ilike("%MUNICIPAL%"),
                VerificationApplication.application_type.ilike("%LOCAL%"),
            )
        )

    # Search filter
    if search:
        search_kw = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(search_kw),
                User.phone.ilike(search_kw),
                GovernmentUnit.name.ilike(search_kw),
                GovernmentUnit.code.ilike(search_kw),
                VerificationApplication.application_type.ilike(search_kw),
            )
        )

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_query)) or 0

    # Order and paginate
    query = query.order_by(VerificationApplication.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    items = []
    for app_row in rows:
        v_app = app_row[0]
        # Query applicant name & organization if available
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == v_app.applicant_user_id)
        )
        org = org_res.scalars().first()

        # Query verifier email if reviewed
        verifier_email = None
        if v_app.verifier_user_id:
            ver_u = await db.get(User, v_app.verifier_user_id)
            if ver_u:
                verifier_email = ver_u.email

        # Deduce tier string
        inferred_tier = "district"
        if "EMPLOYER" in (v_app.application_type or "").upper():
            inferred_tier = "employer"
        elif "INSTITUTE" in (v_app.application_type or "").upper():
            inferred_tier = "institute"
        elif app_row.unit_level == 1 or "CENTRAL" in (app_row.unit_type or "").upper():
            inferred_tier = "central"
        elif app_row.unit_level == 2 or "STATE" in (app_row.unit_type or "").upper():
            inferred_tier = "state"
        elif app_row.unit_level == 3 or "DISTRICT" in (app_row.unit_type or "").upper():
            inferred_tier = "district"
        elif app_row.unit_level == 4 or "LOCAL" in (app_row.unit_type or "").upper():
            inferred_tier = "local"

        items.append({
            "id": str(v_app.id),
            "applicant_user_id": str(v_app.applicant_user_id),
            "applicant_email": app_row.applicant_email,
            "applicant_phone": app_row.applicant_phone,
            "applicant_account_type": app_row.applicant_account_type,
            "organization_id": str(org.id) if org else None,
            "organization_name": org.legal_name if org else (org.display_name if org else None),
            "organization_type": org.organization_type if org else None,
            "government_unit_id": str(v_app.government_unit_id) if v_app.government_unit_id else None,
            "government_unit_name": app_row.unit_name,
            "government_unit_code": app_row.unit_code,
            "government_unit_level": app_row.unit_level,
            "tier": inferred_tier,
            "application_type": v_app.application_type,
            "status": v_app.status,
            "submitted_data": v_app.submitted_data,
            "remarks": v_app.remarks,
            "rejection_reason": v_app.rejection_reason,
            "verifier_user_id": str(v_app.verifier_user_id) if v_app.verifier_user_id else None,
            "verifier_email": verifier_email,
            "submitted_at": v_app.submitted_at.isoformat() if v_app.submitted_at else None,
            "reviewed_at": v_app.reviewed_at.isoformat() if v_app.reviewed_at else None,
            "created_at": v_app.created_at.isoformat() if v_app.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/verifications/{application_id}/action")
async def perform_verification_action(
    application_id: UUID,
    payload: VerificationActionRequest,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Approve, Reject, Request Information, Suspend, or Revoke any verification application.
    Permanently writes full audit trail with: applicant, verifier/admin, role, jurisdiction,
    timestamp, action, previous status, new status, and reason.
    """
    admin_user, _ = current_admin
    now = datetime.now(timezone.utc)

    application = await db.get(VerificationApplication, application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification application '{application_id}' not found.",
        )

    old_status = application.status
    action_map = {
        "APPROVE": VerificationStatus.APPROVED.value,
        "REJECT": VerificationStatus.REJECTED.value,
        "REQUEST_INFO": VerificationStatus.MORE_INFORMATION_REQUIRED.value,
        "SUSPEND": VerificationStatus.SUSPENDED.value,
        "REVOKE": VerificationStatus.REVOKED.value,
    }
    new_status = action_map[payload.action]

    if payload.action in ("REJECT", "SUSPEND", "REVOKE", "REQUEST_INFO") and not payload.reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A mandatory reason is required to {payload.action.lower()} a verification application.",
        )

    # Fetch applicant and jurisdiction
    applicant = await db.get(User, application.applicant_user_id)
    unit = await db.get(GovernmentUnit, application.government_unit_id) if application.government_unit_id else None
    jurisdiction_label = f"{unit.name} ({unit.code})" if unit else "Platform Direct"

    # Update application
    application.status = new_status
    application.verifier_user_id = admin_user.id
    application.reviewed_at = now
    if payload.remarks:
        application.remarks = payload.remarks
    if payload.action in ("REJECT", "SUSPEND", "REVOKE"):
        application.rejection_reason = payload.reason
    elif payload.action == "APPROVE":
        application.rejection_reason = None

    # Sync linked Organization status if applicant owns one
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
    )
    org = org_res.scalars().first()
    if org:
        org.verification_status = new_status

    # Permanent Audit Log
    audit = AuditLogService(db)
    audit_metadata = {
        "applicant_user_id": str(application.applicant_user_id),
        "applicant_email": applicant.email if applicant else None,
        "applicant_phone": applicant.phone if applicant else None,
        "verifier_admin_id": str(admin_user.id),
        "verifier_admin_email": admin_user.email,
        "role": "SUPER_ADMIN",
        "jurisdiction": jurisdiction_label,
        "action": payload.action,
        "previous_status": old_status,
        "new_status": new_status,
        "reason": payload.reason,
        "remarks": payload.remarks,
        "timestamp": now.isoformat(),
        "application_type": application.application_type,
        "organization_id": str(org.id) if org else None,
    }

    action_enum = AuditAction.APPROVE if payload.action == "APPROVE" else (
        AuditAction.REJECT if payload.action == "REJECT" else AuditAction.UPDATE
    )

    await audit.record(
        actor_user_id=admin_user.id,
        action=action_enum,
        resource_type="VerificationApplication",
        resource_id=application.id,
        description=f"Verification status changed from {old_status} to {new_status}. Reason: {payload.reason or 'Approved by Super Admin'}",
        metadata_json=audit_metadata,
    )

    # In-app notification to applicant
    if applicant:
        notif_msg = (
            f"Your verification application ({application.application_type}) has been {new_status} by Super Administrator."
            + (f" Reason: {payload.reason}" if payload.reason else "")
        )
        db.add(
            Notification(
                user_id=applicant.id,
                notification_type="CERTIFICATE_VERIFIED" if payload.action == "APPROVE" else "GOVERNMENT_ALERT",
                priority=NotificationPriority.HIGH,
                title=f"Verification Application: {new_status}",
                message=notif_msg,
                entity_type="VerificationApplication",
                entity_id=application.id,
                action_url="/verification-pending",
            )
        )

    await db.commit()
    await db.refresh(application)

    return {
        "success": True,
        "message": f"Verification application {new_status} successfully.",
        "application_id": str(application.id),
        "previous_status": old_status,
        "new_status": new_status,
        "audit_record": audit_metadata,
    }


# ---------------------------------------------------------------------------
# 3. User Management (Search, Profile, Status, Warnings, Unlock)
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    response: Response,
    q: str | None = Query(None, description="Search by email, phone, or ID"),
    account_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    is_suspended: bool | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Search and filter platform users with roles, linked profile, and warning counts.
    """
    now = datetime.now(timezone.utc)
    query = select(User)

    if q:
        kw = f"%{q.strip()}%"
        query = query.where(or_(User.email.ilike(kw), User.phone.ilike(kw)))

    if account_type and account_type != "ALL":
        query = query.where(User.account_type == account_type.upper())

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if is_suspended is not None:
        query = query.where(User.is_suspended == is_suspended)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_query)) or 0

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    users = list(result.scalars().all())

    response_list = []
    for u in users:
        # Roles
        roles_res = await db.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id, UserRole.revoked_at.is_(None))
        )
        roles = list(roles_res.scalars().all())

        # Warnings count
        warn_cnt = await db.scalar(
            select(func.count(UserWarning.id)).where(UserWarning.user_id == u.id)
        ) or 0

        # Linked entity name
        entity_name = None
        if u.account_type == "CANDIDATE":
            cp = (await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == u.id))).scalars().first()
            if cp:
                entity_name = f"{cp.first_name} {cp.last_name}".strip()
        elif u.account_type in ("EMPLOYER", "TRAINING_INSTITUTE"):
            org = (await db.execute(select(Organization).where(Organization.owner_user_id == u.id))).scalars().first()
            if org:
                entity_name = org.display_name or org.legal_name

        is_locked = bool(u.locked_until and (u.locked_until.replace(tzinfo=timezone.utc) if u.locked_until.tzinfo is None else u.locked_until) > now)

        response_list.append({
            "id": str(u.id),
            "email": u.email,
            "phone": u.phone,
            "account_type": u.account_type,
            "entity_name": entity_name,
            "is_active": u.is_active,
            "is_suspended": u.is_suspended,
            "is_locked": is_locked,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "failed_login_attempts": u.failed_login_attempts,
            "email_verified": u.email_verified,
            "phone_verified": u.phone_verified,
            "government_unit_id": str(u.government_unit_id) if u.government_unit_id else None,
            "roles": roles,
            "warnings_count": warn_cnt,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        })

    response.headers["X-Total-Count"] = str(total)
    return response_list


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve comprehensive user account details, linked profiles, warnings, and audit history.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # Roles
    roles_res = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, UserRole.revoked_at.is_(None))
    )
    roles = list(roles_res.scalars().all())

    # Linked Organization or CandidateProfile
    org = (await db.execute(select(Organization).where(Organization.owner_user_id == user.id))).scalars().first()
    cand = (await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))).scalars().first()

    # Government Unit
    unit = await db.get(GovernmentUnit, user.government_unit_id) if user.government_unit_id else None

    # Warnings
    warnings_res = await db.execute(
        select(UserWarning).where(UserWarning.user_id == user.id).order_by(UserWarning.created_at.desc())
    )
    warnings = [
        {
            "id": str(w.id),
            "title": w.warning_title,
            "message": w.warning_message,
            "reason": w.reason,
            "severity": w.severity,
            "created_at": w.created_at.isoformat(),
        }
        for w in warnings_res.scalars().all()
    ]

    # Recent Audit Logs for this user
    audit_res = await db.execute(
        select(AuditLog)
        .where(or_(AuditLog.resource_id == user.id, AuditLog.actor_user_id == user.id))
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    audit_records = [
        {
            "id": str(a.id),
            "action": a.action,
            "description": a.description,
            "created_at": a.created_at.isoformat(),
            "metadata": a.metadata_json,
        }
        for a in audit_res.scalars().all()
    ]

    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "is_suspended": user.is_suspended,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        "failed_login_attempts": user.failed_login_attempts,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "roles": roles,
        "government_unit": {
            "id": str(unit.id),
            "name": unit.name,
            "code": unit.code,
            "level": unit.level,
        } if unit else None,
        "organization": {
            "id": str(org.id),
            "legal_name": org.legal_name,
            "display_name": org.display_name,
            "type": org.organization_type,
            "verification_status": org.verification_status,
        } if org else None,
        "candidate": {
            "id": str(cand.id),
            "name": f"{cand.first_name} {cand.last_name}".strip(),
            "status": cand.status,
        } if cand else None,
        "warnings": warnings,
        "recent_audit_logs": audit_records,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Suspend, activate, block, or restore access for a user account with mandatory reason.
    """
    admin_user, _ = current_admin
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    old_active = target_user.is_active
    old_suspended = target_user.is_suspended

    if status_update.is_active is not None:
        target_user.is_active = status_update.is_active
    if status_update.is_suspended is not None:
        target_user.is_suspended = status_update.is_suspended

    action = AuditAction.SUSPEND if target_user.is_suspended else (
        AuditAction.RESTORE if old_suspended and not target_user.is_suspended else AuditAction.UPDATE
    )

    effective_reason = (status_update.reason or "").strip() or "Administrative status update"

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=action,
        resource_type="user",
        resource_id=target_user.id,
        description=f"User status updated (active: {old_active}->{target_user.is_active}, suspended: {old_suspended}->{target_user.is_suspended}). Reason: {effective_reason}",
        metadata_json={
            "admin_id": str(admin_user.id),
            "admin_email": admin_user.email,
            "target_user_id": str(target_user.id),
            "old_active": old_active,
            "new_active": target_user.is_active,
            "old_suspended": old_suspended,
            "new_suspended": target_user.is_suspended,
            "reason": effective_reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    await db.commit()
    return {
        "success": True,
        "message": f"User '{user_id}' status updated successfully.",
        "is_active": target_user.is_active,
        "is_suspended": target_user.is_suspended,
        "reason": effective_reason,
    }


@router.post("/users/{user_id}/warning")
async def issue_user_warning(
    user_id: UUID,
    payload: UserWarningCreate,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Issue an individual administrative warning message to a user account.
    Persists to UserWarning, sends in-app notification, and writes to audit log.
    """
    admin_user, _ = current_admin
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # 1. Create UserWarning record
    warning = UserWarning(
        user_id=target_user.id,
        admin_id=admin_user.id,
        warning_title=payload.title,
        warning_message=payload.message,
        reason=payload.reason,
        severity=payload.severity,
    )
    db.add(warning)

    # 2. In-App Notification
    db.add(
        Notification(
            user_id=target_user.id,
            notification_type="GOVERNMENT_ALERT",
            priority=NotificationPriority.CRITICAL if payload.severity in ("HIGH", "CRITICAL") else NotificationPriority.HIGH,
            title=f"Administrative Warning: {payload.title}",
            message=payload.message,
            entity_type="UserWarning",
            entity_id=warning.id,
            action_url="/notifications",
        )
    )

    # 3. Permanent Audit Log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=AuditAction.UPDATE,
        resource_type="user",
        resource_id=target_user.id,
        description=f"Administrative warning issued to user: '{payload.title}'. Reason: {payload.reason}",
        metadata_json={
            "admin_id": str(admin_user.id),
            "admin_email": admin_user.email,
            "target_user_id": str(target_user.id),
            "warning_title": payload.title,
            "warning_message": payload.message,
            "reason": payload.reason,
            "severity": payload.severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    await db.commit()
    await db.refresh(warning)

    return {
        "success": True,
        "message": f"Administrative warning issued to user '{user_id}'.",
        "warning_id": str(warning.id),
        "created_at": warning.created_at.isoformat(),
    }


@router.post("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: UUID,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Unlock a locked user account and reset failed login attempts.
    """
    admin_user, _ = current_admin
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    target_user.locked_until = None
    target_user.failed_login_attempts = 0

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=AuditAction.RESTORE,
        resource_type="user",
        resource_id=target_user.id,
        description=f"User account '{target_user.email or target_user.id}' unlocked by Super Admin.",
    )

    await db.commit()
    return {
        "success": True,
        "message": f"User account '{user_id}' unlocked successfully.",
    }


# ---------------------------------------------------------------------------
# 4. Form & Platform Control (Landing Page, Signup, Login, Validation)
# ---------------------------------------------------------------------------

@router.get("/platform-config/{config_key}")
async def get_platform_config(
    config_key: str,
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch active configuration revision for the specified platform component.
    """
    res = await db.execute(
        select(PlatformConfig)
        .where(PlatformConfig.config_key == config_key, PlatformConfig.is_active.is_(True))
        .order_by(PlatformConfig.version.desc())
    )
    cfg = res.scalars().first()

    if not cfg:
        # Fall back to built-in default if unconfigured
        default_data = DEFAULT_PLATFORM_CONFIGS.get(config_key, {})
        return {
            "config_key": config_key,
            "version": 0,
            "is_active": True,
            "config_data": default_data,
            "change_reason": "System default baseline",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "id": str(cfg.id),
        "config_key": cfg.config_key,
        "version": cfg.version,
        "is_active": cfg.is_active,
        "config_data": cfg.config_data,
        "change_reason": cfg.change_reason,
        "created_at": cfg.created_at.isoformat(),
    }


@router.post("/platform-config/{config_key}")
async def save_platform_config(
    config_key: str,
    payload: PlatformConfigPayload,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Save a new version of platform configuration.
    Historical revisions are NEVER overwritten; previous versions are marked is_active=False.
    Mandatory change_reason is permanently captured in the audit log.
    """
    admin_user, _ = current_admin

    # Fetch latest version number
    latest_res = await db.execute(
        select(PlatformConfig)
        .where(PlatformConfig.config_key == config_key)
        .order_by(PlatformConfig.version.desc())
    )
    previous_active = latest_res.scalars().first()
    next_version = (previous_active.version + 1) if previous_active else 1
    old_data = previous_active.config_data if previous_active else DEFAULT_PLATFORM_CONFIGS.get(config_key, {})

    # Mark previous active version inactive
    if previous_active and previous_active.is_active:
        previous_active.is_active = False

    # Insert new version
    new_cfg = PlatformConfig(
        config_key=config_key,
        version=next_version,
        config_data=payload.config_data,
        is_active=True,
        updated_by_user_id=admin_user.id,
        change_reason=payload.change_reason,
    )
    db.add(new_cfg)
    await db.flush()

    # Permanent Audit Log with before/after comparison
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=AuditAction.UPDATE,
        resource_type="PlatformConfig",
        resource_id=new_cfg.id,
        description=f"Platform configuration '{config_key}' updated to version {next_version}. Reason: {payload.change_reason}",
        metadata_json={
            "admin_id": str(admin_user.id),
            "admin_email": admin_user.email,
            "config_key": config_key,
            "version": next_version,
            "change_reason": payload.change_reason,
            "old_value": old_data,
            "new_value": payload.config_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    await db.commit()
    await db.refresh(new_cfg)

    return {
        "success": True,
        "message": f"Configuration '{config_key}' saved as version {next_version}.",
        "config_key": config_key,
        "version": new_cfg.version,
        "change_reason": new_cfg.change_reason,
        "created_at": new_cfg.created_at.isoformat(),
    }


@router.get("/platform-config/{config_key}/history")
async def get_platform_config_history(
    config_key: str,
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve full revision history for before/after comparison and rollback.
    """
    res = await db.execute(
        select(PlatformConfig, User.email)
        .outerjoin(User, User.id == PlatformConfig.updated_by_user_id)
        .where(PlatformConfig.config_key == config_key)
        .order_by(PlatformConfig.version.desc())
    )
    rows = res.all()

    return [
        {
            "id": str(cfg.id),
            "config_key": cfg.config_key,
            "version": cfg.version,
            "is_active": cfg.is_active,
            "config_data": cfg.config_data,
            "change_reason": cfg.change_reason,
            "updated_by_email": admin_email,
            "created_at": cfg.created_at.isoformat(),
        }
        for cfg, admin_email in rows
    ]


@router.post("/platform-config/{config_key}/rollback/{target_version}")
async def rollback_platform_config(
    config_key: str,
    target_version: int,
    payload: dict[str, str],
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Roll back to a previous configuration version by creating a new version with that historical data.
    """
    admin_user, _ = current_admin
    reason = payload.get("reason") or f"Rollback to revision {target_version}"

    # Find target version
    target_res = await db.execute(
        select(PlatformConfig).where(
            PlatformConfig.config_key == config_key,
            PlatformConfig.version == target_version,
        )
    )
    target_cfg = target_res.scalars().first()
    if not target_cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {target_version} of '{config_key}' not found.",
        )

    # Save as new version
    return await save_platform_config(
        config_key=config_key,
        payload=PlatformConfigPayload(
            config_data=target_cfg.config_data,
            change_reason=f"[ROLLBACK to v{target_version}] {reason}",
        ),
        current_admin=current_admin,
        db=db,
    )


# ---------------------------------------------------------------------------
# 5. Audit History & Authority
# ---------------------------------------------------------------------------

@router.get("/audit-logs")
async def list_admin_audit_logs(
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    actor_user_id: UUID | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve platform audit trail with actor details, action badges,
    and before/after metadata comparison.
    """
    query = (
        select(AuditLog, User.email.label("actor_email"))
        .outerjoin(User, User.id == AuditLog.actor_user_id)
    )

    if action and action != "ALL":
        query = query.where(AuditLog.action == action.upper())

    if resource_type and resource_type != "ALL":
        query = query.where(AuditLog.resource_type == resource_type)

    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)

    if search:
        kw = f"%{search.strip()}%"
        query = query.where(
            or_(
                AuditLog.description.ilike(kw),
                User.email.ilike(kw),
                AuditLog.resource_type.ilike(kw),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_query)) or 0

    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).all()

    items = []
    for log, actor_email in rows:
        items.append({
            "id": str(log.id),
            "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
            "actor_email": actor_email,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.metadata_json or {},
            "created_at": log.created_at.isoformat(),
        })

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# 6. Legacy / Role / Unit Management
# ---------------------------------------------------------------------------

@router.put("/users/{user_id}/government-unit")
async def assign_government_unit(
    user_id: UUID,
    payload: AssignGovtUnitRequest,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    admin_user, _ = current_admin
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    if payload.government_unit_id:
        unit = await db.get(GovernmentUnit, payload.government_unit_id)
        if not unit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Government unit not found.")

    old_unit = target_user.government_unit_id
    target_user.government_unit_id = payload.government_unit_id

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=AuditAction.UPDATE,
        resource_type="user",
        resource_id=target_user.id,
        description=f"Assigned government unit from {old_unit} to {payload.government_unit_id}",
    )
    await db.commit()
    return {"success": True, "message": "Government unit assigned."}


@router.post("/users/{user_id}/roles")
async def assign_user_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    current_admin: tuple[User, list[str]] = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    admin_user, _ = current_admin
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    role_res = await db.execute(select(Role).where(Role.code == payload.role_code, Role.is_active.is_(True)))
    role = role_res.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{payload.role_code}' does not exist.")

    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == target_user.id, UserRole.role_id == role.id, UserRole.revoked_at.is_(None))
    )
    if existing.scalar_one_or_none():
        return {"success": True, "message": f"User already has active role '{payload.role_code}'."}

    user_role = UserRole(user_id=target_user.id, role_id=role.id)
    db.add(user_role)

    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=admin_user.id,
        action=AuditAction.CREATE,
        resource_type="user_role",
        resource_id=role.id,
        description=f"Assigned role '{payload.role_code}' to user '{target_user.email or target_user.id}'.",
    )
    await db.commit()
    return {"success": True, "message": f"Role '{payload.role_code}' granted to user."}
