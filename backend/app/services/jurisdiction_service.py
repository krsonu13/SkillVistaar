from __future__ import annotations

from uuid import UUID
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import SUPER_ADMIN, has_role
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


async def get_descendant_unit_ids(
    db: AsyncSession,
    unit_id: UUID,
) -> set[UUID]:
    """
    Return the unit itself and all descendant unit IDs (children, grandchildren, etc.).
    Uses a recursive query across active government units.
    """
    hierarchy = (
        select(GovernmentUnit.id)
        .where(
            GovernmentUnit.id == unit_id,
            GovernmentUnit.is_active.is_(True),
        )
        .cte(
            name=f"unit_descendants_{str(unit_id).replace('-', '_')[:12]}",
            recursive=True,
        )
    )

    descendants = hierarchy.union_all(
        select(GovernmentUnit.id).where(
            GovernmentUnit.parent_id == hierarchy.c.id,
            GovernmentUnit.is_active.is_(True),
        )
    )

    result = await db.execute(select(descendants.c.id))
    return set(result.scalars().all())


async def get_ancestor_unit_ids(
    db: AsyncSession,
    unit_id: UUID,
) -> set[UUID]:
    """
    Return the unit itself and all ancestor unit IDs up to the root.
    """
    hierarchy = (
        select(GovernmentUnit.id, GovernmentUnit.parent_id)
        .where(
            GovernmentUnit.id == unit_id,
            GovernmentUnit.is_active.is_(True),
        )
        .cte(
            name=f"unit_ancestors_{str(unit_id).replace('-', '_')[:12]}",
            recursive=True,
        )
    )

    ancestors = hierarchy.union_all(
        select(GovernmentUnit.id, GovernmentUnit.parent_id).join(
            hierarchy,
            GovernmentUnit.id == hierarchy.c.parent_id,
        )
    )

    result = await db.execute(select(ancestors.c.id))
    return set(result.scalars().all())


async def get_authorized_unit_ids(
    db: AsyncSession,
    user: User,
    roles: list[str],
) -> set[UUID]:
    """
    Return all government units the user is authorized to oversee or verify.

    Rules:
    1. Super Admin -> Every active government unit.
    2. Direct government unit assignment (`user.government_unit_id`) -> Unit and all its descendants.
    3. Active verifier authorizations (`verifier_authorizations`) -> Authorized unit and all its descendants.
    4. Active government data-access authorizations -> Authorized unit and all its descendants.
    5. Approved verification applications belonging to user -> Unit and all its descendants.
    """
    if not user.is_active or user.is_suspended:
        return set()

    if user.account_type == "SUPER_ADMIN" or has_role(roles, SUPER_ADMIN):
        result = await db.execute(
            select(GovernmentUnit.id).where(GovernmentUnit.is_active.is_(True))
        )
        return set(result.scalars().all())

    source_unit_ids: set[UUID] = set()

    # 1. Direct government unit assignment on user profile
    if getattr(user, "government_unit_id", None) is not None:
        source_unit_ids.add(user.government_unit_id)

    # 2. Verifier authorizations
    verifier_result = await db.execute(
        select(VerifierAuthorization.government_unit_id).where(
            VerifierAuthorization.verifier_user_id == user.id,
            VerifierAuthorization.is_active.is_(True),
        )
    )
    for unit_id in verifier_result.scalars().all():
        if unit_id is not None:
            source_unit_ids.add(unit_id)

    # 3. Data access authorizations
    data_result = await db.execute(
        select(GovernmentDataAccessAuthorization.government_unit_id).where(
            GovernmentDataAccessAuthorization.user_id == user.id,
            GovernmentDataAccessAuthorization.status
            == GovernmentDataAccessAuthorizationStatus.ACTIVE.value,
        )
    )
    for unit_id in data_result.scalars().all():
        if unit_id is not None:
            source_unit_ids.add(unit_id)

    # 4. Approved verification applications
    application_result = await db.execute(
        select(VerificationApplication.government_unit_id).where(
            VerificationApplication.applicant_user_id == user.id,
            VerificationApplication.status == VerificationStatus.APPROVED.value,
            VerificationApplication.government_unit_id.is_not(None),
        )
    )
    for unit_id in application_result.scalars().all():
        if unit_id is not None:
            source_unit_ids.add(unit_id)

    if not source_unit_ids:
        return set()

    accessible_ids: set[UUID] = set()
    for source_id in source_unit_ids:
        descendants = await get_descendant_unit_ids(db, source_id)
        accessible_ids.update(descendants)

    return accessible_ids


