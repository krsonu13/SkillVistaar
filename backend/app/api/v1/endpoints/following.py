from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.following import (
    FollowingCreate,
    FollowingListResponse,
    FollowingResponse,
    FollowingToggleResponse,
    FollowingUpdate,
)
from app.services.following_service import (
    FollowingAccessDeniedError,
    FollowingNotFoundError,
    FollowingService,
    FollowingValidationError,
)

router = APIRouter(
    prefix="/following",
    tags=["Following"],
)


@router.post(
    "/toggle",
    response_model=FollowingToggleResponse,
    status_code=status.HTTP_200_OK,
)
async def toggle_follow(
    payload: FollowingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.toggle_follow(
            user_id=current_user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            target_key=payload.target_key,
            notification_preference=payload.notification_preference,
        )
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except FollowingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=FollowingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow(
    payload: FollowingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.follow(
            user_id=current_user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            target_key=payload.target_key,
            notification_preference=payload.notification_preference,
        )
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except FollowingValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=FollowingListResponse,
)
async def list_following(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        items = await service.get_following(
            user_id=current_user.id,
            include_inactive=include_inactive,
        )

        return FollowingListResponse(
            items=items,
            total=len(items),
        )
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/{following_id}",
    response_model=FollowingResponse,
)
async def get_following(
    following_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.get_one(
            user_id=current_user.id,
            following_id=following_id,
        )
    except FollowingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{following_id}",
    response_model=FollowingResponse,
)
async def update_following(
    following_id: UUID,
    payload: FollowingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        return await service.update_preference(
            user_id=current_user.id,
            following_id=following_id,
            notification_preference=payload.notification_preference,
        )
    except FollowingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{following_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unfollow(
    following_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FollowingService(db)

    try:
        await service.unfollow(
            user_id=current_user.id,
            following_id=following_id,
        )
    except FollowingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except FollowingAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc