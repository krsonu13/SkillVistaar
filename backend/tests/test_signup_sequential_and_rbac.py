from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.services.otp_delivery_service import get_last_delivered_otp_for_test


def unique_email() -> str:
    return f"seq_{uuid4().hex[:10]}@example.com"


def unique_phone() -> str:
    return f"9{uuid4().int % 1000000009:09d}"


@pytest.mark.asyncio
async def test_sequential_signup_candidate_mobile_first_success(client: AsyncClient):
    """
    Full positive flow:
    Choose Account Type -> Enter Mobile -> Real OTP -> Verify Mobile
    -> Enter Email -> Real OTP -> Verify Email
    -> Enter Details & Accept Terms -> Create Account
    -> Verify User is active and can login with both credentials.
    """
    phone = unique_phone()
    email = unique_email()
    password = "SecurePassword@123"

    # Step 1: Start verification with Mobile
    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={
            "account_type": "CANDIDATE",
            "channel": "PHONE",
            "identifier": phone,
        },
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["channel"] == "PHONE"
    assert d1["identifier"] == phone
    session_token = d1["session_token"]
    assert session_token

    # Step 2: Verify primary phone OTP
    otp1 = get_last_delivered_otp_for_test(phone)
    assert otp1, "Real OTP was not generated for primary mobile"

    r2 = await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": session_token, "otp": otp1},
    )
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["primary_verified"] is True
    assert d2["next_channel"] == "EMAIL"

    # Step 3: Enter secondary contact (Email) & send OTP
    r3 = await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={
            "session_token": session_token,
            "channel": "EMAIL",
            "identifier": email,
        },
    )
    assert r3.status_code == 200, r3.text
    d3 = r3.json()
    assert d3["channel"] == "EMAIL"
    assert d3["identifier"] == email

    # Step 4: Verify secondary email OTP
    otp2 = get_last_delivered_otp_for_test(email)
    assert otp2, "Real OTP was not generated for secondary email"

    r4 = await client.post(
        "/api/v1/auth/signup/verify-secondary",
        json={"session_token": session_token, "otp": otp2},
    )
    assert r4.status_code == 200, r4.text
    d4 = r4.json()
    assert d4["both_verified"] is True

    # Step 5: Complete signup with details and terms
    r5 = await client.post(
        "/api/v1/auth/signup/complete",
        json={
            "session_token": session_token,
            "password": password,
            "terms_accepted": True,
            "additional_data": {"fullName": "Alok Verma"},
        },
    )
    assert r5.status_code == 200, r5.text
    d5 = r5.json()
    assert d5["success"] is True
    assert d5["user"]["email"] == email
    assert d5["user"]["phone"] == phone
    assert d5["user"]["account_type"] == "CANDIDATE"
    assert d5["user"]["isVerified"] is True
    assert d5.get("token") or d5.get("access_token")

    # Step 6: Verify login works with both email and phone
    login_email = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
    )
    assert login_email.status_code == 200, login_email.text

    login_phone = await client.post(
        "/api/v1/auth/login",
        json={"identifier": phone, "password": password},
    )
    assert login_phone.status_code == 200, login_phone.text


