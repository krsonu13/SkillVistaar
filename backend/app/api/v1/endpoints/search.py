from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.government_unit import GovernmentUnit
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


@router.get("/profiles")
async def search_profiles(
    q: str = Query("", description="Search term for names, ministries, or @usernames"),
    account_type: str | None = Query(None, description="Optional filter: GOVERNMENT, EMPLOYER, TRAINING_INSTITUTE, CANDIDATE"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Search accounts across SkillVistaar by:
    - Name (User full name, Company name, Institute name)
    - Ministry / Government unit name or code
    - Username (@username)

    Strict Security & Verification Rules:
    - Returns ONLY verified entities:
      * Organizations with verification_status == 'APPROVED'
      * Government units with status == 'ACTIVE'
      * Public candidates who have verified email or phone
    - NEVER returns unverified, pending, rejected, suspended, or administrative accounts.
    - NEVER exposes private email or phone identifiers.
    """
    clean_q = q.strip().lstrip("@").lower()
    if not clean_q:
        return {"items": [], "results": [], "total": 0, "query": q}

    limit_val = int(limit) if limit else 20
    offset_val = int(offset) if offset else 0

    results: list[dict[str, Any]] = []
    norm_acc = account_type.strip().upper() if isinstance(account_type, str) and account_type.strip() else None

    # 1. Government Units (Statutory & Active)
    if norm_acc is None or norm_acc == "GOVERNMENT":
        govt_stmt = (
            select(GovernmentUnit, User)
            .join(User, User.government_unit_id == GovernmentUnit.id)
            .where(
                GovernmentUnit.status == "ACTIVE",
                User.is_active.is_(True),
                User.is_suspended.is_(False),
                User.account_type == "GOVERNMENT",
                (
                    GovernmentUnit.name.ilike(f"%{clean_q}%")
                    | GovernmentUnit.code.ilike(f"%{clean_q}%")
                    | User.username.ilike(f"%{clean_q}%")
                ),
            )
            .limit(limit_val)
        )
        res = await db.execute(govt_stmt)
        for unit, user in res.all():
            results.append({
                "id": str(user.id),
                "username": user.username,
                "handle": f"@{user.username}" if user.username else None,
                "name": unit.name,
                "account_type": "GOVERNMENT",
                "headline": f"{unit.unit_type.replace('_', ' ').title() if unit.unit_type else 'Government Authority'} • Level {unit.level}",
                "location": unit.jurisdiction or "India",
                "is_verified": True,
                "badge_label": "Verified Government",
                "unit_code": unit.code,
            })

    # 2. Approved Organizations (Employer & Training Institute)
    target_org_types = []
    if norm_acc is None:
        target_org_types = ["EMPLOYER", "TRAINING_INSTITUTE"]
    elif norm_acc in ("EMPLOYER", "TRAINING_INSTITUTE"):
        target_org_types = [norm_acc]

    if target_org_types:
        org_stmt = (
            select(Organization, User)
            .join(User, User.id == Organization.owner_user_id)
            .where(
                Organization.verification_status == "APPROVED",
                User.is_active.is_(True),
                User.is_suspended.is_(False),
                User.account_type.in_(target_org_types),
                (
                    Organization.display_name.ilike(f"%{clean_q}%")
                    | Organization.legal_name.ilike(f"%{clean_q}%")
                    | User.username.ilike(f"%{clean_q}%")
                ),
            )
            .limit(limit_val)
        )
        res = await db.execute(org_stmt)
        for org, user in res.all():
            badge = "Verified Employer" if user.account_type == "EMPLOYER" else "Accredited Institute"
            results.append({
                "id": str(user.id),
                "username": user.username,
                "handle": f"@{user.username}" if user.username else None,
                "name": org.display_name or org.legal_name,
                "account_type": user.account_type,
                "headline": f"{badge} • {org.sector or 'Registered Organization'}",
                "location": org.address or None,
                "is_verified": True,
                "badge_label": badge,
            })

    # 3. Public Verified Candidates
    if norm_acc is None or norm_acc == "CANDIDATE":
        cand_stmt = (
            select(CandidateProfile, User)
            .join(User, User.id == CandidateProfile.user_id)
            .where(
                CandidateProfile.is_public.is_(True),
                User.is_active.is_(True),
                User.is_suspended.is_(False),
                User.account_type == "CANDIDATE",
                (User.email_verified.is_(True) | User.phone_verified.is_(True)),
                (
                    CandidateProfile.first_name.ilike(f"%{clean_q}%")
                    | CandidateProfile.last_name.ilike(f"%{clean_q}%")
                    | User.username.ilike(f"%{clean_q}%")
                ),
            )
            .limit(limit_val)
        )
        res = await db.execute(cand_stmt)
        for prof, user in res.all():
            full_name = f"{prof.first_name} {prof.last_name or ''}".strip()
            results.append({
                "id": str(user.id),
                "username": user.username,
                "handle": f"@{user.username}" if user.username else None,
                "name": full_name or "Verified Candidate",
                "account_type": "CANDIDATE",
                "headline": prof.headline or prof.current_occupation or "Verified Candidate",
                "location": prof.preferred_location or None,
                "is_verified": True,
                "badge_label": "Verified Candidate",
            })

    # Deduplicate by user ID while preserving order
    seen_ids = set()
    deduped = []
    for item in results:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            deduped.append(item)

    paginated = deduped[offset_val : offset_val + limit_val]

    return {
        "items": paginated,
        "results": paginated,
        "total": len(deduped),
        "limit": limit_val,
        "offset": offset_val,
        "query": q,
    }
