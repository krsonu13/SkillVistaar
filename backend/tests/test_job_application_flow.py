from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_job_application_routes_are_registered(client: AsyncClient):
    """
    Basic smoke test to ensure the Job/Application API surface is mounted.
    """

    response = await client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    job_paths = [
        path
        for path in paths
        if "/jobs" in path or "/applications" in path
    ]

    assert job_paths, "No Job/Application routes are registered"


@pytest.mark.asyncio
async def test_job_application_unauthorized_access_is_blocked(
    client: AsyncClient,
):
    """
    Job/Application endpoints must not allow unauthenticated access.
    """

@pytest.mark.asyncio
async def test_job_application_unauthorized_access_is_blocked(
    client: AsyncClient,
):
    """
    Public job discovery is allowed without authentication,
    but application endpoints must require authentication.
    """

    # Public job discovery is intentionally accessible.
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200

    # Candidate applications must not be accessible anonymously.
    response = await client.get("/api/v1/applications")
    assert response.status_code in (401, 403, 404)


@pytest.mark.asyncio
async def test_nonexistent_job_application_resources_are_safe(
    client: AsyncClient,
):
    """
    Invalid UUID resources should never produce an unexpected server error.
    """

    fake_id = uuid4()

    paths = [
        f"/api/v1/jobs/{fake_id}",
        f"/api/v1/applications/{fake_id}",
    ]

    for path in paths:
        response = await client.get(path)

        assert response.status_code in (401, 403, 404)