@pytest.mark.asyncio
async def test_sequential_signup_employer_email_first_success(client: AsyncClient):
    """
    Full positive flow for Employer starting with Email, then Phone.
    """
    email = unique_email()
    phone = unique_phone()
    password = "StrongPassword@123"

    # Step 1: Start with Email
    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={
            "account_type": "EMPLOYER",
            "channel": "EMAIL",
            "identifier": email,
        },
    )
    assert r1.status_code == 200, r1.text
    session_token = r1.json()["session_token"]

    # Step 2: Verify primary email OTP
    otp1 = get_last_delivered_otp_for_test(email)
    assert otp1
    r2 = await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": session_token, "otp": otp1},
    )
    assert r2.status_code == 200

    # Step 3: Send secondary phone OTP
    r3 = await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={
            "session_token": session_token,
            "channel": "PHONE",
            "identifier": phone,
        },
    )
    assert r3.status_code == 200

    # Step 4: Verify secondary phone OTP
    otp2 = get_last_delivered_otp_for_test(phone)
    assert otp2
    r4 = await client.post(
        "/api/v1/auth/signup/verify-secondary",
        json={"session_token": session_token, "otp": otp2},
    )
    assert r4.status_code == 200

    # Step 5: Complete signup for Employer
    r5 = await client.post(
        "/api/v1/auth/signup/complete",
        json={
            "session_token": session_token,
            "password": password,
            "terms_accepted": True,
            "additional_data": {"companyName": "TechSolutions Pvt Ltd"},
        },
    )
    assert r5.status_code == 200, r5.text
    d5 = r5.json()
    assert d5["user"]["account_type"] == "EMPLOYER"
    emp_token = d5["token"]

    # Step 6: Employer dashboard is initially gated (403 VERIFICATION_REQUIRED)
    r_dash = await client.get(
        "/api/v1/organizations/me/dashboard",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_dash.status_code == 403, r_dash.text
    assert r_dash.json()["detail"]["code"] == "VERIFICATION_REQUIRED"
    assert r_dash.json()["detail"]["verification_status"] == "PENDING"

    # Step 7: Check statutory verification status
    r_vstatus = await client.get(
        "/api/v1/users/me/verification-status",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_vstatus.status_code == 200, r_vstatus.text
    v_data = r_vstatus.json()
    assert v_data["verification_status"] == "PENDING"
    assert v_data["application_id"] is not None

    # Step 8: Platform Admin approves the statutory verification
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_token = admin_login.json()["access_token"]

    app_id = v_data["application_id"]
    approve_resp = await client.post(
        f"/api/v1/admin/verifications/{app_id}/action",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "action": "APPROVE",
            "remarks": "Approved during automated test verification",
        },
    )
    assert approve_resp.status_code == 200, approve_resp.text

    # Step 9: Employer can access Employer dashboard now that status is APPROVED
    r_dash_approved = await client.get(
        "/api/v1/organizations/me/dashboard",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_dash_approved.status_code == 200, r_dash_approved.text
    dash_data = r_dash_approved.json()
    assert dash_data["success"] is True
    assert dash_data["organization"]["name"] == "TechSolutions Pvt Ltd"


@pytest.mark.asyncio
async def test_sequential_signup_reject_terms_not_accepted(client: AsyncClient):
    """
    Account completion must be blocked with 400 if terms_accepted is False.
    """
    email = unique_email()
    phone = unique_phone()

    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
    )
    st = r1.json()["session_token"]
    otp1 = get_last_delivered_otp_for_test(email)
    await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": st, "otp": otp1},
    )

    await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={"session_token": st, "channel": "PHONE", "identifier": phone},
    )
    otp2 = get_last_delivered_otp_for_test(phone)
    await client.post(
        "/api/v1/auth/signup/verify-secondary",
        json={"session_token": st, "otp": otp2},
    )

    # Attempt complete with terms_accepted=False
    r_fail = await client.post(
        "/api/v1/auth/signup/complete",
        json={
            "session_token": st,
            "password": "Password@123",
            "terms_accepted": False,
        },
    )
    assert r_fail.status_code == 400
    assert "terms of service and privacy policy must be accepted" in r_fail.text.lower()


@pytest.mark.asyncio
async def test_sequential_signup_reject_incomplete_secondary_verification(client: AsyncClient):
    """
    Account completion must be rejected if secondary contact was never verified.
    """
    email = unique_email()

    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
    )
    st = r1.json()["session_token"]
    otp1 = get_last_delivered_otp_for_test(email)
    await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": st, "otp": otp1},
    )

    # Attempt to complete without verifying secondary contact
    r_fail = await client.post(
        "/api/v1/auth/signup/complete",
        json={
            "session_token": st,
            "password": "Password@123",
            "terms_accepted": True,
        },
    )
    assert r_fail.status_code == 400
    assert "both mobile number and email address must be verified" in r_fail.text.lower()


