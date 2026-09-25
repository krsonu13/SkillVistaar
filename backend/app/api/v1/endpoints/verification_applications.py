from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    APPROVE_VERIFICATION,
    CREATE_VERIFICATION,
    REJECT_VERIFICATION,
    REQUEST_VERIFICATION_INFO,
    REVIEW_VERIFICATION,
    SUPER_ADMIN,
    VIEW_VERIFICATION,
    get_permissions_for_roles,
    has_role,
    require_permissions,
)
from app.db.session import get_db
from app.models.government_data_access_authorization import (
    GovernmentDataAccessAuthorization,
    GovernmentDataAccessAuthorizationStatus,
)
from app.models.government_unit import GovernmentUnit
from app.models.user import User
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.models.verifier_authorization import VerifierAuthorization
from app.models.organization import Organization, OrganizationVerificationStatus
from app.models.institution_profile import InstitutionProfile, InstitutionVerificationStatus
from app.schemas.verification_application import (
    VerificationApplicationCreate,
    VerificationApplicationResponse,
    VerificationApplicationReview,
)
from app.services.audit_log_service import AuditLogService


router = APIRouter(
    prefix="/verification-applications",
    tags=["Verification Applications"],
)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc

    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Verification application operation failed.",
    ) from exc


async def _is_super_admin(
    current_user: User,
    roles: list[str],
) -> bool:
    return (
        current_user.is_active
        and not current_user.is_suspended
        and has_role(roles, SUPER_ADMIN)
    )


async def _get_authorized_unit_ids(
    db: AsyncSession,
    user_id: UUID,
    roles: list[str],
) -> set[UUID]:
    """
    Return all government units the user may operate within.

    Authorization sources:
    1. Super Admin -> every active government unit.
    2. Active verifier authorizations.
    3. Active government data-access authorizations.
    4. Approved verification applications belonging to the user.

    A unit grants access to that unit and all active descendants.
    """

    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active or user.is_suspended:
        return set()

    if has_role(roles, SUPER_ADMIN):
        result = await db.execute(
            select(GovernmentUnit.id).where(
                GovernmentUnit.is_active.is_(True)
            )
        )
        return set(result.scalars().all())

    source_unit_ids: set[UUID] = set()

    verifier_result = await db.execute(
        select(VerifierAuthorization.government_unit_id).where(
            VerifierAuthorization.verifier_user_id == user_id,
            VerifierAuthorization.is_active.is_(True),
        )
    )

    source_unit_ids.update(
        unit_id
        for unit_id in verifier_result.scalars().all()
        if unit_id is not None
    )

    data_result = await db.execute(
        select(
            GovernmentDataAccessAuthorization.government_unit_id
        ).where(
            GovernmentDataAccessAuthorization.user_id == user_id,
            GovernmentDataAccessAuthorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE.value,
        )
    )

    source_unit_ids.update(
        unit_id
        for unit_id in data_result.scalars().all()
        if unit_id is not None
    )

    application_result = await db.execute(
        select(VerificationApplication.government_unit_id).where(
            VerificationApplication.applicant_user_id == user_id,
            VerificationApplication.status
            == VerificationStatus.APPROVED.value,
            VerificationApplication.government_unit_id.is_not(None),
        )
    )

    source_unit_ids.update(
        unit_id
        for unit_id in application_result.scalars().all()
        if unit_id is not None
    )

    if not source_unit_ids:
        return set()

    accessible_ids: set[UUID] = set()

    for source_id in source_unit_ids:
        hierarchy = (
            select(GovernmentUnit.id)
            .where(
                GovernmentUnit.id == source_id,
                GovernmentUnit.is_active.is_(True),
            )
            .cte(
                name=(
                    "government_hierarchy_"
                    f"{str(source_id).replace('-', '_')[:12]}"
                ),
                recursive=True,
            )
        )

        descendants = hierarchy.union_all(
            select(GovernmentUnit.id).where(
                GovernmentUnit.parent_id == hierarchy.c.id,
                GovernmentUnit.is_active.is_(True),
            )
        )

        result = await db.execute(
            select(descendants.c.id)
        )

        accessible_ids.update(result.scalars().all())

    return accessible_ids


