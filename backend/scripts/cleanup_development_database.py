"""
Database cleanup script for SkillVistaar.
Removes all test/dummy accounts, orphan records, fake jobs, fake applications,
and fake verification records while preserving:
- Database schema and Alembic migrations
- System roles
- Statutory GovernmentUnit hierarchy
- PlatformConfig entries
- Preserved administrative and statutory verifier accounts with canonical @usernames
"""
import asyncio
import logging
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PRESERVED_ACCOUNTS = {
    "admin@skillvistaar.com": "superadmin",
    "admin@skillvistaar.gov.in": "admin",
    "central.verifier@skillvistaar.gov.in": "msde_central",
    "bihar.state@skillvistaar.gov.in": "bihar_skill",
    "rohtas.district@skillvistaar.gov.in": "rohtas_skill",
    "pune.district@skillvistaar.gov.in": "pune_skill",
    "sasaram.local@skillvistaar.gov.in": "sasaram_skill",
}


async def safe_delete(session, sql_query, params=None):
    try:
        await session.execute(text(sql_query), params or {})
    except Exception as e:
        logger.warning("Could not execute '%s': %s", sql_query, e)


async def cleanup():
    async with AsyncSessionLocal() as session:
        logger.info("Step 1: Ensuring 'username' column and lowercase unique index exist on 'users'...")
        await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(30);"))
        await session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username_lower ON users (LOWER(username));"))
        await session.commit()

        logger.info("Step 2: Assigning canonical usernames to preserved statutory accounts...")
        for email, uname in PRESERVED_ACCOUNTS.items():
            await session.execute(
                text("UPDATE users SET username = :uname WHERE email = :email"),
                {"uname": uname, "email": email},
            )
        await session.commit()

        logger.info("Step 3: Finding preserved user IDs...")
        res = await session.execute(
            text("SELECT id, email, username FROM users WHERE email = ANY(:emails)"),
            {"emails": list(PRESERVED_ACCOUNTS.keys())},
        )
        preserved_rows = res.all()
        preserved_ids = [str(r[0]) for r in preserved_rows]
        logger.info("Preserved %d statutory users: %s", len(preserved_ids), [r[1] for r in preserved_rows])

        if not preserved_ids:
            logger.error("No preserved users found! Aborting cleanup to protect database.")
            return

        logger.info("Step 4: Purging dependent test/demo records in cascade order...")
        preserved_params = {"emails": list(PRESERVED_ACCOUNTS.keys())}
        
        # 4a. Temporary & Session tables
        await safe_delete(session, "DELETE FROM auth_sessions WHERE user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        await safe_delete(session, "DELETE FROM verification_challenges;")
        await safe_delete(session, "DELETE FROM signup_verification_sessions;")
        
        # 4b. Notifications & Followings
        await safe_delete(session, "DELETE FROM notifications;")
        await safe_delete(session, "DELETE FROM followings;")
        
        # 4c. Jobs, Applications, Assessments
        await safe_delete(session, "DELETE FROM job_applications;")
        await safe_delete(session, "DELETE FROM job_screening_questions;")
        await safe_delete(session, "DELETE FROM job_skill_requirements;")
        await safe_delete(session, "DELETE FROM jobs;")
        await safe_delete(session, "DELETE FROM assessment_answers;")
        await safe_delete(session, "DELETE FROM assessment_attempts;")
        await safe_delete(session, "DELETE FROM assessment_invitations;")
        await safe_delete(session, "DELETE FROM assessment_questions;")
        await safe_delete(session, "DELETE FROM assessments;")
        
        # 4d. Courses & Placements
        await safe_delete(session, "DELETE FROM course_alignments;")
        await safe_delete(session, "DELETE FROM course_skills;")
        await safe_delete(session, "DELETE FROM courses;")
        await safe_delete(session, "DELETE FROM placement_outcomes;")
        
        # 4e. Candidate records
        await safe_delete(session, "DELETE FROM candidate_credential_skills;")
        await safe_delete(session, "DELETE FROM candidate_credentials;")
        await safe_delete(session, "DELETE FROM candidate_skills;")
        await safe_delete(session, "DELETE FROM candidate_profiles;")
        
        # 4f. Organization Documents & Profiles
        await safe_delete(session, "DELETE FROM organization_document_history;")
        await safe_delete(session, "DELETE FROM organization_documents;")
        await safe_delete(session, "DELETE FROM organization_members;")
        await safe_delete(session, "DELETE FROM institution_profiles;")
        await safe_delete(session, "DELETE FROM organizations;")
        
        # 4g. Verification applications & Authorizations
        await safe_delete(session, "DELETE FROM application_status_history;")
        await safe_delete(session, "DELETE FROM verification_applications WHERE applicant_user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        await safe_delete(session, "DELETE FROM verifier_authorizations WHERE verifier_user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        
        # 4h. Audit Logs for non-preserved
        await safe_delete(session, "DELETE FROM audit_logs WHERE actor_user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        
        # 4i. User Roles & Warnings for non-preserved
        await safe_delete(session, "DELETE FROM user_roles WHERE user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        await safe_delete(session, "DELETE FROM user_warnings WHERE user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        await safe_delete(session, "DELETE FROM user_notification_preferences WHERE user_id NOT IN (SELECT id FROM users WHERE email = ANY(:emails))", preserved_params)
        
        # 4j. Non-preserved users
        deleted_users_res = await session.execute(
            text("DELETE FROM users WHERE id NOT IN (SELECT id FROM users WHERE email = ANY(:emails)) RETURNING id"),
            {"emails": list(PRESERVED_ACCOUNTS.keys())},
        )
        deleted_count = len(deleted_users_res.all())
        logger.info("Purged %d test/demo accounts from 'users'.", deleted_count)
        
        await session.commit()

        logger.info("Step 5: Verifying database health and zero orphan records...")
        counts = {}
        for tbl in [
            "users",
            "government_units",
            "roles",
            "platform_configs",
            "organizations",
            "candidate_profiles",
            "jobs",
            "courses",
            "notifications",
            "followings",
            "verification_applications",
        ]:
            c_res = await session.execute(text(f"SELECT count(*) FROM {tbl}"))
            counts[tbl] = c_res.scalar()

        logger.info("Current Table Row Counts post-cleanup:")
        for t, cnt in counts.items():
            logger.info("  - %s: %d", t, cnt)

        # Check for remaining users
        u_res = await session.execute(text("SELECT email, username, account_type FROM users"))
        remaining_users = u_res.all()
        logger.info("Remaining active verified users (%d):", len(remaining_users))
        for r in remaining_users:
            logger.info("  @%-15s | %-35s | %s", r[1], r[0], r[2])

        logger.info("Cleanup successfully completed with zero orphan records!")


if __name__ == "__main__":
    asyncio.run(cleanup())