@pytest.mark.asyncio
async def test_sequential_signup_reject_demo_static_otp(client: AsyncClient):
    """
    Static demo OTP '123456' must be rejected (400 Bad Request) on both primary and secondary steps.
    """
    email = unique_email()
    phone = unique_phone()

    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
    )
    st = r1.json()["session_token"]

    # Try static OTP 123456 on primary
    r_bad_prim = await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": st, "otp": "123456"},
    )
    assert r_bad_prim.status_code == 400
    assert "invalid verification code" in r_bad_prim.text.lower()

    # Provide real OTP to proceed
    real_otp1 = get_last_delivered_otp_for_test(email)
    r_good_prim = await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": st, "otp": real_otp1},
    )
    assert r_good_prim.status_code == 200

    # Start secondary
    await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={"session_token": st, "channel": "PHONE", "identifier": phone},
    )

    # Try static OTP 123456 on secondary
    r_bad_sec = await client.post(
        "/api/v1/auth/signup/verify-secondary",
        json={"session_token": st, "otp": "123456"},
    )
    assert r_bad_sec.status_code == 400
    assert "invalid verification code" in r_bad_sec.text.lower()


@pytest.mark.asyncio
async def test_sequential_signup_duplicate_rejection(client: AsyncClient):
    """
    Uniqueness checks: already registered email or phone must be rejected with 409 Conflict.
    """
    # Create an active registered user first
    existing_email = unique_email()
    existing_phone = unique_phone()

    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": existing_email},
    )
    st = r1.json()["session_token"]
    otp1 = get_last_delivered_otp_for_test(existing_email)
    await client.post("/api/v1/auth/signup/verify-primary", json={"session_token": st, "otp": otp1})

    await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={"session_token": st, "channel": "PHONE", "identifier": existing_phone},
    )
    otp2 = get_last_delivered_otp_for_test(existing_phone)
    await client.post("/api/v1/auth/signup/verify-secondary", json={"session_token": st, "otp": otp2})

    await client.post(
        "/api/v1/auth/signup/complete",
        json={"session_token": st, "password": "Password@123", "terms_accepted": True},
    )

    # 1. Primary conflict on duplicate email
    r_dup_email = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": existing_email},
    )
    assert r_dup_email.status_code == 409
    assert r_dup_email.json()["detail"] == "Email already registered"

    # 2. Primary conflict on duplicate phone
    r_dup_phone = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "PHONE", "identifier": existing_phone},
    )
    assert r_dup_phone.status_code == 409
    assert r_dup_phone.json()["detail"] == "Phone already registered"

    # 3. Secondary conflict: start with new email, but enter existing phone as secondary
    new_email = unique_email()
    r_new = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": new_email},
    )
    st2 = r_new.json()["session_token"]
    otp_new = get_last_delivered_otp_for_test(new_email)
    await client.post("/api/v1/auth/signup/verify-primary", json={"session_token": st2, "otp": otp_new})

    r_sec_conflict = await client.post(
        "/api/v1/auth/signup/send-secondary-otp",
        json={"session_token": st2, "channel": "PHONE", "identifier": existing_phone},
    )
    assert r_sec_conflict.status_code == 409
    assert r_sec_conflict.json()["detail"] == "Phone already registered"


