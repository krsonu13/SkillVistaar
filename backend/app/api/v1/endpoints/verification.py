from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_manager
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.institution_profile import InstitutionProfile, InstitutionVerificationStatus
from app.models.notification import NotificationPriority, NotificationType
from app.models.organization import Organization, OrganizationVerificationStatus
from app.models.user import User
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.schemas.verification_application import (
    VerificationApplicationResponse,
    VerificationApplicationResubmit,
    VerificationApplicationReview,
)
from app.services.audit_log_service import AuditLogService
from app.services.jurisdiction_service import (
    enforce_jurisdiction_access,
    enforce_verification_authority,
    get_authorized_unit_ids,
    get_eligible_verifier_user_ids,
    validate_verification_authority,
)
from app.services.notification_service import NotificationService

router = APIRouter(
    prefix="/verification",
    tags=["Verification"],
)


@router.get("/pending", response_model=list[VerificationApplicationResponse])
async def list_pending_verifications(
    application_type: str | None = Query(None),
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> list[VerificationApplication]:
    """
    List pending verification applications within caller's jurisdiction and authority matrix.
    Enforces that verifiers only see applications they have strict statutory authority to review.
    """
    user, roles = current_user_and_roles
    is_admin = user.account_type == "SUPER_ADMIN" or "SUPER_ADMIN" in roles
    is_govt = user.account_type == "GOVERNMENT" or any("GOVERNMENT" in r for r in roles)

    if not is_admin and not is_govt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized government verifiers.",
        )

    query = select(VerificationApplication).where(
        VerificationApplication.status == VerificationStatus.PENDING.value
    )

    if application_type:
        query = query.where(
            VerificationApplication.application_type == application_type
        )

    query = query.order_by(VerificationApplication.created_at.desc())
    result = await db.execute(query)
    all_pending = list(result.scalars().all())

    # Filter through the multi-tier verification authority rule engine
    filtered: list[VerificationApplication] = []
    for app in all_pending:
        allowed, _ = await validate_verification_authority(
            db=db,
            verifier_user=user,
            verifier_roles=roles,
            target_entity_type=app.application_type,
            target_unit_id=app.government_unit_id,
        )
        if allowed:
            filtered.append(app)

    return filtered


@router.get("/applications/{application_id}", response_model=VerificationApplicationResponse)
async def get_application(
    application_id: UUID,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> VerificationApplication:
    """
    Get verification application by ID.
    """
    user, roles = current_user_and_roles
    app = await db.get(VerificationApplication, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification application '{application_id}' not found.",
        )

    # Allow applicant, or verifier in jurisdiction
    if app.applicant_user_id != user.id:
        await enforce_jurisdiction_access(
            db, user, roles, app.government_unit_id, "view this verification application"
        )

    return app


@router.post("/applications/{application_id}/review", response_model=VerificationApplicationResponse)
async def review_verification_app_unified(
    application_id: UUID,
    payload: VerificationApplicationReview,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> VerificationApplication:
    """
    Approve, reject, or request more information on a verification application.
    Enforces strict jurisdiction authority matrix:
      - Central Govt: verified only by Super Admin
      - State Govt: verified by Central Govt or Super Admin
      - District Govt: verified by respective State Govt, Central Govt, or Super Admin
      - Local Govt: verified ONLY by respective District Govt (Super Admin & Central restricted)
      - Training Institutes & Employers: verified by respective District Govt, State Govt, Central Govt, or Super Admin
    Synchronizes status across User, Organization, and InstitutionProfile.
    Emits real-time notifications and WebSocket events.
    """
    user, roles = current_user_and_roles
    app = await db.get(VerificationApplication, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification application '{application_id}' not found.",
        )

    if app.applicant_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot review your own verification application.",
        )

    # Strict multi-tier verification authority enforcement
    await enforce_verification_authority(
        db, user, roles, app.application_type, app.government_unit_id, "review this verification application"
    )

    old_status = app.status
    now = datetime.now(timezone.utc)
    app.status = payload.status
    app.verifier_user_id = user.id
    app.reviewed_at = now
    app.remarks = payload.remarks
    app.rejection_reason = payload.reason

    # Synchronize linked Organization and InstitutionProfile
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == app.applicant_user_id)
    )
    for org in org_res.scalars().all():
        org.verification_status = payload.status
        if payload.status == "APPROVED" and app.government_unit_id and not org.government_unit_id:
            org.government_unit_id = app.government_unit_id

        inst_res = await db.execute(
            select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
        )
        for inst in inst_res.scalars().all():
            inst.verification_status = payload.status

    # If applicant user is Government, assign government unit upon approval
    applicant_user = await db.get(User, app.applicant_user_id)
    if applicant_user and applicant_user.account_type == "GOVERNMENT":
        if payload.status == "APPROVED" and app.government_unit_id:
            applicant_user.government_unit_id = app.government_unit_id

    # Record Audit log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.APPROVE if payload.status == "APPROVED" else (AuditAction.REJECT if payload.status == "REJECTED" else AuditAction.UPDATE),
        resource_type="verification_application",
        resource_id=app.id,
        description=f"Verification application {app.id} status updated from {old_status} to {payload.status}.",
        metadata_json={
            "verifier_user_id": str(user.id),
            "old_status": old_status,
            "new_status": payload.status,
            "remarks": payload.remarks,
            "reason": payload.reason,
            "government_unit_id": str(app.government_unit_id) if app.government_unit_id else None,
        },
    )

    # Create persistent Notification for applicant
    notif_service = NotificationService(db)
    human_status = payload.status.replace("_", " ").title()
    await notif_service.create_notification(
        user_id=app.applicant_user_id,
        notification_type=NotificationType.VERIFICATION_STATUS_UPDATED,
        title=f"Verification Application {human_status}",
        message=payload.remarks or f"Your {app.application_type.lower()} verification application has been marked as {human_status}.",
        priority=NotificationPriority.HIGH,
        entity_type="VERIFICATION_APPLICATION",
        entity_id=app.id,
    )

    # Real-time WebSocket event dispatch to applicant
    await event_manager.send_to_user(
        app.applicant_user_id,
        "VERIFICATION_STATUS_UPDATED",
        {
            "application_id": str(app.id),
            "status": payload.status,
            "remarks": payload.remarks,
            "reason": payload.reason,
            "entity_type": app.application_type,
        },
    )

    # Real-time broadcast to verifiers regarding queue update
    eligible_verifiers = await get_eligible_verifier_user_ids(db, app.application_type, app.government_unit_id)
    await event_manager.broadcast_to_users(
        eligible_verifiers,
        "VERIFICATION_QUEUE_UPDATED",
        {
            "action": "STATUS_CHANGED",
            "application_id": str(app.id),
            "status": payload.status,
        },
    )

    await db.commit()
    await db.refresh(app)
    return app


