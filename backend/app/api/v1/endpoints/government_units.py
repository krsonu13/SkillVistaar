from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_with_roles
from app.db.session import get_db
from app.models.government_unit import GovernmentUnit
from app.models.user import User
from app.schemas.government_unit import (
    GovernmentUnitCreate,
    GovernmentUnitNode,
    GovernmentUnitResponse,
    GovernmentUnitUpdate,
)
from app.services.jurisdiction_service import (
    build_government_hierarchy_tree,
    get_descendant_unit_ids,
)

router = APIRouter(
    prefix="/government-units",
    tags=["Government Units"],
)


@router.get("/hierarchy", response_model=list[GovernmentUnitNode])
async def get_hierarchy(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get full recursive hierarchy tree of government units (Central -> State -> District -> Local).
    """
    return await build_government_hierarchy_tree(db)


@router.get("", response_model=list[GovernmentUnitResponse])
async def list_government_units(
    level: int | None = Query(None, description="Filter by administrative level"),
    parent_id: UUID | None = Query(None, description="Filter by parent unit ID"),
    is_active: bool = Query(True, description="Filter active units"),
    db: AsyncSession = Depends(get_db),
) -> list[GovernmentUnit]:
    """
    List government units with optional level and parent filters.
    """
    query = select(GovernmentUnit).where(GovernmentUnit.is_active == is_active)
    if level is not None:
        query = query.where(GovernmentUnit.level == level)
    if parent_id is not None:
        query = query.where(GovernmentUnit.parent_id == parent_id)

    query = query.order_by(GovernmentUnit.level, GovernmentUnit.name)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/by-code/{code}", response_model=GovernmentUnitResponse)
async def get_unit_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> GovernmentUnit:
    """
    Get government unit by unique administrative code.
    """
    result = await db.execute(
        select(GovernmentUnit).where(GovernmentUnit.code == code)
    )
    unit = result.scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government unit with code '{code}' not found.",
        )
    return unit


@router.get("/{unit_id}", response_model=GovernmentUnitResponse)
async def get_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> GovernmentUnit:
    """
    Get government unit by ID.
    """
    unit = await db.get(GovernmentUnit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government unit '{unit_id}' not found.",
        )
    return unit


@router.get("/{unit_id}/descendants", response_model=list[GovernmentUnitResponse])
async def get_descendants(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[GovernmentUnit]:
    """
    Get all descendant government units under a given unit.
    """
    unit = await db.get(GovernmentUnit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government unit '{unit_id}' not found.",
        )

    descendant_ids = await get_descendant_unit_ids(db, unit_id)
    result = await db.execute(
        select(GovernmentUnit)
        .where(GovernmentUnit.id.in_(descendant_ids))
        .order_by(GovernmentUnit.level, GovernmentUnit.name)
    )
    return list(result.scalars().all())


@router.post("", response_model=GovernmentUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_government_unit(
    data: GovernmentUnitCreate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> GovernmentUnit:
    """
    Create a new government unit. Requires SUPER_ADMIN role.
    """
    user, roles = current_user_and_roles
    if user.account_type != "SUPER_ADMIN" and "SUPER_ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create government units.",
        )

    # Check code uniqueness
    existing = await db.execute(
        select(GovernmentUnit).where(GovernmentUnit.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Government unit code '{data.code}' already exists.",
        )

    # Verify parent if specified
    if data.parent_id:
        parent = await db.get(GovernmentUnit, data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent government unit '{data.parent_id}' does not exist.",
            )

    unit = GovernmentUnit(
        code=data.code,
        name=data.name,
        unit_type=data.unit_type,
        level=data.level,
        description=data.description,
        status=data.status,
        jurisdiction=data.jurisdiction,
        parent_id=data.parent_id,
        is_active=True,
    )
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@router.put("/{unit_id}", response_model=GovernmentUnitResponse)
async def update_government_unit(
    unit_id: UUID,
    data: GovernmentUnitUpdate,
    current_user_and_roles: tuple[User, list[str]] = Depends(get_current_user_with_roles),
    db: AsyncSession = Depends(get_db),
) -> GovernmentUnit:
    """
    Update a government unit.
    """
    user, roles = current_user_and_roles
    if user.account_type != "SUPER_ADMIN" and "SUPER_ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update government units.",
        )

    unit = await db.get(GovernmentUnit, unit_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government unit '{unit_id}' not found.",
        )

    if data.name is not None:
        unit.name = data.name
    if data.description is not None:
        unit.description = data.description
    if data.status is not None:
        unit.status = data.status
    if data.jurisdiction is not None:
        unit.jurisdiction = data.jurisdiction
    if data.is_active is not None:
        unit.is_active = data.is_active

    await db.commit()
    await db.refresh(unit)
    return unit