async def can_user_verify_jurisdiction(
    db: AsyncSession,
    user: User,
    roles: list[str],
    target_unit_id: UUID | None,
) -> bool:
    """
    Check whether a user has authority to verify/manage an entity in target_unit_id.
    """
    if user.account_type == "SUPER_ADMIN" or has_role(roles, SUPER_ADMIN):
        return True

    if target_unit_id is None:
        # If target has no unit specified, check if user is at root (Central Govt)
        if getattr(user, "government_unit_id", None) is not None:
            unit = await db.get(GovernmentUnit, user.government_unit_id)
            if unit and unit.level == 1:
                return True
        return False

    authorized_units = await get_authorized_unit_ids(db, user, roles)
    return target_unit_id in authorized_units


async def enforce_jurisdiction_access(
    db: AsyncSession,
    user: User,
    roles: list[str],
    target_unit_id: UUID | None,
    action_description: str = "verify this entity",
) -> None:
    """
    Enforce that user has jurisdiction authority over target_unit_id.
    Raises HTTP 403 Forbidden if not authorized.
    """
    authorized = await can_user_verify_jurisdiction(db, user, roles, target_unit_id)
    if not authorized:
        target_name = str(target_unit_id) if target_unit_id else "Unassigned Jurisdiction"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Cross-jurisdiction access forbidden: Your government unit is not authorized "
                f"to {action_description} in jurisdiction {target_name}."
            ),
        )


async def resolve_government_unit_for_registration(
    db: AsyncSession,
    state: str | None = None,
    city: str | None = None,
    level: str | int | None = None,
    account_type: str | None = None,
) -> GovernmentUnit | None:
    """
    Intelligently resolves the matching GovernmentUnit for a new registrant or verification application
    based on geographical jurisdiction (state, city) and hierarchy level.
    """
    res = await db.execute(
        select(GovernmentUnit)
        .where(GovernmentUnit.is_active.is_(True))
        .order_by(GovernmentUnit.level.desc())
    )
    all_units = list(res.scalars().all())
    if not all_units:
        return None

    norm_level: int | None = None
    if level is not None:
        level_str = str(level).strip().upper()
        if level_str in ("1", "CENTRAL"):
            norm_level = 1
        elif level_str in ("2", "STATE"):
            norm_level = 2
        elif level_str in ("3", "DISTRICT"):
            norm_level = 3
        elif level_str in ("4", "LOCAL"):
            norm_level = 4

    clean_state = state.strip().lower() if state else ""
    clean_city = city.strip().lower() if city else ""

    if norm_level == 1:
        for u in all_units:
            if u.level == 1:
                return u

    if norm_level == 4:
        for u in all_units:
            if u.level == 4:
                u_text = f"{u.name} {u.jurisdiction or ''}".lower()
                if clean_city and clean_city in u_text:
                    return u
                if clean_state and clean_state in u_text:
                    return u
        for u in all_units:
            if u.level == 4:
                return u

    if norm_level == 3:
        for u in all_units:
            if u.level == 3:
                u_text = f"{u.name} {u.jurisdiction or ''}".lower()
                if clean_city and clean_city in u_text:
                    return u
                if clean_state and clean_state in u_text:
                    return u
        for u in all_units:
            if u.level == 2 and clean_state and clean_state in f"{u.name} {u.jurisdiction or ''}".lower():
                return u

    if norm_level == 2:
        for u in all_units:
            if u.level == 2:
                u_text = f"{u.name} {u.jurisdiction or ''}".lower()
                if clean_state and clean_state in u_text:
                    return u
        for u in all_units:
            if u.level == 1:
                return u

    # For Employers & Training Institutes
    if clean_city:
        for u in all_units:
            if u.level == 3:
                u_text = f"{u.name} {u.jurisdiction or ''}".lower()
                if clean_city in u_text:
                    return u

    if clean_state:
        for u in all_units:
            if u.level == 2:
                u_text = f"{u.name} {u.jurisdiction or ''}".lower()
                if clean_state in u_text:
                    return u

    for u in all_units:
        if u.level == 1:
            return u

    return all_units[0] if all_units else None


