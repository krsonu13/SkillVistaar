import os

os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
settings.TESTING = True
settings.ENVIRONMENT = "test"

from app.db.session import engine
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Shared async HTTP client for FastAPI endpoint tests.

    The SQLAlchemy async engine is disposed after every test so
    asyncpg connections are never reused across pytest event loops.
    This is important with Python 3.14 and pytest-asyncio.
    """
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client:
            yield async_client
    finally:
        await engine.dispose()