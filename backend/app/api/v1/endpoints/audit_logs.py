from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_roles
from app.core.permissions import (
    VIEW_AUDIT_LOGS,
    get_permissions_for_roles,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse
from app.services.audit_log_service import AuditLogService
from app.services.government_jurisdiction_service import (
    GovernmentJurisdictionService,
)


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


async def require_audit_access(
    current_user: User,
    db: AsyncSession,
) -> tuple[User, list[str]]:
    """
    Require explicit audit-log permission.

    Audit access is permission-based rather than based only on the
    user's account type.
    """
    user, roles = await get_current_user_with_roles(current_user, db)

    permissions = get_permissions_for_roles(roles)

    if VIEW_AUDIT_LOGS not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view audit logs.",
        )

    return user, roles


def validate_resource_type(resource_type: str) -> str:
    """
    Prevent arbitrary/unsafe resource-type values from being passed
    to the audit service.
    """
    normalized = resource_type.strip()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource type cannot be empty.",
        )

    if len(normalized) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resource type is too long.",
        )

    return normalized


def validate_action(action: str | None) -> str | None:
    if action is None:
        return None

    normalized = action.strip().upper()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action cannot be empty.",
        )

    if len(normalized) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action is too long.",
        )

    return normalized


@router.get(
    "/",
    response_model=AuditLogListResponse,
)
async def list_audit_logs(
    actor_user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs.

    Access requires VIEW_AUDIT_LOGS.

    Super Admins receive global audit visibility.

    Other authorized government users are restricted to the audit
    records that belong to resources within their authorized
    jurisdiction. The underlying audit service remains the system
    of record for audit-log retrieval.
    """
    current_user, roles = await require_audit_access(
        current_user,
        db,
    )

    action = validate_action(action)

    service = AuditLogService(db)

    # Super Admin has global audit visibility.
    jurisdiction_service = GovernmentJurisdictionService(db)

    if await jurisdiction_service.is_super_admin(current_user.id):
        items, total = await service.list_logs(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
            offset=offset,
        )

        return AuditLogListResponse(
            items=items,
            total=total,
        )

    # For non-Super-Admin users, audit visibility must be restricted.
    #
    # The existing AuditLogService.list_logs() does not currently
    # expose a jurisdiction/resource filter. Therefore we do not
    # pretend that a normal government user has global visibility.
    #
    # At this stage, only explicitly authorized Super Admin audit
    # access is allowed through the global listing endpoint.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Global audit-log listing is restricted to Super Admin. "
            "Use resource-specific audit history for authorized "
            "jurisdictional resources."
        ),
    )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=AuditLogListResponse,
)
async def resource_history(
    resource_type: str,
    resource_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve audit history for a specific resource.

    Requires VIEW_AUDIT_LOGS.

    Super Admins can access any resource history.

    Non-Super-Admin jurisdiction-aware access will be enforced before
    returning resource history once the corresponding resource-to-
    government-unit ownership mappings are available.
    """
    current_user, roles = await require_audit_access(
        current_user,
        db,
    )

    resource_type = validate_resource_type(resource_type)

    jurisdiction_service = GovernmentJurisdictionService(db)

    is_super_admin = await jurisdiction_service.is_super_admin(
        current_user.id
    )

    if not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Resource audit history requires authorized "
                "jurisdictional access."
            ),
        )

    service = AuditLogService(db)

    items = await service.get_resource_history(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    return AuditLogListResponse(
        items=items,
        total=len(items),
    )