async def get_eligible_verifier_user_ids(
    db: AsyncSession,
    target_entity_type: str,
    target_unit_id: UUID | None,
) -> set[UUID]:
    """
    Returns user IDs of all active government verifiers and administrators who have
    jurisdiction and authority to review an application of type target_entity_type in target_unit_id.
    """
    from app.models.role import Role
    from app.models.user_role import UserRole

    eligible_user_ids: set[UUID] = set()

    res = await db.execute(
        select(User).where(
            User.is_active.is_(True),
            User.is_suspended.is_(False),
            User.account_type.in_(["GOVERNMENT", "SUPER_ADMIN"]),
        )
    )
    users = list(res.scalars().all())

    for u in users:
        role_res = await db.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == u.id,
                UserRole.revoked_at.is_(None),
                Role.is_active.is_(True),
            )
        )
        roles = list(role_res.scalars().all())

        allowed, _ = await validate_verification_authority(
            db=db,
            verifier_user=u,
            verifier_roles=roles,
            target_entity_type=target_entity_type,
            target_unit_id=target_unit_id,
        )
        if allowed:
            eligible_user_ids.add(u.id)

    return eligible_user_ids


async def validate_verification_authority(
    db: AsyncSession,
    verifier_user: User,
    verifier_roles: list[str],
    target_entity_type: str,
    target_unit_id: UUID | None,
) -> tuple[bool, str]:
    """
    Strict multi-tier verification authority rule engine:

    1. CENTRAL GOVERNMENT ACCOUNT:
       - Verified ONLY by SUPER ADMIN.
    2. STATE GOVERNMENT ACCOUNT:
       - Verified by Central Government (level 1) or SUPER ADMIN.
    3. DISTRICT GOVERNMENT ACCOUNT:
       - Verified by Respective State Government (level 2), Central Government (level 1), or SUPER ADMIN.
    4. LOCAL GOVERNMENT ACCOUNT:
       - Verified ONLY by Respective District Government (level 3).
       - Even Central Government and Super Admin cannot verify local government.
    5. TRAINING INSTITUTE & EMPLOYER / INDUSTRY (and their documents):
       - Verified by Respective District Government (level 3), Respective State Government (level 2),
         Central Government (level 1), or SUPER ADMIN.
       - Local Government (level 4) CANNOT verify Training Institutes or Employers.
       - Unrelated district or state verifiers CANNOT verify.
    """
    normalized_type = target_entity_type.upper()
    is_admin = verifier_user.account_type == "SUPER_ADMIN" or has_role(verifier_roles, SUPER_ADMIN)

    # Rule 4: Local Government Account
    # Verified ONLY by Respective District Government (even Central and Super Admin cannot bypass this).
    if normalized_type in ("LOCAL_GOVERNMENT", "LOCAL_GOV"):
        verifier_unit_id = getattr(verifier_user, "government_unit_id", None)
        if not verifier_unit_id:
            return False, "Local Government accounts can be verified ONLY by Respective District Government."
        verifier_unit = await db.get(GovernmentUnit, verifier_unit_id)
        if not verifier_unit or not verifier_unit.is_active:
            return False, "Verifier government unit is inactive or invalid."
        if verifier_unit.level == 3 and target_unit_id:
            district_descendants = await get_descendant_unit_ids(db, verifier_unit_id)
            if target_unit_id in district_descendants or target_unit_id == verifier_unit_id:
                return True, "Respective District Government authorized to verify Local Government."
        return False, "Local Government accounts can be verified ONLY by Respective District Government (Super Admin & Central Govt restricted)."

    # Rule 1: Central Government Account
    if normalized_type in ("CENTRAL_GOVERNMENT", "CENTRAL_GOV"):
        if is_admin:
            return True, "Super Admin authorized to verify Central Government account."
        return False, "Central Government accounts can be verified ONLY by Super Admin."

    # Super Admin has universal verification authority for all other types
    if is_admin:
        return True, "Super Admin has universal verification authority."

    # Get verifier's unit
    verifier_unit_id = getattr(verifier_user, "government_unit_id", None)
    if not verifier_unit_id:
        return False, "Verifier account is not associated with any authorized government unit."

    verifier_unit = await db.get(GovernmentUnit, verifier_unit_id)
    if not verifier_unit or not verifier_unit.is_active:
        return False, "Verifier government unit is inactive or invalid."

    verifier_level = verifier_unit.level

    # Rule 2: State Government Account
    if normalized_type in ("STATE_GOVERNMENT", "STATE_GOV"):
        if verifier_level == 1:
            return True, "Central Government authorized to verify State Government account."
        return False, "State Government accounts can be verified only by Central Government or Super Admin."

    # Rule 3: District Government Account
    if normalized_type in ("DISTRICT_GOVERNMENT", "DISTRICT_GOV"):
        if verifier_level == 1:
            return True, "Central Government authorized to verify District Government account."
        if verifier_level == 2:
            if target_unit_id:
                state_descendants = await get_descendant_unit_ids(db, verifier_unit_id)
                if target_unit_id in state_descendants or target_unit_id == verifier_unit_id:
                    return True, "Respective State Government authorized to verify District Government."
            return False, "State Government can only verify districts within its own state jurisdiction."
        return False, "District Government accounts can only be verified by Respective State Gov, Central Gov, or Super Admin."

    # Rule 5: Training Institute, Employer / Industry, and Organization Documents
    # Allowed: Respective District Gov (level 3), Respective State Gov (level 2), Central Gov (level 1).
    # Disallowed: Local Government (level 4).
    if verifier_level >= 4:
        return False, "Local Government units are not authorized to verify Training Institutes, Employers, or organizational documents."

    if verifier_level == 1:
        return True, "Central Government authorized to verify organizations across all national jurisdictions."

    # For State (level 2) or District (level 3): target must be in respective jurisdiction
    if target_unit_id is None:
        return False, "Entity does not have a registered jurisdiction assigned; cannot verify without Central or Super Admin authority."

    authorized_units = await get_authorized_unit_ids(db, verifier_user, verifier_roles)
    if target_unit_id in authorized_units:
        return True, f"Government Unit ({verifier_unit.name}) is authorized over jurisdiction."

    return False, (
        f"Cross-jurisdiction access forbidden: Your government office ({verifier_unit.name}) "
        f"does not have jurisdiction authority over the target entity's registered jurisdiction."
    )


