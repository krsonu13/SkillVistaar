from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.organization_member import (
    OrganizationMemberCreate,
    OrganizationMemberResponse,
    OrganizationMemberRevokeRequest,
)
from app.services.organization_member_service import (
    OrganizationMemberError,
    add_member,
    list_organization_members,
    revoke_member,
)

router = APIRouter(
    prefix="/organizations",
    tags=["Organization Members"],
)


@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_member(
    organization_id: uuid.UUID,
    data: OrganizationMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await add_member(
            db=db,
            organization_id=organization_id,
            target_user_id=data.user_id,
            role_code=data.role_code.value,
            invited_by_user_id=current_user.id,
        )

    except OrganizationMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
)
async def get_organization_members(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_organization_members(
            db=db,
            organization_id=organization_id,
            requesting_user_id=current_user.id,
        )

    except OrganizationMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/{organization_id}/members/{user_id}/revoke",
    response_model=OrganizationMemberResponse,
)
async def revoke_organization_member(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    data: OrganizationMemberRevokeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await revoke_member(
            db=db,
            organization_id=organization_id,
            target_user_id=user_id,
            role_code=data.role_code.value,
            revoked_by_user_id=current_user.id,
        )

    except OrganizationMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc