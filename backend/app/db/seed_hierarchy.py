from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.candidate_credential import CandidateCredential, CredentialStatus, CredentialType
from app.models.candidate_profile import CandidateProfile, CandidateProfileStatus
from app.models.candidate_skill import CandidateSkill, CandidateSkillProficiency, CandidateSkillStatus
from app.models.government_unit import GovernmentUnit
from app.models.institution_profile import InstitutionProfile, InstitutionVerificationStatus
from app.models.organization import (
    Organization,
    OrganizationType,
    OrganizationVerificationStatus,
)
from app.models.role import Role
from app.models.skill import Skill
from app.models.user import User
from app.models.user_role import UserRole
from app.models.verification_application import (
    VerificationApplication,
    VerificationStatus,
)
from app.models.verifier_authorization import VerifierAuthorization


GOVERNMENT_UNITS_DATA = [
    {
        "code": "CEN-IN-01",
        "name": "Ministry of Skill Development & Entrepreneurship",
        "unit_type": "CENTRAL_GOVERNMENT",
        "level": 1,
        "description": "National apex body for skill development initiatives across India.",
        "jurisdiction": "India (National)",
        "parent_code": None,
    },
    {
        "code": "STE-BR-01",
        "name": "Bihar Skill Development Mission",
        "unit_type": "STATE_GOVERNMENT",
        "level": 2,
        "description": "State nodal agency for skilling in Bihar.",
        "jurisdiction": "Bihar",
        "parent_code": "CEN-IN-01",
    },
    {
        "code": "STE-MH-01",
        "name": "Maharashtra State Skill Development Society",
        "unit_type": "STATE_GOVERNMENT",
        "level": 2,
        "description": "State nodal agency for skilling in Maharashtra.",
        "jurisdiction": "Maharashtra",
        "parent_code": "CEN-IN-01",
    },
    {
        "code": "DST-BR-ROH",
        "name": "Rohtas District Skill Office",
        "unit_type": "DISTRICT_GOVERNMENT",
        "level": 3,
        "description": "District skill administration for Rohtas District, Bihar.",
        "jurisdiction": "Rohtas, Bihar",
        "parent_code": "STE-BR-01",
    },
    {
        "code": "DST-BR-PAT",
        "name": "Patna District Skill Administration",
        "unit_type": "DISTRICT_GOVERNMENT",
        "level": 3,
        "description": "District skill administration for Patna District, Bihar.",
        "jurisdiction": "Patna, Bihar",
        "parent_code": "STE-BR-01",
    },
    {
        "code": "DST-MH-PUN",
        "name": "Pune District Skill Mission",
        "unit_type": "DISTRICT_GOVERNMENT",
        "level": 3,
        "description": "District skill administration for Pune District, Maharashtra.",
        "jurisdiction": "Pune, Maharashtra",
        "parent_code": "STE-MH-01",
    },
    {
        "code": "LOC-BR-SAS",
        "name": "Sasaram Local Skill Cell",
        "unit_type": "LOCAL_GOVERNMENT",
        "level": 4,
        "description": "Sub-divisional skill development center in Sasaram, Rohtas.",
        "jurisdiction": "Sasaram, Rohtas, Bihar",
        "parent_code": "DST-BR-ROH",
    },
]