async def _can_access_application(
    db: AsyncSession,
    current_user: User,
    roles: list[str],
    application: VerificationApplication,
) -> bool:
    if application.applicant_user_id == current_user.id:
        return True

    if await _is_super_admin(current_user, roles):
        return True

    if application.government_unit_id is None:
        return False

    accessible_units = await _get_authorized_unit_ids(
        db,
        current_user.id,
        roles,
    )

    return application.government_unit_id in accessible_units


async def _require_application_jurisdiction(
    db: AsyncSession,
    current_user: User,
    roles: list[str],
    application: VerificationApplication,
) -> None:
    if not await _can_access_application(
        db,
        current_user,
        roles,
        application,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized to access this verification "
                "application within your government jurisdiction."
            ),
        )


async def _record_verification_audit(
    db: AsyncSession,
    *,
    current_user: User,
    application: VerificationApplication,
    action: str,
    description: str,
    metadata: dict | None = None,
) -> None:
    """
    Record a verification action in the audit log.

    This is intentionally called before the surrounding transaction
    commits so the verification state change and audit record are
    persisted together.
    """

    audit_metadata = {
        "government_unit_id": (
            str(application.government_unit_id)
            if application.government_unit_id
            else None
        ),
        "application_type": application.application_type,
        "verification_status": application.status,
    }

    if metadata:
        audit_metadata.update(metadata)

    await AuditLogService.record(
        db,
        actor_user_id=current_user.id,
        action=action,
        resource_type="VerificationApplication",
        resource_id=application.id,
        description=description,
        metadata=audit_metadata,
    )


