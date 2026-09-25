from sqlalchemy import text

from app.db.session import engine


async def check_database_connection() -> bool:
    """
    Check whether SkillVistaar can connect to PostgreSQL.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return False