async def seed_government_hierarchy() -> None:
    async with AsyncSessionLocal() as db:
        print("--- Seeding Government Hierarchy Units ---")
        units_cache: dict[str, GovernmentUnit] = {}

        # First load existing units
        existing_res = await db.execute(select(GovernmentUnit))
        for u in existing_res.scalars().all():
            units_cache[u.code] = u

        # Insert units level by level
        for data in GOVERNMENT_UNITS_DATA:
            unit = units_cache.get(data["code"])
            parent_id = None
            if data["parent_code"] and data["parent_code"] in units_cache:
                parent_id = units_cache[data["parent_code"]].id

            if unit is None:
                unit = GovernmentUnit(
                    code=data["code"],
                    name=data["name"],
                    unit_type=data["unit_type"],
                    level=data["level"],
                    description=data["description"],
                    status="ACTIVE",
                    jurisdiction=data["jurisdiction"],
                    parent_id=parent_id,
                    is_active=True,
                )
                db.add(unit)
                await db.flush()
                units_cache[unit.code] = unit
                print(f"Created government unit: {unit.name} ({unit.code})")
            else:
                unit.status = "ACTIVE"
                unit.jurisdiction = data["jurisdiction"]
                unit.parent_id = parent_id
                print(f"Updated government unit: {unit.name} ({unit.code})")

        await db.commit()

        # Load roles
        roles_cache: dict[str, Role] = {}
        roles_res = await db.execute(select(Role))
        for r in roles_res.scalars().all():
            roles_cache[r.code] = r

        default_pw_hash = hash_password("Password@123")
        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # Helper to create/update seeded user
        # -------------------------------------------------------------
        async def create_or_update_user(
            email: str,
            account_type: str,
            role_codes: list[str],
            government_unit_code: str | None = None,
            phone: str | None = None,
            username: str | None = None,
        ) -> User:
            res = await db.execute(select(User).where(User.email == email))
            user = res.scalar_one_or_none()

            govt_unit_id = (
                units_cache[government_unit_code].id
                if government_unit_code and government_unit_code in units_cache
                else None
            )

            if user is None:
                user = User(
                    email=email,
                    phone=phone,
                    username=username,
                    password_hash=default_pw_hash,
                    account_type=account_type,
                    government_unit_id=govt_unit_id,
                    is_active=True,
                    is_suspended=False,
                    email_verified=True,
                    phone_verified=True,
                    password_changed_at=now,
                )
                db.add(user)
                await db.flush()
                print(f"Created user: {email} [{account_type}]")
            else:
                user.account_type = account_type
                user.government_unit_id = govt_unit_id
                user.is_active = True
                user.is_suspended = False
                user.email_verified = True
                user.password_hash = default_pw_hash
                if username:
                    user.username = username
                print(f"Updated user: {email} [{account_type}]")

            # Assign roles
            for role_code in role_codes:
                if role_code in roles_cache:
                    role_id = roles_cache[role_code].id
                    ur_res = await db.execute(
                        select(UserRole).where(
                            UserRole.user_id == user.id,
                            UserRole.role_id == role_id,
                        )
                    )
                    ur = ur_res.scalar_one_or_none()
                    if ur is None:
                        db.add(UserRole(user_id=user.id, role_id=role_id))
                    elif ur.revoked_at is not None:
                        ur.revoked_at = None

            return user

        print("\n--- Seeding Stakeholder Accounts ---")
        # 1. Super Admin
        admin_user = await create_or_update_user(
            email="admin@skillvistaar.gov.in",
            account_type="SUPER_ADMIN",
            role_codes=["SUPER_ADMIN"],
            phone="+911100000001",
            username="admin",
        )

        # 2. Central Government Verifier
        central_govt_user = await create_or_update_user(
            email="central.verifier@skillvistaar.gov.in",
            account_type="GOVERNMENT",
            role_codes=["GOVERNMENT_ADMIN", "GOVERNMENT_VERIFIER"],
            government_unit_code="CEN-IN-01",
            phone="+911100000002",
            username="msde_central",
        )

        # 3. Bihar State Government Verifier
        bihar_state_user = await create_or_update_user(
            email="bihar.state@skillvistaar.gov.in",
            account_type="GOVERNMENT",
            role_codes=["GOVERNMENT_VERIFIER"],
            government_unit_code="STE-BR-01",
            phone="+911100000003",
            username="bihar_skill",
        )

        # 4. Rohtas District Government Verifier
        rohtas_district_user = await create_or_update_user(
            email="rohtas.district@skillvistaar.gov.in",
            account_type="GOVERNMENT",
            role_codes=["GOVERNMENT_VERIFIER"],
            government_unit_code="DST-BR-ROH",
            phone="+911100000004",
            username="rohtas_skill",
        )

        # 5. Pune District Government Verifier (Unrelated jurisdiction)
        pune_district_user = await create_or_update_user(
            email="pune.district@skillvistaar.gov.in",
            account_type="GOVERNMENT",
            role_codes=["GOVERNMENT_VERIFIER"],
            government_unit_code="DST-MH-PUN",
            phone="+911100000005",
            username="pune_skill",
        )

        # 6. Sasaram Local Government Verifier
        sasaram_local_user = await create_or_update_user(
            email="sasaram.local@skillvistaar.gov.in",
            account_type="GOVERNMENT",
            role_codes=["GOVERNMENT_VERIFIER"],
            government_unit_code="LOC-BR-SAS",
            phone="+911100000006",
            username="sasaram_skill",
        )

        # 7. Employer: Recruiter at Tata Motors
        recruiter_user = await create_or_update_user(
            email="recruiter@tatamotors.com",
            account_type="EMPLOYER",
            role_codes=["ORG_ADMIN", "HR"],
            phone="+911100000007",
            username="tatamotors_recruiter",
        )
        pune_unit = units_cache.get("DST-MH-PUN")
        org_emp_res = await db.execute(select(Organization).where(Organization.owner_user_id == recruiter_user.id))
        org_emp = org_emp_res.scalar_one_or_none()
        if org_emp is None:
            org_emp = Organization(
                owner_user_id=recruiter_user.id,
                legal_name="Tata Motors Commercial Vehicles Ltd",
                display_name="Tata Motors",
                organization_type="EMPLOYER",
                government_unit_id=pune_unit.id if pune_unit else None,
                verification_status="APPROVED",
                address="Pune, Maharashtra",
                is_active=True,
            )
            db.add(org_emp)
            await db.flush()

        # 8. Training Institute: Principal at Rohtas Polytechnic
        principal_user = await create_or_update_user(
            email="principal@rohtaspolytechnic.edu.in",
            account_type="TRAINING_INSTITUTE",
            role_codes=["INSTITUTION_ADMIN"],
            phone="+911100000008",
            username="rohtas_polytechnic",
        )
        rohtas_unit = units_cache.get("DST-BR-ROH")
        org_inst_res = await db.execute(select(Organization).where(Organization.owner_user_id == principal_user.id))
        org_inst = org_inst_res.scalar_one_or_none()
        if org_inst is None:
            org_inst = Organization(
                owner_user_id=principal_user.id,
                legal_name="Rohtas Government Polytechnic",
                display_name="Rohtas Polytechnic",
                organization_type="TRAINING_INSTITUTE",
                government_unit_id=rohtas_unit.id if rohtas_unit else None,
                verification_status="PENDING",
                address="Sasaram, Rohtas, Bihar",
                is_active=True,
            )
            db.add(org_inst)
            await db.flush()

        inst_prof_res = await db.execute(select(InstitutionProfile).where(InstitutionProfile.organization_id == org_inst.id))
        inst_prof = inst_prof_res.scalar_one_or_none()
        if inst_prof is None:
            inst_prof = InstitutionProfile(
                organization_id=org_inst.id,
                verification_status="PENDING",
            )
            db.add(inst_prof)
            await db.flush()

        # 9. Candidate: Rajesh Kumar
        candidate_user = await create_or_update_user(
            email="candidate.rajesh@skillvistaar.in",
            account_type="CANDIDATE",
            role_codes=["CANDIDATE"],
            phone="+911100000009",
            username="rajesh_kumar",
        )
        cand_prof_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == candidate_user.id))
        cand_prof = cand_prof_res.scalar_one_or_none()
        if cand_prof is None:
            cand_prof = CandidateProfile(
                user_id=candidate_user.id,
                first_name="Rajesh",
                last_name="Kumar",
                status="ACTIVE",
                is_public=True,
            )
            db.add(cand_prof)
            await db.flush()

        # Ensure candidate has a verified skill
        skill_res = await db.execute(select(Skill).where(Skill.name == "Automotive Mechanics"))
        skill = skill_res.scalar_one_or_none()
        if skill is None:
            skill = Skill(
                name="Automotive Mechanics",
                normalized_name="automotive mechanics",
                skill_type="TECHNICAL",
                category="Automotive",
                status="ACTIVE",
                is_active=True,
            )
            db.add(skill)
            await db.flush()

        cand_skill_res = await db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_profile_id == cand_prof.id,
                CandidateSkill.skill_id == skill.id,
            )
        )
        cand_skill = cand_skill_res.scalar_one_or_none()
        if cand_skill is None:
            cand_skill = CandidateSkill(
                candidate_profile_id=cand_prof.id,
                skill_id=skill.id,
                proficiency_level="INTERMEDIATE",
                status="VERIFIED",
            )
            db.add(cand_skill)
            await db.flush()

        await db.commit()
        print("\n=== SkillVistaar Database Seed Complete (Administrative & Test Accounts) ===")


if __name__ == "__main__":
    asyncio.run(seed_government_hierarchy())