@router.post(
    "",
    response_model=VerificationApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_application(
    data: VerificationApplicationCreate,
    current_user_and_roles=Depends(
        require_permissions(CREATE_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, _ = current_user_and_roles

    if data.applicant_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create your own verification application.",
        )

    if data.government_unit_id is not None:
        unit_result = await db.execute(
            select(GovernmentUnit).where(
                GovernmentUnit.id == data.government_unit_id,
                GovernmentUnit.is_active.is_(True),
            )
        )

        if unit_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Government unit not found or inactive.",
            )

    application = VerificationApplication(
        applicant_user_id=current_user.id,
        government_unit_id=data.government_unit_id,
        application_type=data.application_type,
        submitted_data=data.submitted_data,
        remarks=data.remarks,
        status=VerificationStatus.PENDING.value,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    return application


@router.get(
    "",
    response_model=list[VerificationApplicationResponse],
)
async def list_verification_applications(
    application_status: str | None = Query(
        default=None,
        alias="status",
    ),
    applicant_user_id: UUID | None = None,
    current_user_and_roles=Depends(
        require_permissions(VIEW_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    permissions = get_permissions_for_roles(roles)

    can_review = any(
        permission in permissions
        for permission in (
            REVIEW_VERIFICATION,
            APPROVE_VERIFICATION,
            REJECT_VERIFICATION,
            REQUEST_VERIFICATION_INFO,
        )
    )

    query = select(VerificationApplication)

    if await _is_super_admin(current_user, roles):
        if applicant_user_id is not None:
            query = query.where(
                VerificationApplication.applicant_user_id
                == applicant_user_id
            )

    elif can_review:
        accessible_units = await _get_authorized_unit_ids(
            db,
            current_user.id,
            roles,
        )

        conditions = [
            VerificationApplication.applicant_user_id
            == current_user.id
        ]

        if accessible_units:
            conditions.append(
                VerificationApplication.government_unit_id.in_(
                    accessible_units
                )
            )

        query = query.where(or_(*conditions))

        if applicant_user_id is not None:
            query = query.where(
                VerificationApplication.applicant_user_id
                == applicant_user_id
            )

    else:
        query = query.where(
            VerificationApplication.applicant_user_id
            == current_user.id
        )

    if application_status is not None:
        query = query.where(
            VerificationApplication.status == application_status
        )

    query = query.order_by(
        VerificationApplication.created_at.desc()
    )

    result = await db.execute(query)

    return list(result.scalars().all())


@router.get(
    "/{application_id}",
    response_model=VerificationApplicationResponse,
)
async def get_verification_application(
    application_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(VIEW_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.id == application_id
        )
    )

    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification application not found.",
        )

    await _require_application_jurisdiction(
        db,
        current_user,
        roles,
        application,
    )

    return application


@router.post(
    "/{application_id}/review",
    response_model=VerificationApplicationResponse,
)
async def review_verification_application(
    application_id: UUID,
    data: VerificationApplicationReview,
    current_user_and_roles=Depends(
        require_permissions(REVIEW_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.id == application_id
        )
    )

    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification application not found.",
        )

    if application.applicant_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A user cannot review their own verification application.",
        )

    await _require_application_jurisdiction(
        db,
        current_user,
        roles,
        application,
    )

    requested_status = data.status

    allowed_statuses = {
        VerificationStatus.APPROVED.value,
        VerificationStatus.REJECTED.value,
        VerificationStatus.MORE_INFORMATION_REQUIRED.value,
    }

    if requested_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid review status. Allowed values: "
                "APPROVED, REJECTED, MORE_INFORMATION_REQUIRED."
            ),
        )

    permissions = get_permissions_for_roles(roles)

    required_permission = {
        VerificationStatus.APPROVED.value: APPROVE_VERIFICATION,
        VerificationStatus.REJECTED.value: REJECT_VERIFICATION,
        VerificationStatus.MORE_INFORMATION_REQUIRED.value:
            REQUEST_VERIFICATION_INFO,
    }[requested_status]

    if required_permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"The {required_permission} permission is required "
                "for this verification action."
            ),
        )

    if (
        requested_status == VerificationStatus.REJECTED.value
        and not data.reason
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection reason is required.",
        )

    application.status = requested_status
    application.verifier_user_id = current_user.id

    if requested_status == VerificationStatus.REJECTED.value:
        application.rejection_reason = data.reason

    elif requested_status == VerificationStatus.APPROVED.value:
        application.rejection_reason = None

    application.remarks = data.remarks or application.remarks

    # Synchronize linked Organization and InstitutionProfile
    org_res = await db.execute(
        select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
    )
    for org in org_res.scalars().all():
        org.verification_status = requested_status
        if requested_status == VerificationStatus.APPROVED.value and application.government_unit_id and not org.government_unit_id:
            org.government_unit_id = application.government_unit_id

        inst_res = await db.execute(
            select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
        )
        for inst in inst_res.scalars().all():
            inst.verification_status = requested_status

    # If applicant is government user, link government unit on approval
    applicant_user = await db.get(User, application.applicant_user_id)
    if applicant_user and applicant_user.account_type == "GOVERNMENT":
        if requested_status == VerificationStatus.APPROVED.value and application.government_unit_id:
            applicant_user.government_unit_id = application.government_unit_id

    audit_action = {
        VerificationStatus.APPROVED.value: "APPROVE",
        VerificationStatus.REJECTED.value: "REJECT",
        VerificationStatus.MORE_INFORMATION_REQUIRED.value:
            "REQUEST_INFORMATION",
    }[requested_status]

    audit_description = {
        VerificationStatus.APPROVED.value:
            "Government verification application approved.",
        VerificationStatus.REJECTED.value:
            "Government verification application rejected.",
        VerificationStatus.MORE_INFORMATION_REQUIRED.value:
            "Additional information requested for government verification application.",
    }[requested_status]

    audit_metadata = {}

    if requested_status == VerificationStatus.REJECTED.value:
        audit_metadata["reason"] = data.reason

    if data.remarks:
        audit_metadata["remarks"] = data.remarks

    await _record_verification_audit(
        db,
        current_user=current_user,
        application=application,
        action=audit_action,
        description=audit_description,
        metadata=audit_metadata,
    )

    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority
    from app.core.events import event_manager

    notif_service = NotificationService(db)
    human_status = requested_status.replace("_", " ").title()
    await notif_service.create_notification(
        user_id=application.applicant_user_id,
        notification_type=NotificationType.VERIFICATION_STATUS_UPDATED,
        title=f"Verification Application {human_status}",
        message=data.remarks or f"Your {application.application_type.lower()} verification application has been marked as {human_status}.",
        priority=NotificationPriority.HIGH,
        entity_type="VERIFICATION_APPLICATION",
        entity_id=application.id,
    )

    await event_manager.send_to_user(
        application.applicant_user_id,
        "VERIFICATION_STATUS_UPDATED",
        {
            "application_id": str(application.id),
            "status": requested_status,
            "remarks": data.remarks,
            "reason": data.reason,
            "entity_type": application.application_type,
        },
    )

    await db.commit()
    await db.refresh(application)

    return application


