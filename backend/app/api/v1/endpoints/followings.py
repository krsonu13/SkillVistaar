from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.following import (
    FollowingCreate,
    FollowingListResponse,
    FollowingPreferenceUpdate,
    FollowingResponse,
)
from app.services.following_service import (
    FollowingNotFoundError,
    FollowingService,
    FollowingServiceError,
)

router = APIRouter(
    prefix="/followings",
    tags=["Followings"],
)


@router.post(
    "",
    response_model=FollowingResponse,
)
async def follow(
    data: FollowingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.follow(
            user_id=user.id,
            target_type=data.target_type,
            target_id=data.target_id,
            target_key=data.target_key,
            notification_preference=(
                data.notification_preference
            ),
        )
    except FollowingServiceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=FollowingListResponse,
)
async def list_followings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    items = await service.list_for_user(user.id)

    return {
        "items": items,
        "total": len(items),
    }


@router.patch(
    "/{following_id}/preference",
    response_model=FollowingResponse,
)
async def update_preference(
    following_id: UUID,
    data: FollowingPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.update_preference(
            user_id=user.id,
            following_id=following_id,
            preference=data.notification_preference,
        )
    except FollowingServiceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{following_id}",
    response_model=FollowingResponse,
)
async def unfollow(
    following_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.unfollow(
            user.id,
            following_id,
        )
    except FollowingNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc