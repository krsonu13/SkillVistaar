import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_statutory_accounts_login_and_usernames(client: AsyncClient) -> None:
    """Verify statutory accounts can log in and return their @usernames."""
    statutory_users = [
        ("admin@skillvistaar.gov.in", "admin", "SUPER_ADMIN"),
        ("central.verifier@skillvistaar.gov.in", "msde_central", "GOVERNMENT"),
        ("bihar.state@skillvistaar.gov.in", "bihar_skill", "GOVERNMENT"),
        ("rohtas.district@skillvistaar.gov.in", "rohtas_skill", "GOVERNMENT"),
    ]

    for email, expected_username, expected_type in statutory_users:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": "Password@123"},
        )
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert data["user"]["username"] == expected_username
        assert data["user"]["account_type"] == expected_type


@pytest.mark.asyncio
async def test_username_availability_endpoint(client: AsyncClient) -> None:
    """Check username availability endpoint works as expected."""
    # Taken statutory username
    resp = await client.get("/api/v1/auth/check-username?username=msde_central")
    assert resp.status_code == 200
    assert resp.json()["available"] is False

    # Reserved word
    resp = await client.get("/api/v1/auth/check-username?username=root")
    assert resp.status_code == 200
    assert resp.json()["available"] is False

    # Available username
    resp = await client.get("/api/v1/auth/check-username?username=unique_stakeholder_2026")
    assert resp.status_code == 200
    assert resp.json()["available"] is True


@pytest.mark.asyncio
async def test_global_search_verified_profiles(client: AsyncClient) -> None:
    """Search for verified government units and organizations."""
    resp = await client.get("/api/v1/search/profiles?q=bihar")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert any(item.get("username") == "bihar_skill" for item in data["results"])

    # Search by handle prefix
    resp = await client.get("/api/v1/search/profiles?q=@rohtas")
    assert resp.status_code == 200
    data = resp.json()
    assert any(item.get("username") == "rohtas_skill" for item in data["results"])


@pytest.mark.asyncio
async def test_public_profile_sanitization_and_handle(client: AsyncClient) -> None:
    """Verify public profile returns handle and never exposes email/phone."""
    resp = await client.get("/api/v1/users/public/@msde_central")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "msde_central"
    assert data["handle"] == "@msde_central"
    assert "email" not in data or data.get("email") is None
    assert "phone" not in data or data.get("phone") is None
    assert "followers_count" in data
    assert "following_count" in data


@pytest.mark.asyncio
async def test_following_system_and_self_follow_prevention(client: AsyncClient) -> None:
    """Test follow toggle and self-follow block."""
    # Login as Rohtas
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    rohtas_token = rohtas_login.json()["access_token"]
    rohtas_id = rohtas_login.json()["user"]["id"]

    # Login as Central
    central_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "central.verifier@skillvistaar.gov.in", "password": "Password@123"},
    )
    central_id = central_login.json()["user"]["id"]

    # Attempt self-follow
    self_follow_resp = await client.post(
        "/api/v1/following/toggle",
        headers={"Authorization": f"Bearer {rohtas_token}"},
        json={"target_type": "USER", "target_id": rohtas_id},
    )
    assert self_follow_resp.status_code == 400

    # Toggle follow Central
    follow_resp = await client.post(
        "/api/v1/following/toggle",
        headers={"Authorization": f"Bearer {rohtas_token}"},
        json={"target_type": "USER", "target_id": central_id},
    )
    assert follow_resp.status_code == 200
    assert "is_following" in follow_resp.json()


@pytest.mark.asyncio
async def test_statutory_verification_gating(client: AsyncClient) -> None:
    """Verify that verified government account has dashboard access."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "central.verifier@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    dash_resp = await client.get(
        "/api/v1/government/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert "unit" in data
    assert "statistics" in data
