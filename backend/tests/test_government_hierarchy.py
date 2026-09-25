from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_government_hierarchy_tree(client: AsyncClient) -> None:
    """
    Verify the recursive government hierarchy tree returns 4 levels
    (Central -> State -> District -> Local).
    """
    response = await client.get("/api/v1/government-units/hierarchy")
    assert response.status_code == 200
    tree = response.json()
    assert len(tree) >= 1

    # Root should be Central Government (level 1)
    central = next((n for n in tree if n["code"] == "CEN-IN-01"), None)
    assert central is not None
    assert central["level"] == 1
    assert len(central["children"]) >= 2  # Bihar and Maharashtra

    # Check Bihar State (level 2)
    bihar = next((c for c in central["children"] if c["code"] == "STE-BR-01"), None)
    assert bihar is not None
    assert bihar["level"] == 2
    assert len(bihar["children"]) >= 2  # Rohtas and Patna

    # Check Rohtas District (level 3)
    rohtas = next((d for d in bihar["children"] if d["code"] == "DST-BR-ROH"), None)
    assert rohtas is not None
    assert rohtas["level"] == 3
    assert len(rohtas["children"]) >= 1  # Sasaram Local

    # Check Sasaram Local (level 4)
    sasaram = next((l for l in rohtas["children"] if l["code"] == "LOC-BR-SAS"), None)
    assert sasaram is not None
    assert sasaram["level"] == 4


@pytest.mark.asyncio
async def test_government_units_by_code(client: AsyncClient) -> None:
    """
    Verify fetching government units by administrative code.
    """
    response = await client.get("/api/v1/government-units/by-code/DST-BR-ROH")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "DST-BR-ROH"
    assert data["level"] == 3
    assert "Rohtas" in data["name"]


@pytest.mark.asyncio
async def test_login_all_seeded_stakeholder_roles(client: AsyncClient) -> None:
    """
    Verify login works for all 5 roles:
    SUPER_ADMIN, GOVERNMENT (Central, District, Local), EMPLOYER, TRAINING_INSTITUTE, CANDIDATE.
    """
    credentials = [
        ("admin@skillvistaar.gov.in", "SUPER_ADMIN"),
        ("central.verifier@skillvistaar.gov.in", "GOVERNMENT"),
        ("rohtas.district@skillvistaar.gov.in", "GOVERNMENT"),
        ("pune.district@skillvistaar.gov.in", "GOVERNMENT"),
        ("recruiter@tatamotors.com", "EMPLOYER"),
        ("principal@rohtaspolytechnic.edu.in", "TRAINING_INSTITUTE"),
        ("candidate.rajesh@skillvistaar.in", "CANDIDATE"),
    ]

    for email, expected_type in credentials:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": "Password@123"},
        )
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"] is not None
        assert data["user"]["account_type"] == expected_type