@pytest.mark.asyncio
async def test_sequential_signup_max_attempts_lockout(client: AsyncClient):
    """
    More than 5 invalid attempts locks the session with 429 Too Many Requests.
    """
    email = unique_email()
    r1 = await client.post(
        "/api/v1/auth/signup/start-verification",
        json={"account_type": "CANDIDATE", "channel": "EMAIL", "identifier": email},
    )
    st = r1.json()["session_token"]

    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/signup/verify-primary",
            json={"session_token": st, "otp": "000000"},
        )
        assert r.status_code in (400, 429)

    # 6th attempt must be 429
    r_locked = await client.post(
        "/api/v1/auth/signup/verify-primary",
        json={"session_token": st, "otp": "000000"},
    )
    assert r_locked.status_code == 429


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_unauthenticated(client: AsyncClient):
    """
    Unauthenticated requests to any dashboard/profile endpoint return 401 Unauthorized.
    """
    endpoints = [
        "/api/v1/candidates/me/profile",
        "/api/v1/organizations/me/dashboard",
        "/api/v1/institutions/me/dashboard",
        "/api/v1/government/dashboard",
        "/api/v1/admin/stats",
    ]
    for ep in endpoints:
        resp = await client.get(ep)
        assert resp.status_code == 401, f"Expected 401 for {ep}, got {resp.status_code}"


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_candidate(client: AsyncClient):
    """
    Candidate token:
    - /candidates/me/profile -> 200 OK
    - /organizations/me/dashboard -> 403 Forbidden
    - /institutions/me/dashboard -> 403 Forbidden
    - /government/dashboard -> 403 Forbidden
    - /admin/stats -> 403 Forbidden
    """
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "candidate.rajesh@skillvistaar.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Candidate profile works
    assert (await client.get("/api/v1/candidates/me/profile", headers=headers)).status_code == 200

    # Unauthorized dashboards fail with 403
    for ep in [
        "/api/v1/organizations/me/dashboard",
        "/api/v1/institutions/me/dashboard",
        "/api/v1/government/dashboard",
        "/api/v1/admin/stats",
    ]:
        resp = await client.get(ep, headers=headers)
        assert resp.status_code == 403, f"Candidate was not blocked from {ep}: status {resp.status_code}"


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_employer(client: AsyncClient):
    """
    Employer token:
    - /organizations/me/dashboard -> 200 OK
    - /candidates/me/profile -> 403 Forbidden
    - /institutions/me/dashboard -> 403 Forbidden
    - /government/dashboard -> 403 Forbidden
    - /admin/stats -> 403 Forbidden
    """
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "recruiter@tatamotors.com", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Employer dashboard works
    assert (await client.get("/api/v1/organizations/me/dashboard", headers=headers)).status_code == 200

    # Unauthorized endpoints fail with 403
    for ep in [
        "/api/v1/candidates/me/profile",
        "/api/v1/institutions/me/dashboard",
        "/api/v1/government/dashboard",
        "/api/v1/admin/stats",
    ]:
        resp = await client.get(ep, headers=headers)
        assert resp.status_code == 403, f"Employer was not blocked from {ep}: status {resp.status_code}"


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_institution(client: AsyncClient):
    """
    Training Institute token:
    - /institutions/me/dashboard -> 200 OK
    - /candidates/me/profile -> 403 Forbidden
    - /organizations/me/dashboard -> 403 Forbidden
    - /government/dashboard -> 403 Forbidden
    - /admin/stats -> 403 Forbidden
    """
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "principal@rohtaspolytechnic.edu.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Institution dashboard works
    assert (await client.get("/api/v1/institutions/me/dashboard", headers=headers)).status_code == 200

    # Unauthorized endpoints fail with 403
    for ep in [
        "/api/v1/candidates/me/profile",
        "/api/v1/organizations/me/dashboard",
        "/api/v1/government/dashboard",
        "/api/v1/admin/stats",
    ]:
        resp = await client.get(ep, headers=headers)
        assert resp.status_code == 403, f"Institution was not blocked from {ep}: status {resp.status_code}"


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_government(client: AsyncClient):
    """
    Government official token:
    - /government/dashboard -> 200 OK
    - /candidates/me/profile -> 403 Forbidden
    - /organizations/me/dashboard -> 403 Forbidden
    - /institutions/me/dashboard -> 403 Forbidden
    - /admin/stats -> 403 Forbidden
    """
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "central.verifier@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Government dashboard works
    assert (await client.get("/api/v1/government/dashboard", headers=headers)).status_code == 200

    # Unauthorized endpoints fail with 403
    for ep in [
        "/api/v1/candidates/me/profile",
        "/api/v1/organizations/me/dashboard",
        "/api/v1/institutions/me/dashboard",
        "/api/v1/admin/stats",
    ]:
        resp = await client.get(ep, headers=headers)
        assert resp.status_code == 403, f"Government was not blocked from {ep}: status {resp.status_code}"


@pytest.mark.asyncio
async def test_rbac_dashboard_isolation_super_admin(client: AsyncClient):
    """
    Super Admin token has elevated platform clearance across dashboards.
    """
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Super Admin stats works
    assert (await client.get("/api/v1/admin/stats", headers=headers)).status_code == 200

    # Admin has supervisor clearance on govt and org dashboards
    assert (await client.get("/api/v1/government/dashboard", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/organizations/me/dashboard", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/institutions/me/dashboard", headers=headers)).status_code == 200
