from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.government_unit import GovernmentUnit


class GovernmentUnitError(Exception):
    pass


class GovernmentUnitNotFoundError(GovernmentUnitError):
    pass


class InvalidGovernmentHierarchyError(GovernmentUnitError):
    pass


async def get_government_unit(
    db: AsyncSession,
    government_unit_id: UUID,
) -> GovernmentUnit:
    unit = await db.get(GovernmentUnit, government_unit_id)

    if unit is None:
        raise GovernmentUnitNotFoundError(
            "Government unit not found."
        )

    return unit


async def create_government_unit(
    db: AsyncSession,
    code: str,
    name: str,
    unit_type: str,
    level: int,
    parent_id: UUID | None = None,
    description: str | None = None,
) -> GovernmentUnit:
    """
    Create a government unit while enforcing basic hierarchy rules.

    Level 0 = root / central
    Level 1 = state-level
    Level 2 = district-level
    Level 3 = local-level

    The service remains generic: unit_type is configurable and is not
    hard-coded to a particular country's administrative terminology.
    """

    if level < 0:
        raise InvalidGovernmentHierarchyError(
            "Government unit level cannot be negative."
        )

    if level == 0 and parent_id is not None:
        raise InvalidGovernmentHierarchyError(
            "A root government unit cannot have a parent."
        )

    if level > 0 and parent_id is None:
        raise InvalidGovernmentHierarchyError(
            "A non-root government unit must have a parent."
        )

    if parent_id is not None:
        parent = await get_government_unit(
            db,
            parent_id,
        )

        if not parent.is_active:
            raise InvalidGovernmentHierarchyError(
                "The parent government unit is inactive."
            )

        if parent.level != level - 1:
            raise InvalidGovernmentHierarchyError(
                "A government unit must have a parent exactly one level above it."
            )

    existing_result = await db.execute(
        select(GovernmentUnit).where(
            GovernmentUnit.code == code
        )
    )

    if existing_result.scalar_one_or_none() is not None:
        raise InvalidGovernmentHierarchyError(
            "A government unit with this code already exists."
        )

    unit = GovernmentUnit(
        code=code,
        name=name,
        unit_type=unit_type,
        level=level,
        parent_id=parent_id,
        description=description,
        is_active=True,
    )

    db.add(unit)
    await db.commit()
    await db.refresh(unit)

    return unit


async def get_children(
    db: AsyncSession,
    government_unit_id: UUID,
    active_only: bool = True,
) -> list[GovernmentUnit]:
    conditions = [
        GovernmentUnit.parent_id == government_unit_id
    ]

    if active_only:
        conditions.append(
            GovernmentUnit.is_active.is_(True)
        )

    result = await db.execute(
        select(GovernmentUnit)
        .where(*conditions)
        .order_by(GovernmentUnit.name.asc())
    )

    return list(result.scalars().all())


async def get_parent(
    db: AsyncSession,
    government_unit_id: UUID,
) -> GovernmentUnit | None:
    unit = await get_government_unit(
        db,
        government_unit_id,
    )

    if unit.parent_id is None:
        return None

    return await db.get(
        GovernmentUnit,
        unit.parent_id,
    )


async def get_ancestors(
    db: AsyncSession,
    government_unit_id: UUID,
) -> list[GovernmentUnit]:
    """
    Return ancestors from immediate parent up to the root.

    Example:

        Local
          ↓
        District
          ↓
        State
          ↓
        Central

    Result:
        [District, State, Central]
    """

    ancestors: list[GovernmentUnit] = []

    current = await get_government_unit(
        db,
        government_unit_id,
    )

    visited: set[UUID] = {current.id}

    while current.parent_id is not None:
        parent = await db.get(
            GovernmentUnit,
            current.parent_id,
        )

        if parent is None:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a missing parent."
            )

        if parent.id in visited:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a cycle."
            )

        visited.add(parent.id)
        ancestors.append(parent)
        current = parent

    return ancestors


async def get_root(
    db: AsyncSession,
    government_unit_id: UUID,
) -> GovernmentUnit:
    unit = await get_government_unit(
        db,
        government_unit_id,
    )

    visited: set[UUID] = {unit.id}

    while unit.parent_id is not None:
        parent = await db.get(
            GovernmentUnit,
            unit.parent_id,
        )

        if parent is None:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a missing parent."
            )

        if parent.id in visited:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a cycle."
            )

        visited.add(parent.id)
        unit = parent

    return unit


async def is_same_or_descendant(
    db: AsyncSession,
    descendant_unit_id: UUID,
    ancestor_unit_id: UUID,
) -> bool:
    """
    Return True when descendant_unit_id is the same unit as,
    or is below, ancestor_unit_id.
    """

    descendant = await get_government_unit(
        db,
        descendant_unit_id,
    )

    ancestor = await get_government_unit(
        db,
        ancestor_unit_id,
    )

    if descendant.id == ancestor.id:
        return True

    visited: set[UUID] = {descendant.id}

    current = descendant

    while current.parent_id is not None:
        if current.parent_id == ancestor.id:
            return True

        if current.parent_id in visited:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a cycle."
            )

        visited.add(current.parent_id)

        parent = await db.get(
            GovernmentUnit,
            current.parent_id,
        )

        if parent is None:
            raise InvalidGovernmentHierarchyError(
                "Government hierarchy contains a missing parent."
            )

        current = parent

    return False


async def can_manage_unit(
    db: AsyncSession,
    manager_unit_id: UUID,
    target_unit_id: UUID,
) -> bool:
    """
    A government administrator/verifier can manage their own
    jurisdiction and descendants.

    Example:

        State → can manage State + its Districts + Local units
        District → can manage District + its Local units
        Local → can manage Local only
    """

    return await is_same_or_descendant(
        db,
        target_unit_id,
        manager_unit_id,
    )