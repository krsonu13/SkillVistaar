import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole


EMAIL = "admin@skillvistaar.com"
PASSWORD = "Admin@12345"


async def create_super_admin():
    async with AsyncSessionLocal() as db:

        # Find existing user
        result = await db.execute(
            select(User).where(User.email == EMAIL)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=EMAIL,
                phone=None,
                password_hash=hash_password(PASSWORD),
                account_type="SUPER_ADMIN",
                is_active=True,
                is_suspended=False,
                email_verified=True,
                phone_verified=False,
                mfa_enabled=False,
                failed_login_attempts=0,
                password_changed_at=datetime.now(timezone.utc),
            )

            db.add(user)
            await db.flush()

            print(f"Created user: {EMAIL}")

        else:
            print(f"User already exists: {EMAIL}")

            # Make sure the existing account can log in as SUPER_ADMIN
            user.account_type = "SUPER_ADMIN"
            user.is_active = True
            user.is_suspended = False
            user.email_verified = True

        # Find SUPER_ADMIN role
        role_result = await db.execute(
            select(Role).where(
                Role.code == "SUPER_ADMIN",
                Role.is_active.is_(True),
            )
        )

        role = role_result.scalar_one_or_none()

        if role is None:
            print("System roles not found. Seeding initial roles...")
            from app.db.seed import seed_roles
            await seed_roles()
            role_result = await db.execute(
                select(Role).where(
                    Role.code == "SUPER_ADMIN",
                    Role.is_active.is_(True),
                )
            )
            role = role_result.scalar_one_or_none()
            if role is None:
                raise RuntimeError("Failed to seed SUPER_ADMIN role.")

        # Check existing role assignment
        assignment_result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )

        assignment = assignment_result.scalar_one_or_none()

        if assignment is None:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )
            print("Assigned SUPER_ADMIN role.")
        elif assignment.revoked_at is not None:
            assignment.revoked_at = None
            print("Restored SUPER_ADMIN role.")

        await db.commit()

        print()
        print("====================================")
        print(" SkillVistaar Super Admin Created")
        print("====================================")
        print(f"Email    : {EMAIL}")
        print(f"Password : {PASSWORD}")
        print("Role     : SUPER_ADMIN")
        print("Verified : YES")
        print("====================================")


if __name__ == "__main__":
    asyncio.run(create_super_admin())
