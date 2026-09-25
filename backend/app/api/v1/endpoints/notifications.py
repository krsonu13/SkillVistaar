from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferenceListResponse,
    NotificationPreferenceResponse,
    NotificationResponse,
)
from app.services.notification_service import (
    NotificationAccessDeniedError,
    NotificationNotFoundError,
    NotificationService,
    NotificationServiceError,
    NotificationValidationError,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


def handle_service_error(
    exc: NotificationServiceError,
) -> HTTPException:
    if isinstance(
        exc,
        NotificationNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        NotificationAccessDeniedError,
    ):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(
        exc,
        NotificationValidationError,
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


# ------------------------------------------------------------------
# LIST NOTIFICATIONS
# ------------------------------------------------------------------


@router.get(
    "",
    response_model=NotificationListResponse,
)
async def list_notifications(
    unread_only: bool = Query(
        default=False,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)

    try:
        items, total, unread_count = (
            await service.get_notifications(
                user=current_user,
                limit=limit,
                offset=offset,
                unread_only=unread_only,
            )
        )

        return NotificationListResponse(
            items=[
                NotificationResponse.model_validate(
                    item
                )
                for item in items
            ],
            total=total,
            unread_count=unread_count,
        )

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc


# ------------------------------------------------------------------
# UNREAD COUNT
# ------------------------------------------------------------------


@router.get(
    "/unread-count",
)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)

    try:
        _, _, unread = await service.get_notifications(
            user=current_user,
            limit=1,
            offset=0,
        )

        return {
            "count": unread,
            "unread_count": unread,
        }

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc


# ------------------------------------------------------------------
# MARK ALL READ
# ------------------------------------------------------------------


@router.post(
    "/read-all",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)

    try:
        count = await service.mark_all_as_read(
            user=current_user,
        )

        return {
            "message": "Notifications marked as read.",
            "updated_count": count,
        }

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc


# ------------------------------------------------------------------
# PREFERENCES
# ------------------------------------------------------------------


@router.get(
    "/preferences",
    response_model=NotificationPreferenceListResponse,
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)

    try:
        preferences = await service.get_preferences(
            user=current_user,
        )

        return NotificationPreferenceListResponse(
            items=[
                NotificationPreferenceResponse.model_validate(
                    preference
                )
                for preference in preferences
            ]
        )

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc


@router.put(
    "/preferences/{notification_type}",
    response_model=NotificationPreferenceResponse,
)
async def update_notification_preference(
    notification_type: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.notification import (
        NotificationPreferenceUpdate,
    )

    service = NotificationService(db)

    try:
        data = NotificationPreferenceUpdate.model_validate(
            payload
        )

        preference = await service.update_preference(
            user=current_user,
            notification_type=notification_type,
            data=data,
        )

        return NotificationPreferenceResponse.model_validate(
            preference
        )

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc


# ------------------------------------------------------------------
# SINGLE NOTIFICATION
# ------------------------------------------------------------------


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)

    try:
        notification = await service.mark_as_read(
            user=current_user,
            notification_id=notification_id,
        )

        return NotificationResponse.model_validate(
            notification
        )

    except NotificationServiceError as exc:
        raise handle_service_error(exc) from exc