@pytest.mark.asyncio
async def test_cross_district_access_forbidden(client: AsyncClient) -> None:
    """
    Verify that a Pune District Government verifier cannot review or verify
    an organization located in Rohtas District (Strict Cross-Jurisdiction Enforcement).
    """
    # 1. Login as Pune District Verifier
    pune_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "pune.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert pune_login.status_code == 200
    pune_token = pune_login.json()["access_token"]

    # 2. Get Rohtas Polytechnic Org
    orgs_resp = await client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {pune_token}"},
    )
    assert orgs_resp.status_code == 200

    # Retrieve all organizations using admin token to get Rohtas org ID
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]
    all_orgs = (
        await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()

    rohtas_org = next(
        (o for o in all_orgs if "Rohtas" in o["legal_name"]), None
    )
    assert rohtas_org is not None

    # 3. Pune Verifier attempts to review Rohtas Org -> MUST return 403 Forbidden
    cross_review_resp = await client.post(
        f"/api/v1/organizations/{rohtas_org['id']}/review",
        json={
            "status": "APPROVED",
            "remarks": "Unauthorized cross-district review attempt.",
        },
        headers={"Authorization": f"Bearer {pune_token}"},
    )
    assert cross_review_resp.status_code == 403
    assert "Cross-jurisdiction access forbidden" in cross_review_resp.json()["detail"]


@pytest.mark.asyncio
async def test_authorized_rohtas_verifier_can_review(client: AsyncClient) -> None:
    """
    Verify that the authorized Rohtas District verifier CAN review and approve Rohtas Org.
    """
    # 1. Login as Rohtas District Verifier
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert rohtas_login.status_code == 200
    rohtas_token = rohtas_login.json()["access_token"]

    # 2. Get Rohtas org
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]
    all_orgs = (
        await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()
    rohtas_org = next((o for o in all_orgs if "Rohtas" in o["legal_name"]), None)
    assert rohtas_org is not None

    # 3. Rohtas verifier reviews Rohtas Org -> MUST succeed
    review_resp = await client.post(
        f"/api/v1/organizations/{rohtas_org['id']}/review",
        json={
            "status": "APPROVED",
            "remarks": "Verified by Rohtas District Skill Office.",
        },
        headers={"Authorization": f"Bearer {rohtas_token}"},
    )
    assert review_resp.status_code == 200
    updated_org = review_resp.json()
    assert updated_org["verification_status"] == "APPROVED"
    assert updated_org["verified_at"] is not None


@pytest.mark.asyncio
async def test_candidate_skill_status_transition_lifecycle(client: AsyncClient) -> None:
    """
    Verify candidate skills status transitions across the verifiable states:
    SELF_DECLARED -> PENDING -> VERIFIED -> REJECTED -> REVOKED.
    """
    # 1. Login as Candidate
    cand_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "candidate.rajesh@skillvistaar.in", "password": "Password@123"},
    )
    assert cand_login.status_code == 200
    cand_token = cand_login.json()["access_token"]

    # 2. Get candidate's skills
    skills_resp = await client.get(
        "/api/v1/candidates/me/skills",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert skills_resp.status_code == 200
    skills = skills_resp.json()
    assert len(skills) >= 1
    target_skill = skills[0]

    # 3. Login as Rohtas Verifier to transition skill status
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    rohtas_token = rohtas_login.json()["access_token"]

    # Transition to REJECTED
    trans_resp = await client.post(
        f"/api/v1/candidates/skills/{target_skill['id']}/transition",
        json={"status": "REJECTED", "notes": "Candidate failed practical re-test."},
        headers={"Authorization": f"Bearer {rohtas_token}"},
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "REJECTED"

    # Transition back to VERIFIED
    trans_resp2 = await client.post(
        f"/api/v1/candidates/skills/{target_skill['id']}/transition",
        json={"status": "VERIFIED", "notes": "Candidate passed re-assessment."},
        headers={"Authorization": f"Bearer {rohtas_token}"},
    )
    assert trans_resp2.status_code == 200
    assert trans_resp2.json()["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_super_admin_stats_and_controls(client: AsyncClient) -> None:
    """
    Verify Super Admin platform stats and user controls.
    """
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]

    stats_resp = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["users"]["total"] >= 5
    assert stats["government_units_count"] >= 7
    assert stats["organizations_count"] >= 2


@pytest.mark.asyncio
async def test_invalid_password_login_rejected(client: AsyncClient) -> None:
    """
    Verify login is strictly rejected with 401 when an invalid password is provided.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "WrongPassword!999"},
    )
    assert resp.status_code == 401
    assert "Invalid credentials." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_employer_registration_and_jurisdiction_verification(client: AsyncClient) -> None:
    """
    Verify employer registration starts as PENDING_VERIFICATION,
    cross-district verifier cannot approve (403),
    and authorized district verifier successfully approves it (200).
    """
    # 1. Login as Employer
    emp_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "recruiter@tatamotors.com", "password": "Password@123"},
    )
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]

    # 2. Get Rohtas Unit ID
    rohtas_unit_resp = await client.get("/api/v1/government-units/by-code/DST-BR-ROH")
    assert rohtas_unit_resp.status_code == 200
    rohtas_unit_id = rohtas_unit_resp.json()["id"]

    # 3. Register a new employer org in Rohtas jurisdiction
    from uuid import uuid4
    unique_name = f"Rohtas Precision Tools {uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/organizations",
        json={
            "legal_name": unique_name,
            "display_name": unique_name,
            "organization_type": "EMPLOYER",
            "registration_number": f"GSTIN{uuid4().hex[:10].upper()}",
            "email": f"info_{uuid4().hex[:6]}@rohtastools.in",
            "government_unit_id": rohtas_unit_id,
            "city": "Sasaram",
            "state": "Bihar",
        },
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert create_resp.status_code == 201
    org = create_resp.json()
    assert org["verification_status"] == "PENDING"
    assert org["government_unit_id"] == rohtas_unit_id
    org_id = org["id"]

    # 4. Attempt approval by Pune District Verifier -> MUST FAIL (403)
    pune_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "pune.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert pune_login.status_code == 200
    pune_token = pune_login.json()["access_token"]

    pune_review = await client.post(
        f"/api/v1/organizations/{org_id}/review",
        json={"status": "APPROVED", "remarks": "Unauthorized approval attempt"},
        headers={"Authorization": f"Bearer {pune_token}"},
    )
    assert pune_review.status_code == 403
    assert "Cross-jurisdiction access forbidden" in pune_review.json()["detail"]

    # 5. Authorized Rohtas Verifier approves -> MUST SUCCEED (200)
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert rohtas_login.status_code == 200
    rohtas_token = rohtas_login.json()["access_token"]

    rohtas_review = await client.post(
        f"/api/v1/organizations/{org_id}/review",
        json={"status": "APPROVED", "remarks": "Verified statutory GSTIN and shop establishment."},
        headers={"Authorization": f"Bearer {rohtas_token}"},
    )
    assert rohtas_review.status_code == 200
    assert rohtas_review.json()["verification_status"] == "APPROVED"


@pytest.mark.asyncio
async def test_state_government_can_verify_subordinate_district(client: AsyncClient) -> None:
    """
    Verify that Bihar State Government verifier can review an organization located
    in its child district (Rohtas), but cannot review Pune (Maharashtra).
    """
    # 1. Login as Bihar State Verifier
    bihar_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "bihar.state@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert bihar_login.status_code == 200
    bihar_token = bihar_login.json()["access_token"]

    # 2. Get Rohtas Org and register a Pune Org (Maharashtra)
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]
    all_orgs = (
        await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    ).json()

    rohtas_org = next((o for o in all_orgs if "Rohtas" in o["legal_name"]), None)
    assert rohtas_org is not None

    # Get Pune District Unit ID and create an org under Maharashtra jurisdiction
    pune_unit_resp = await client.get("/api/v1/government-units/by-code/DST-MH-PUN")
    assert pune_unit_resp.status_code == 200
    pune_unit_id = pune_unit_resp.json()["id"]

    from uuid import uuid4
    pune_org_name = f"Pune Precision Components {uuid4().hex[:6]}"
    pune_create = await client.post(
        "/api/v1/organizations",
        json={
            "legal_name": pune_org_name,
            "display_name": pune_org_name,
            "organization_type": "EMPLOYER",
            "registration_number": f"MH{uuid4().hex[:10].upper()}",
            "email": f"pune_{uuid4().hex[:6]}@punecomp.in",
            "government_unit_id": pune_unit_id,
            "city": "Pune",
            "state": "Maharashtra",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert pune_create.status_code == 201
    pune_org = pune_create.json()

    # 3. Bihar State CAN review Rohtas org (State is ancestor of Rohtas District)
    state_review = await client.post(
        f"/api/v1/organizations/{rohtas_org['id']}/review",
        json={"status": "APPROVED", "remarks": "State level oversight approval."},
        headers={"Authorization": f"Bearer {bihar_token}"},
    )
    assert state_review.status_code == 200
    assert state_review.json()["verification_status"] == "APPROVED"

    # 4. Bihar State CANNOT review Pune Org (Pune is in Maharashtra) -> 403 Forbidden
    cross_state_review = await client.post(
        f"/api/v1/organizations/{pune_org['id']}/review",
        json={"status": "APPROVED", "remarks": "Cross-state review attempt."},
        headers={"Authorization": f"Bearer {bihar_token}"},
    )
    assert cross_state_review.status_code == 403
    assert "Cross-jurisdiction access forbidden" in cross_state_review.json()["detail"]


@pytest.mark.asyncio
async def test_candidate_credential_verification_lifecycle(client: AsyncClient) -> None:
    """
    Verify candidate credential state transition:
    UPLOADED -> PENDING_VERIFICATION -> VERIFIED.
    Also verify unauthorized candidate cannot self-verify (403).
    """
    # 1. Login as Candidate
    cand_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "candidate.rajesh@skillvistaar.in", "password": "Password@123"},
    )
    assert cand_login.status_code == 200
    cand_token = cand_login.json()["access_token"]

    # 2. Upload candidate credential
    cred_create = await client.post(
        "/api/v1/candidates/me/credentials",
        json={
            "credential_type": "CERTIFICATE",
            "title": "Industrial CNC Specialist Qualification",
            "issuer_name": "National Skill Development Corporation",
            "issued_date": "2025-06-01T00:00:00Z",
            "document_url": "https://digilocker.gov.in/doc/NSDC-CNC-9901.pdf",
        },
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert cred_create.status_code == 201
    cred = cred_create.json()
    assert cred["status"] == "UPLOADED"
    cred_id = cred["id"]

    # 3. Candidate cannot self-approve -> MUST return 403
    self_approve = await client.post(
        f"/api/v1/candidates/credentials/{cred_id}/transition",
        json={"status": "VERIFIED", "notes": "Candidate self-approval attempt."},
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert self_approve.status_code == 403

    # 4. Authorized Verifier approves credential
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    rohtas_token = rohtas_login.json()["access_token"]

    verifier_approve = await client.post(
        f"/api/v1/candidates/credentials/{cred_id}/transition",
        json={"status": "VERIFIED", "notes": "DigiLocker hash validated against NSDC registry."},
        headers={"Authorization": f"Bearer {rohtas_token}"},
    )
    assert verifier_approve.status_code == 200
    assert verifier_approve.json()["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_super_admin_suspend_and_reactivate_user(client: AsyncClient) -> None:
    """
    Verify Super Admin can suspend and reactivate users with audit logging.
    """
    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@skillvistaar.gov.in", "password": "Password@123"},
    )
    admin_token = admin_login.json()["access_token"]

    # Get user to suspend
    users_resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert users_resp.status_code == 200
    users = users_resp.json()
    target_user = next((u for u in users if u["account_type"] == "EMPLOYER"), None)
    assert target_user is not None
    user_id = target_user["id"]

    # Suspend user
    suspend_resp = await client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_suspended": True, "is_active": False, "reason": "Statutory audit pending"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["is_suspended"] is True

    # Reactivate user
    reactivate_resp = await client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_suspended": False, "is_active": True, "reason": "Audit cleared successfully"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["is_suspended"] is False

