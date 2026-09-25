import re
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")

RESERVED_USERNAMES = {
    "admin",
    "superadmin",
    "system",
    "skillvistaar",
    "api",
    "support",
    "help",
    "auth",
    "login",
    "signup",
    "government",
    "root",
    "official",
    "verified",
    "null",
    "undefined",
    "mod",
    "moderator",
    "terms",
    "privacy",
    "security",
    "contact",
    "about",
    "status",
    "dashboard",
    "explore",
    "search",
    "notifications",
    "settings",
    "profile",
    "jobs",
    "courses",
    "network",
    "india",
    "msde",
    "ncvet",
    "aicte",
    "dgt",
}


def normalize_username(username: str) -> str:
    if not username:
        return ""
    clean = username.strip().lstrip("@").lower()
    return clean


def validate_username_format(username: str) -> tuple[bool, str]:
    clean = normalize_username(username)
    if not clean:
        return False, "Username cannot be empty."
    
    if len(clean) < 3:
        return False, "Username must be at least 3 characters."
    if len(clean) > 30:
        return False, "Username must be at most 30 characters."
    
    if not USERNAME_REGEX.match(clean):
        return False, "Username can only contain letters, numbers, underscores (_), and periods (.)."
    
    if clean.startswith(".") or clean.endswith("."):
        return False, "Username cannot start or end with a period."
    if clean.startswith("_") or clean.endswith("_"):
        return False, "Username cannot start or end with an underscore."
    if ".." in clean or "__" in clean:
        return False, "Username cannot contain consecutive periods or underscores."
    
    if clean in RESERVED_USERNAMES:
        return False, f"The username '@{clean}' is reserved and cannot be registered."
    
    return True, clean


async def is_username_available(
    db: AsyncSession,
    username: str,
    exclude_user_id: UUID | None = None,
) -> tuple[bool, str]:
    is_valid, msg = validate_username_format(username)
    if not is_valid:
        return False, msg
    
    clean = msg  # returned clean username
    stmt = select(User.id).where(func.lower(User.username) == clean)
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return False, f"The username '@{clean}' is already taken."
    
    return True, f"Username '@{clean}' is available."


async def generate_available_username(
    db: AsyncSession,
    seed: str,
) -> str:
    """Generate an available username derived from a seed (name or email prefix)."""
    # Clean seed to allowed characters
    clean = re.sub(r"[^a-zA-Z0-9_]", "", seed.lower())
    if len(clean) < 3:
        clean = f"user_{clean}"
    clean = clean[:20]
    
    candidate = clean
    counter = 1
    while True:
        available, _ = await is_username_available(db, candidate)
        if available:
            return candidate
        candidate = f"{clean}_{counter}"
        counter += 1
