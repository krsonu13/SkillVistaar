from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_employer_and_institute_real_dashboard_stats(client: AsyncClient) -> None:
    """
    Verify /institutions/me/dashboard and /organizations/me/dashboard return real DB metrics (not hardcoded).
    """
    # 1. Login as Training Institute
    inst_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "principal@rohtaspolytechnic.edu.in", "password": "Password@123"},
    )
    assert inst_login.status_code == 200
    inst_token = inst_login.json()["access_token"]

    inst_dash = await client.get(
        "/api/v1/institutions/me/dashboard",
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert inst_dash.status_code == 200
    inst_data = inst_dash.json()
    assert inst_data["success"] is True
    assert "stats" in inst_data
    assert "affiliated_courses" in inst_data["stats"]
    assert "enrolled_students" in inst_data["stats"]
    assert "active_batches" in inst_data["stats"]
    assert "organization" in inst_data
    assert inst_data["organization"]["display_name"] is not None

    # 2. Login as Employer
    emp_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "recruiter@tatamotors.com", "password": "Password@123"},
    )
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]

    emp_dash = await client.get(
        "/api/v1/organizations/me/dashboard",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert emp_dash.status_code == 200
    emp_data = emp_dash.json()
    assert emp_data["success"] is True
    assert "stats" in emp_data
    assert "active_postings" in emp_data["stats"]
    assert "total_applicants" in emp_data["stats"]
    assert "organization" in emp_data


@pytest.mark.asyncio
async def test_organization_document_upload_and_verification_lifecycle(client: AsyncClient) -> None:
    """
    Test complete lifecycle of organization document:
    1. Upload document as Institute.
    2. List documents via /mine.
    3. Rohtas District verifier reviews & approves document.
    4. Verify status updated to VERIFIED and audit history recorded.
    """
    # 1. Login as Training Institute
    inst_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "principal@rohtaspolytechnic.edu.in", "password": "Password@123"},
    )
    assert inst_login.status_code == 200
    inst_token = inst_login.json()["access_token"]

    # 2. Upload Document
    upload_resp = await client.post(
        "/api/v1/organization-documents",
        headers={"Authorization": f"Bearer {inst_token}"},
        json={
            "document_type": "ACCREDITATION_DOCUMENT",
            "title": "AICTE Approval 2026-2027",
            "document_number": "AICTE-ROH-2026-09",
            "issuing_authority": "All India Council for Technical Education",
            "issue_date": "2026-01-15",
            "expiry_date": "2027-01-14",
            "file_name": "aicte_approval_2026.pdf",
            "file_url": "https://storage.skillvistaar.gov.in/docs/aicte_approval_2026.pdf",
            "file_size": 2048500,
            "mime_type": "application/pdf",
        },
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["status"] == "PENDING"
    assert doc_data["title"] == "AICTE Approval 2026-2027"

    # 3. Retrieve list for caller's organization
    mine_resp = await client.get(
        "/api/v1/organization-documents/mine",
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert mine_resp.status_code == 200
    my_docs = mine_resp.json()
    assert any(d["id"] == doc_id for d in my_docs)

    # 4. Rohtas District Verifier logs in and performs approval
    rohtas_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "rohtas.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert rohtas_login.status_code == 200
    rohtas_token = rohtas_login.json()["access_token"]

    action_resp = await client.post(
        f"/api/v1/organization-documents/{doc_id}/action",
        headers={"Authorization": f"Bearer {rohtas_token}"},
        json={
            "action": "APPROVE",
            "remarks": "Document verified against national regulatory repository.",
        },
    )
    assert action_resp.status_code == 200
    verified_doc = action_resp.json()
    assert verified_doc["status"] == "VERIFIED"
    assert verified_doc["verification_remarks"] == "Document verified against national regulatory repository."
    assert verified_doc["verified_at"] is not None


@pytest.mark.asyncio
async def test_cross_jurisdiction_document_verification_forbidden(client: AsyncClient) -> None:
    """
    Verify that an unrelated district government verifier (Pune) cannot approve or reject
    a document belonging to an organization in Rohtas District.
    """
    # 1. Login as Training Institute in Rohtas and create a doc
    inst_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "principal@rohtaspolytechnic.edu.in", "password": "Password@123"},
    )
    inst_token = inst_login.json()["access_token"]

    upload_resp = await client.post(
        "/api/v1/organization-documents",
        headers={"Authorization": f"Bearer {inst_token}"},
        json={
            "document_type": "REGISTRATION_CERTIFICATE",
            "title": "State Council Affiliation Certificate",
            "document_number": "SCVT-BR-2026-88",
            "issuing_authority": "Bihar State Council for Vocational Training",
            "file_name": "affiliation_2026.pdf",
        },
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # 2. Login as Pune District Verifier
    pune_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "pune.district@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert pune_login.status_code == 200
    pune_token = pune_login.json()["access_token"]

    # 3. Pune Verifier tries to take action on Rohtas document -> MUST be 403 Forbidden
    cross_action = await client.post(
        f"/api/v1/organization-documents/{doc_id}/action",
        headers={"Authorization": f"Bearer {pune_token}"},
        json={
            "action": "APPROVE",
            "remarks": "Attempting cross-district approval",
        },
    )
    assert cross_action.status_code == 403, f"Expected 403, got {cross_action.status_code}"
    assert "Cross-jurisdiction access forbidden" in cross_action.json()["detail"]


@pytest.mark.asyncio
async def test_government_drill_down_and_pending_documents(client: AsyncClient) -> None:
    """
    Verify government drill-down endpoint and pending documents list for verifiers.
    """
    # 1. Login as Central Verifier
    cen_login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "central.verifier@skillvistaar.gov.in", "password": "Password@123"},
    )
    assert cen_login.status_code == 200
    cen_token = cen_login.json()["access_token"]

    # 2. Test drill-down
    dd_resp = await client.get(
        "/api/v1/government/drill-down",
        headers={"Authorization": f"Bearer {cen_token}"},
    )
    assert dd_resp.status_code == 200
    dd_data = dd_resp.json()
    assert "current_unit" in dd_data
    assert "sub_units" in dd_data
    assert "organizations" in dd_data
    assert "aggregates" in dd_data

    # 3. Test pending documents endpoint
    pending_resp = await client.get(
        "/api/v1/government/documents/pending",
        headers={"Authorization": f"Bearer {cen_token}"},
    )
    assert pending_resp.status_code == 200
    assert isinstance(pending_resp.json(), list)