@router.post(
    "/{application_id}/approve",
    response_model=VerificationApplicationResponse,
)
async def approve_verification_application(
    application_id: UUID,
    current_user_and_roles=Depends(
        require_permissions(APPROVE_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.id == application_id
        )
    )

    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification application not found.",
        )

    if application.applicant_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A user cannot approve their own verification application.",
        )

    await _require_application_jurisdiction(
        db,
        current_user,
        roles,
        application,
    )

    application.status = VerificationStatus.APPROVED.value
    application.verifier_user_id = current_user.id
    application.rejection_reason = None

    if application.application_type == "EMPLOYER":
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
        )
        org = org_res.scalars().first()
        if org:
            org.verification_status = OrganizationVerificationStatus.APPROVED.value
    elif application.application_type == "INSTITUTION":
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
        )
        org = org_res.scalars().first()
        if org:
            org.verification_status = OrganizationVerificationStatus.APPROVED.value
            inst_res = await db.execute(
                select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
            )
            inst = inst_res.scalars().first()
            if inst:
                inst.verification_status = InstitutionVerificationStatus.APPROVED.value

    applicant_user = await db.get(User, application.applicant_user_id)
    if applicant_user and applicant_user.account_type == "GOVERNMENT":
        if application.government_unit_id:
            applicant_user.government_unit_id = application.government_unit_id

    await _record_verification_audit(
        db,
        current_user=current_user,
        application=application,
        action="APPROVE",
        description="Government verification application approved.",
    )

    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority
    from app.core.events import event_manager

    notif_service = NotificationService(db)
    await notif_service.create_notification(
        user_id=application.applicant_user_id,
        notification_type=NotificationType.VERIFICATION_STATUS_UPDATED,
        title="Verification Application Approved",
        message=f"Your {application.application_type.lower()} verification application has been approved.",
        priority=NotificationPriority.HIGH,
        entity_type="VERIFICATION_APPLICATION",
        entity_id=application.id,
    )

    await event_manager.send_to_user(
        application.applicant_user_id,
        "VERIFICATION_STATUS_UPDATED",
        {
            "application_id": str(application.id),
            "status": "APPROVED",
            "entity_type": application.application_type,
        },
    )

    await db.commit()
    await db.refresh(application)

    return application


