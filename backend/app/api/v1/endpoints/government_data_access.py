from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    MANAGE_GOVERNMENT_DATA_ACCESS,
    VIEW_GOVERNMENT_ANALYTICS,
    get_permissions_for_roles,
    require_permissions,
)
from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.government_data_access import (
    GovernmentDataAccessAuthorizationCreate,
    GovernmentDataAccessAuthorizationResponse,
    GovernmentDataAccessAuthorizationStatusUpdate,
)
from app.services.government_data_access_service import (
    GovernmentDataAccessDeniedError,
    GovernmentDataAccessError,
    GovernmentDataAccessNotFoundError,
    GovernmentDataAccessService,
    GovernmentDataAccessValidationError,
)


router = APIRouter(
    prefix="/government/data-access",
    tags=["Government Data Access"],
)


# ============================================================================
# ERROR HANDLING
# ============================================================================


def _raise_http_error(
    exc: GovernmentDataAccessError,
) -> None:
    """Convert service errors into FastAPI HTTP errors."""

    if isinstance(
        exc,
        GovernmentDataAccessNotFoundError,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        GovernmentDataAccessDeniedError,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        GovernmentDataAccessValidationError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    ) from exc


# ============================================================================
# CREATE AUTHORIZATION
# ============================================================================


@router.post(
    "/",
    response_model=GovernmentDataAccessAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_authorization(
    data: GovernmentDataAccessAuthorizationCreate,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        require_permissions(
            MANAGE_GOVERNMENT_DATA_ACCESS
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Grant government-data access to another government user.

    RBAC verifies that the current user has the management
    permission.

    The service verifies jurisdiction and authorization rules.
    """

    current_user, _roles = current_user_and_roles

    service = GovernmentDataAccessService(db)

    try:
        return await service.create_authorization(
            granted_by_user_id=current_user.id,
            data=data,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# LIST AUTHORIZATIONS
# ============================================================================


@router.get(
    "/",
    response_model=list[
        GovernmentDataAccessAuthorizationResponse
    ],
)
async def list_authorizations(
    user_id: UUID | None = Query(
        default=None,
    ),
    government_unit_id: UUID | None = Query(
        default=None,
    ),
    include_inactive: bool = Query(
        default=False,
    ),
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List government-data access authorizations.

    Government users need either:
    - MANAGE_GOVERNMENT_DATA_ACCESS, or
    - VIEW_GOVERNMENT_ANALYTICS.

    The service enforces jurisdiction boundaries.
    """

    current_user, roles = current_user_and_roles

    permissions = get_permissions_for_roles(roles)

    if (
        MANAGE_GOVERNMENT_DATA_ACCESS not in permissions
        and VIEW_GOVERNMENT_ANALYTICS not in permissions
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to view "
                "government data access authorizations."
            ),
        )

    service = GovernmentDataAccessService(db)

    try:
        return await service.list_authorizations(
            requesting_user_id=current_user.id,
            user_id=user_id,
            government_unit_id=government_unit_id,
            include_inactive=include_inactive,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# GET AUTHORIZATION
# ============================================================================


@router.get(
    "/{authorization_id}",
    response_model=GovernmentDataAccessAuthorizationResponse,
)
async def get_authorization(
    authorization_id: UUID,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        get_current_user_with_roles
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get one government-data access authorization.
    """

    current_user, roles = current_user_and_roles

    permissions = get_permissions_for_roles(roles)

    if (
        MANAGE_GOVERNMENT_DATA_ACCESS not in permissions
        and VIEW_GOVERNMENT_ANALYTICS not in permissions
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to view "
                "government data access authorizations."
            ),
        )

    service = GovernmentDataAccessService(db)

    try:
        return await service.get_authorization(
            authorization_id=authorization_id,
            requesting_user_id=current_user.id,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# UPDATE STATUS
# ============================================================================


@router.patch(
    "/{authorization_id}/status",
    response_model=GovernmentDataAccessAuthorizationResponse,
)
async def update_authorization_status(
    authorization_id: UUID,
    data: GovernmentDataAccessAuthorizationStatusUpdate,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        require_permissions(
            MANAGE_GOVERNMENT_DATA_ACCESS
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update authorization status.

    Allowed lifecycle states are controlled by the service.
    """

    current_user, _roles = current_user_and_roles

    service = GovernmentDataAccessService(db)

    try:
        return await service.update_status(
            authorization_id=authorization_id,
            status_value=data.status,
            requesting_user_id=current_user.id,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# SUSPEND
# ============================================================================


@router.post(
    "/{authorization_id}/suspend",
    response_model=GovernmentDataAccessAuthorizationResponse,
)
async def suspend_authorization(
    authorization_id: UUID,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        require_permissions(
            MANAGE_GOVERNMENT_DATA_ACCESS
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a government-data access authorization."""

    current_user, _roles = current_user_and_roles

    service = GovernmentDataAccessService(db)

    try:
        return await service.suspend_authorization(
            authorization_id=authorization_id,
            requesting_user_id=current_user.id,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# REVOKE
# ============================================================================


@router.post(
    "/{authorization_id}/revoke",
    response_model=GovernmentDataAccessAuthorizationResponse,
)
async def revoke_authorization(
    authorization_id: UUID,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        require_permissions(
            MANAGE_GOVERNMENT_DATA_ACCESS
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a government-data access authorization."""

    current_user, _roles = current_user_and_roles

    service = GovernmentDataAccessService(db)

    try:
        return await service.revoke_authorization(
            authorization_id=authorization_id,
            requesting_user_id=current_user.id,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)


# ============================================================================
# REACTIVATE
# ============================================================================


@router.post(
    "/{authorization_id}/reactivate",
    response_model=GovernmentDataAccessAuthorizationResponse,
)
async def reactivate_authorization(
    authorization_id: UUID,
    current_user_and_roles: tuple[
        User,
        list[str],
    ] = Depends(
        require_permissions(
            MANAGE_GOVERNMENT_DATA_ACCESS
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Reactivate a suspended authorization.

    Expired and revoked authorizations cannot simply be
    reactivated.
    """

    current_user, _roles = current_user_and_roles

    service = GovernmentDataAccessService(db)

    try:
        return await service.reactivate_authorization(
            authorization_id=authorization_id,
            requesting_user_id=current_user.id,
        )

    except GovernmentDataAccessError as exc:
        _raise_http_error(exc)