async def enforce_verification_authority(
    db: AsyncSession,
    verifier_user: User,
    verifier_roles: list[str],
    target_entity_type: str,
    target_unit_id: UUID | None,
    action_label: str = "verify",
) -> None:
    """
    Enforces validate_verification_authority, raising HTTP 403 Forbidden on failure.
    """
    allowed, message = await validate_verification_authority(
        db=db,
        verifier_user=verifier_user,
        verifier_roles=verifier_roles,
        target_entity_type=target_entity_type,
        target_unit_id=target_unit_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Verification authority error: Cannot {action_label}. {message}",
        )



async def build_government_hierarchy_tree(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Build and return the full hierarchical tree of government units.
    """
    result = await db.execute(
        select(GovernmentUnit)
        .where(GovernmentUnit.is_active.is_(True))
        .order_by(GovernmentUnit.level, GovernmentUnit.name)
    )
    all_units = list(result.scalars().all())

    units_by_id: dict[UUID, dict[str, Any]] = {}
    for unit in all_units:
        units_by_id[unit.id] = {
            "id": str(unit.id),
            "code": unit.code,
            "name": unit.name,
            "unit_type": unit.unit_type,
            "level": unit.level,
            "status": unit.status,
            "jurisdiction": unit.jurisdiction,
            "parent_id": str(unit.parent_id) if unit.parent_id else None,
            "children": [],
        }

    root_nodes: list[dict[str, Any]] = []
    for unit in all_units:
        node = units_by_id[unit.id]
        if unit.parent_id and unit.parent_id in units_by_id:
            units_by_id[unit.parent_id]["children"].append(node)
        else:
            root_nodes.append(node)

    return root_nodes