@router.post(
    "/{application_id}/reject",
    response_model=VerificationApplicationResponse,
)
async def reject_verification_application(
    application_id: UUID,
    reason: str | None = Query(default=None),
    current_user_and_roles=Depends(
        require_permissions(REJECT_VERIFICATION)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.id == application_id
        )
    )

    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification application not found.",
        )

    if application.applicant_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A user cannot reject their own verification application.",
        )

    await _require_application_jurisdiction(
        db,
        current_user,
        roles,
        application,
    )

    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection reason is required.",
        )

    application.status = VerificationStatus.REJECTED.value
    application.verifier_user_id = current_user.id
    application.rejection_reason = reason

    if application.application_type == "EMPLOYER":
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
        )
        org = org_res.scalars().first()
        if org:
            org.verification_status = OrganizationVerificationStatus.REJECTED.value
    elif application.application_type == "INSTITUTION":
        org_res = await db.execute(
            select(Organization).where(Organization.owner_user_id == application.applicant_user_id)
        )
        org = org_res.scalars().first()
        if org:
            org.verification_status = OrganizationVerificationStatus.REJECTED.value
            inst_res = await db.execute(
                select(InstitutionProfile).where(InstitutionProfile.organization_id == org.id)
            )
            inst = inst_res.scalars().first()
            if inst:
                inst.verification_status = InstitutionVerificationStatus.REJECTED.value

    await _record_verification_audit(
        db,
        current_user=current_user,
        application=application,
        action="REJECT",
        description="Government verification application rejected.",
        metadata={
            "reason": reason,
        },
    )

    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority
    from app.core.events import event_manager

    notif_service = NotificationService(db)
    await notif_service.create_notification(
        user_id=application.applicant_user_id,
        notification_type=NotificationType.VERIFICATION_STATUS_UPDATED,
        title="Verification Application Rejected",
        message=f"Your {application.application_type.lower()} verification application was rejected: {reason}",
        priority=NotificationPriority.HIGH,
        entity_type="VERIFICATION_APPLICATION",
        entity_id=application.id,
    )

    await event_manager.send_to_user(
        application.applicant_user_id,
        "VERIFICATION_STATUS_UPDATED",
        {
            "application_id": str(application.id),
            "status": "REJECTED",
            "reason": reason,
            "entity_type": application.application_type,
        },
    )

    await db.commit()
    await db.refresh(application)

    return application


@router.post(
    "/{application_id}/request-information",
    response_model=VerificationApplicationResponse,
)
async def request_verification_information(
    application_id: UUID,
    remarks: str = Query(..., min_length=1),
    current_user_and_roles=Depends(
        require_permissions(REQUEST_VERIFICATION_INFO)
    ),
    db: AsyncSession = Depends(get_db),
):
    current_user, roles = current_user_and_roles

    result = await db.execute(
        select(VerificationApplication).where(
            VerificationApplication.id == application_id
        )
    )

    application = result.scalar_one_or_none()

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification application not found.",
        )

    if application.applicant_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "A user cannot request more information "
                "from their own verification application."
            ),
        )

    await _require_application_jurisdiction(
        db,
        current_user,
        roles,
        application,
    )

    application.status = (
        VerificationStatus.MORE_INFORMATION_REQUIRED.value
    )
    application.verifier_user_id = current_user.id
    application.remarks = remarks

    await _record_verification_audit(
        db,
        current_user=current_user,
        application=application,
        action="REQUEST_INFORMATION",
        description=(
            "Additional information requested for government "
            "verification application."
        ),
        metadata={
            "remarks": remarks,
        },
    )

    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority
    from app.core.events import event_manager

    notif_service = NotificationService(db)
    await notif_service.create_notification(
        user_id=application.applicant_user_id,
        notification_type=NotificationType.VERIFICATION_STATUS_UPDATED,
        title="More Information Requested",
        message=f"Additional information requested for your verification application: {remarks}",
        priority=NotificationPriority.HIGH,
        entity_type="VERIFICATION_APPLICATION",
        entity_id=application.id,
    )

    await event_manager.send_to_user(
        application.applicant_user_id,
        "VERIFICATION_STATUS_UPDATED",
        {
            "application_id": str(application.id),
            "status": "MORE_INFORMATION_REQUIRED",
            "remarks": remarks,
            "entity_type": application.application_type,
        },
    )

    await db.commit()
    await db.refresh(application)

    return application