@router.post("/applications/{application_id}/resubmit", response_model=VerificationApplicationResponse)
async def resubmit_verification_application(
    application_id: UUID,
    payload: VerificationApplicationResubmit,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> VerificationApplication:
    """
    Allow applicant to resubmit an application in MORE_INFORMATION_REQUIRED status with updated data/remarks.
    Resets status to PENDING and notifies eligible verifiers.
    """
    user, _ = current_user_and_roles
    app = await db.get(VerificationApplication, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification application '{application_id}' not found.",
        )

    if app.applicant_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only resubmit your own verification application.",
        )

    if app.status != VerificationStatus.MORE_INFORMATION_REQUIRED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application cannot be resubmitted when in '{app.status}' status.",
        )

    old_status = app.status
    app.status = VerificationStatus.PENDING.value
    if payload.submitted_data:
        app.submitted_data = json.dumps(payload.submitted_data) if isinstance(payload.submitted_data, dict) else str(payload.submitted_data)
    if payload.remarks:
        app.remarks = payload.remarks

    # Also update organization/institution to PENDING
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == app.applicant_user_id)
    )
    for org in org_res.scalars().all():
        org.verification_status = OrganizationVerificationStatus.PENDING.value
        inst_res = await db.execute(
            select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
        )
        for inst in inst_res.scalars().all():
            inst.verification_status = InstitutionVerificationStatus.PENDING.value

    # Audit log
    audit = AuditLogService(db)
    await audit.record(
        actor_user_id=user.id,
        action=AuditAction.UPDATE,
        resource_type="verification_application",
        resource_id=app.id,
        description=f"Applicant resubmitted verification application {app.id}.",
        metadata_json={
            "old_status": old_status,
            "new_status": app.status,
            "remarks": payload.remarks,
        },
    )

    # Notify verifiers
    eligible_verifiers = await get_eligible_verifier_user_ids(db, app.application_type, app.government_unit_id)
    notif_service = NotificationService(db)
    for verifier_id in eligible_verifiers:
        await notif_service.create_notification(
            user_id=verifier_id,
            notification_type=NotificationType.GOVERNMENT_ALERT,
            title="Verification Application Resubmitted",
            message=f"Application for {app.application_type.replace('_', ' ').title()} was resubmitted with requested information.",
            priority=NotificationPriority.HIGH,
            entity_type="VERIFICATION_APPLICATION",
            action_url="/dashboard/government",
        )
    await event_manager.broadcast_to_users(
        eligible_verifiers,
        "VERIFICATION_QUEUE_UPDATED",
        {
            "action": "RESUBMITTED",
            "application_id": str(app.id),
        },
    )

    await db.commit()
    await db.refresh(app)
    return app
