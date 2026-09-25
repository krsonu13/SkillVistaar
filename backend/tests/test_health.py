import pytest


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["project"] == "SkillVistaar"
    assert data["message"] == "Welcome to SkillVistaar API"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")

    assert response.status_code in {200, 503}

    data = response.json()

    assert data["project"] == "SkillVistaar"
    assert data["status"] in {
        "healthy",
        "degraded",
    }

    assert data["database"] in {
        "connected",
        "disconnected",
    }


@pytest.mark.asyncio
async def test_liveness(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["project"] == "SkillVistaar"


@pytest.mark.asyncio
async def test_readiness(client):
    response = await client.get("/health/ready")
    assert response.status_code in {200, 503}
    data = response.json()
    assert data["status"] in {"ready", "unready"}