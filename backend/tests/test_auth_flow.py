from uuid import uuid4

import pytest
from httpx import AsyncClient


def unique_email() -> str:
    return f"test_{uuid4().hex[:12]}@example.com"


def unique_phone() -> str:
    return f"9{uuid4().int % 1000000009:09d}"


from app.services.otp_delivery_service import get_last_delivered_otp_for_test


async def complete_verification(
    client: AsyncClient,
    verification_token: str,
    channel: str = "EMAIL",
):
    headers = {"Authorization": f"Bearer {verification_token}"}

    req_resp = await client.post(
        "/api/v1/auth/verification/request",
        json={"channel": channel, "purpose": "SIGNUP"},
        headers=headers,
    )
    assert req_resp.status_code == 200, (
        req_resp.status_code,
        req_resp.text,
    )

    otp = get_last_delivered_otp_for_test()
    assert otp, "OTP must be delivered to outbox"

    ver_resp = await client.post(
        "/api/v1/auth/verification/verify",
        json={"channel": channel, "otp": otp, "purpose": "SIGNUP"},
        headers=headers,
    )
    assert ver_resp.status_code == 200, (
        ver_resp.status_code,
        ver_resp.text,
    )


@pytest.mark.asyncio
async def test_complete_authentication_flow(client: AsyncClient):
    email = unique_email()
    password = "StrongPass@123"

    # 1. SIGNUP
    signup_response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "account_type": "CANDIDATE",
        },
    )

    assert signup_response.status_code in (200, 201), (
        signup_response.status_code,
        signup_response.text,
    )

    signup_data = signup_response.json()
    assert signup_data["email"] == email
    assert signup_data["account_type"] == "CANDIDATE"
    assert signup_data.get("verification_token")

    # 1b. VERIFY ACCOUNT BEFORE LOGIN
    await complete_verification(
        client,
        signup_data["verification_token"],
        channel="EMAIL",
    )

    # 2. LOGIN
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200, (
        login_response.status_code,
        login_response.text,
    )

    login_data = login_response.json()
    assert login_data.get("access_token")
    assert login_data.get("refresh_token")
    assert login_data["token_type"].lower() == "bearer"

    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 3. GET /auth/me
    me_response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers,
    )

    assert me_response.status_code == 200, (
        me_response.status_code,
        me_response.text,
    )

    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["account_type"] == "CANDIDATE"
    user_id = me_data["id"]

    # 4. GET /auth/me/roles
    roles_response = await client.get(
        "/api/v1/auth/me/roles",
        headers=auth_headers,
    )

    assert roles_response.status_code == 200, (
        roles_response.status_code,
        roles_response.text,
    )

    roles_data = roles_response.json()
    assert roles_data["user_id"] == user_id
    assert roles_data["account_type"] == "CANDIDATE"
    assert "CANDIDATE" in roles_data["roles"]

    # 5. REFRESH TOKEN
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200, (
        refresh_response.status_code,
        refresh_response.text,
    )

    refresh_data = refresh_response.json()
    new_access_token = refresh_data["access_token"]
    new_refresh_token = refresh_data["refresh_token"]
    assert new_refresh_token != refresh_token

    # 6. OLD REFRESH TOKEN FAILS
    old_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert old_refresh_response.status_code == 401

    # 7. NEW ACCESS TOKEN WORKS
    new_me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )

    assert new_me_response.status_code == 200
    assert new_me_response.json()["id"] == user_id

    # 8. LOGOUT
    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh_token},
    )

    assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_unverified_signup_resume_and_duplicate_verified_rejection(client: AsyncClient):
    email = unique_email()
    password = "StrongPass@123"

    # 1. Unverified signup (1st time)
    r1 = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "account_type": "CANDIDATE"},
    )
    assert r1.status_code in (200, 201)
    tok1 = r1.json()["verification_token"]

    # 2. Resuming unverified signup with WRONG password -> 401 Unauthorized
    r_bad_pw = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "WrongPassword@123", "account_type": "CANDIDATE"},
    )
    assert r_bad_pw.status_code == 401, r_bad_pw.text

    # 3. Resuming unverified signup with CORRECT password -> 200/201 (not 409)
    r2 = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "account_type": "CANDIDATE"},
    )
    assert r2.status_code in (200, 201)

    # 4. Complete verification
    await complete_verification(client, tok1, channel="EMAIL")

    # 5. Duplicate signup for VERIFIED account -> 409 Conflict
    r3 = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "account_type": "CANDIDATE"},
    )
    assert r3.status_code == 409, r3.text


@pytest.mark.asyncio
async def test_candidate_phone_verified_login_allowed(client: AsyncClient):
    phone = unique_phone()
    password = "StrongPass@123"

    # Signup with candidate phone
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"phone": phone, "password": password, "account_type": "CANDIDATE"},
    )
    assert signup_resp.status_code in (200, 201)
    v_token = signup_resp.json()["verification_token"]

    # Verify phone
    await complete_verification(client, v_token, channel="PHONE")

    # Login should be allowed even if email is unverified/absent
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": phone, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text


@pytest.mark.asyncio
async def test_prevent_account_takeover_merging(client: AsyncClient):
    email = unique_email()
    phone = unique_phone()
    password = "StrongPass@123"

    # Create account A with email
    r1 = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "account_type": "CANDIDATE"},
    )
    assert r1.status_code in (200, 201)

    # Create account B with phone
    r2 = await client.post(
        "/api/v1/auth/signup",
        json={"phone": phone, "password": password, "account_type": "CANDIDATE"},
    )
    assert r2.status_code in (200, 201)

    # Attempt to signup combining email of account A and phone of account B -> 409 Conflict
    r3 = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "phone": phone, "password": password, "account_type": "CANDIDATE"},
    )
    assert r3.status_code == 409, r3.text


