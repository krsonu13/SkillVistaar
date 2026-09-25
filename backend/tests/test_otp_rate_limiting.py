import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.services.otp_delivery_service import clear_test_outbox, get_last_delivered_otp_for_test

@pytest.mark.asyncio
async def test_smtp_status_endpoint(client: AsyncClient):
    """Verify /api/v1/auth/smtp-status endpoint returns status safely without leaking passwords."""
    resp = await client.get("/api/v1/auth/smtp-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data
    assert "is_gmail" in data
    assert "host" in data
    assert "password" not in data  # Never expose passwords

@pytest.mark.asyncio
async def test_health_reports_email_service(client: AsyncClient):
    """Verify /health includes email_service status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "email_service" in data
    assert "is_gmail" in data["email_service"]

@pytest.mark.asyncio
async def test_resend_cooldown_rate_limit(client: AsyncClient):
    """Verify that rapid OTP requests trigger 429 Too Many Requests in non-test mode."""
    clear_test_outbox()
    email = "ratelimit.test@example.com"
    
    # 1. First request succeeds
    resp1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
    )
    assert resp1.status_code == 200
    
    # 2. Second request immediately after in live runtime mode raises 429
    with patch("app.services.verification_service._is_testing_environment", return_value=False):
        resp2 = await client.post(
            "/api/v1/auth/signup/start-verification",
            json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
        )
        assert resp2.status_code == 429
        assert "Please wait" in resp2.json()["detail"]
        assert "seconds before requesting" in resp2.json()["detail"]
