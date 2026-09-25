from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.role import Role


SYSTEM_ROLES = [
    {
        "code": "SUPER_ADMIN",
        "name": "Super Admin",
        "description": "Full platform administration and governance access.",
    },
    {
        "code": "GOVERNMENT_ADMIN",
        "name": "Government Admin",
        "description": "Government administration and jurisdiction-level management.",
    },
    {
        "code": "GOVERNMENT_VERIFIER",
        "name": "Government Verifier",
        "description": "Authorized government verification and review access.",
    },
    {
        "code": "ORG_ADMIN",
        "name": "Organization Admin",
        "description": "Employer organization administration.",
    },
    {
        "code": "HR",
        "name": "HR",
        "description": "Employer HR and recruitment management.",
    },
    {
        "code": "JOB_POSTER",
        "name": "Job Poster",
        "description": "Create and manage employer job postings.",
    },
    {
        "code": "ASSESSMENT_MANAGER",
        "name": "Assessment Manager",
        "description": "Create and manage recruitment assessments.",
    },
    {
        "code": "INSTITUTION_ADMIN",
        "name": "Institution Admin",
        "description": "Training institute administration.",
    },
    {
        "code": "CANDIDATE",
        "name": "Candidate",
        "description": "Candidate profile, skills, credentials and career access.",
    },
]


async def seed_roles() -> None:
    async with AsyncSessionLocal() as db:
        for role_data in SYSTEM_ROLES:
            result = await db.execute(
                select(Role).where(Role.code == role_data["code"])
            )
            role = result.scalar_one_or_none()

            if role is None:
                role = Role(
                    code=role_data["code"],
                    name=role_data["name"],
                    description=role_data["description"],
                    is_system_role=True,
                    is_active=True,
                )
                db.add(role)
                print(f"Created role: {role_data['code']}")
            else:
                print(f"Already exists: {role_data['code']}")

        await db.commit()


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_roles())