@pytest.mark.asyncio
async def test_candidate_otp_verification_and_dashboard_profile(client: AsyncClient):
    email = unique_email()
    password = "StrongPass@123"
    full_name = "Vikram Aditya"

    # 1. Signup candidate with fullName
    r_signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "account_type": "CANDIDATE",
            "fullName": full_name,
        },
    )
    assert r_signup.status_code in (200, 201), r_signup.text
    signup_data = r_signup.json()
    assert signup_data["email"] == email
    assert signup_data["email_verified"] is False

    # 2. Login before verification returns 403 Forbidden
    r_unver_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
    )
    assert r_unver_login.status_code == 403, r_unver_login.text
    assert "unverified" in r_unver_login.json()["detail"].lower()

    # 3. Login with wrong password returns 401 or 403
    r_bad_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "WrongPassword@123"},
    )
    assert r_bad_login.status_code in (401, 403)

    # 4. Verify OTP using direct verify-otp endpoint with real OTP from outbox
    real_otp = get_last_delivered_otp_for_test(email)
    assert real_otp, "Real OTP was not dispatched"
    r_verify = await client.post(
        "/api/v1/auth/verify-otp",
        json={
            "identifier": email,
            "otp": real_otp,
            "accountType": "candidate",
        },
    )
    assert r_verify.status_code == 200, r_verify.text
    verify_data = r_verify.json()
    assert verify_data["success"] is True
    assert verify_data.get("token") or verify_data.get("access_token")
    assert verify_data.get("refresh_token")
    assert verify_data["user"]["isVerified"] is True

    # 5. Login after verification returns 200 OK with tokens
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
    )
    assert r_login.status_code == 200, r_login.text
    token_data = r_login.json()
    token = token_data["access_token"]
    assert token_data["user"]["email"] == email

    # 6. Candidate Profile endpoint /candidates/me/profile works
    r_profile = await client.get(
        "/api/v1/candidates/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_profile.status_code == 200, r_profile.text
    prof = r_profile.json()
    assert prof["first_name"] == "Vikram"
    assert prof["last_name"] == "Aditya"
    assert prof["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_employer_and_institute_signup_auto_provisioning(client: AsyncClient):
    # Employer
    emp_email = unique_email()
    password = "StrongPass@123"
    r_emp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": emp_email,
            "password": password,
            "account_type": "EMPLOYER",
            "companyName": "Acme Innovations Pvt Ltd",
        },
    )
    assert r_emp.status_code in (200, 201), r_emp.text

    # Verify Employer OTP
    emp_otp = get_last_delivered_otp_for_test(emp_email)
    assert emp_otp, "Employer OTP was not dispatched"
    r_v_emp = await client.post(
        "/api/v1/auth/verify-otp",
        json={"identifier": emp_email, "otp": emp_otp, "accountType": "employer"},
    )
    assert r_v_emp.status_code == 200

    # Training Institute
    inst_email = unique_email()
    r_inst = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": inst_email,
            "password": password,
            "account_type": "TRAINING_INSTITUTE",
            "instituteName": "National Vocational Academy",
        },
    )
    assert r_inst.status_code in (200, 201), r_inst.text

    # Verify Institute OTP
    inst_otp = get_last_delivered_otp_for_test(inst_email)
    assert inst_otp, "Institute OTP was not dispatched"
    r_v_inst = await client.post(
        "/api/v1/auth/verify-otp",
        json={"identifier": inst_email, "otp": inst_otp, "accountType": "institute"},
    )
    assert r_v_inst.status_code == 200


@pytest.mark.asyncio
async def test_signup_409_clear_messages_and_uniqueness(client: AsyncClient):
    email = unique_email()
    phone = unique_phone()
    password = "StrongPass@123"

    # 1. Signup with brand new email & phone -> 201 Created
    r_new = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "phone": phone,
            "password": password,
            "account_type": "CANDIDATE",
            "fullName": "Priya Sharma",
        },
    )
    assert r_new.status_code in (200, 201), r_new.text
    assert r_new.json()["email"] == email

    # Verify the account with real OTP
    real_otp = get_last_delivered_otp_for_test(email)
    assert real_otp, "Real OTP was not dispatched"
    v_resp = await client.post(
        "/api/v1/auth/verify-otp",
        json={"identifier": email, "otp": real_otp, "accountType": "candidate"},
    )
    assert v_resp.status_code == 200

    # 2. Duplicate signup with same email -> 409 Conflict with "Email already registered"
    r_dup_email = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "phone": unique_phone(),
            "password": password,
            "account_type": "CANDIDATE",
        },
    )
    assert r_dup_email.status_code == 409, r_dup_email.text
    assert r_dup_email.json()["detail"] == "Email already registered"

    # 3. Duplicate signup with same phone -> 409 Conflict with "Phone already registered"
    r_dup_phone = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": unique_email(),
            "phone": phone,
            "password": password,
            "account_type": "CANDIDATE",
        },
    )
    assert r_dup_phone.status_code == 409, r_dup_phone.text
    assert r_dup_phone.json()["detail"] == "Phone already registered"

    # 4. Duplicate phone with +91 variation -> 409 Conflict with "Phone already registered"
    r_dup_phone_var = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": unique_email(),
            "phone": f"+91{phone}",
            "password": password,
            "account_type": "CANDIDATE",
        },
    )
    assert r_dup_phone_var.status_code == 409, r_dup_phone_var.text
    assert r_dup_phone_var.json()["detail"] == "Phone already registered"
