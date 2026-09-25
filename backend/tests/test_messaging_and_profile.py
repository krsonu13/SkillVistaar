import io
from uuid import uuid4
import pytest
from httpx import AsyncClient

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
    assert req_resp.status_code == 200, req_resp.text

    otp = get_last_delivered_otp_for_test()
    assert otp, "OTP must be delivered to outbox"

    ver_resp = await client.post(
        "/api/v1/auth/verification/verify",
        json={"channel": channel, "otp": otp, "purpose": "SIGNUP"},
        headers=headers,
    )
    assert ver_resp.status_code == 200, ver_resp.text


@pytest.mark.asyncio
async def test_profile_and_messaging_system_flow(client: AsyncClient):
    uid_a = uuid4().hex[:8]
    u_a_email = f"candidate_a_{uid_a}@example.com"
    u_a_phone = f"9{uuid4().int % 1000000009:09d}"
    u_a_username = f"user_a_{uid_a}"
    password = "StrongPass@123"

    reg_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": u_a_email,
            "phone": u_a_phone,
            "password": password,
            "account_type": "CANDIDATE",
            "username": u_a_username,
        },
    )
    assert reg_a.status_code in (200, 201), reg_a.text
    signup_a = reg_a.json()
    await complete_verification(client, signup_a["verification_token"], channel="EMAIL")

    login_a = await client.post(
        "/api/v1/auth/login",
        json={"identifier": u_a_username, "password": password},
    )
    assert login_a.status_code == 200, login_a.text
    token_a = login_a.json()["access_token"]
    user_a_id = login_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Create User B (Candidate)
    uid_b = uuid4().hex[:8]
    u_b_email = f"candidate_b_{uid_b}@example.com"
    u_b_phone = f"9{uuid4().int % 1000000009:09d}"
    u_b_username = f"user_b_{uid_b}"

    reg_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": u_b_email,
            "phone": u_b_phone,
            "password": password,
            "account_type": "CANDIDATE",
            "username": u_b_username,
        },
    )
    assert reg_b.status_code in (200, 201), reg_b.text
    signup_b = reg_b.json()
    await complete_verification(client, signup_b["verification_token"], channel="EMAIL")

    login_b = await client.post(
        "/api/v1/auth/login",
        json={"identifier": u_b_username, "password": password},
    )
    assert login_b.status_code == 200, login_b.text
    token_b = login_b.json()["access_token"]
    user_b_id = login_b.json()["user"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Test Profile Management for User A
    get_prof = await client.get("/api/v1/candidates/me/profile", headers=headers_a)
    assert get_prof.status_code == 200, get_prof.text
    prof_data = get_prof.json()
    assert prof_data["username"] == u_a_username

    # Update profile with education, experience, projects, headline, bio
    update_payload = {
        "first_name": "Aarav",
        "last_name": "Sharma",
        "headline": "Lead Full-Stack Systems Engineer",
        "bio": "Passionate developer building large scale GovTech architectures.",
        "preferred_location": "New Delhi, India",
        "education": [
            {
                "institution": "Indian Institute of Technology Delhi",
                "degree": "B.Tech Computer Science",
                "field_of_study": "Computer Science",
                "startDate": "2020",
                "endDate": "2024",
                "grade": "9.4 CGPA",
            }
        ],
        "experience": [
            {
                "title": "Software Engineer",
                "organization": "National Informatics Centre",
                "employmentType": "Full-time",
                "location": "New Delhi",
                "startDate": "2024",
                "endDate": "Present",
                "description": "Architecting resilient digital public infrastructure.",
            }
        ],
        "projects": [
            {
                "title": "SkillVistaar Open Protocol",
                "description": "Federated credential discovery mechanism.",
                "tags": ["FastAPI", "React", "PostgreSQL"],
                "link": "https://github.com/skillvistaar",
            }
        ],
        "languages": [
            {"language": "English", "proficiency": "Native / Bilingual"},
            {"language": "Hindi", "proficiency": "Native"},
        ],
        "career_preferences": {
            "preferred_role": "Senior Engineer",
            "preferred_locations": ["New Delhi", "Bengaluru"],
        },
    }
    put_prof = await client.put(
        "/api/v1/candidates/me/profile",
        json=update_payload,
        headers=headers_a,
    )
    assert put_prof.status_code == 200, put_prof.text
    updated_prof = put_prof.json()
    assert updated_prof["first_name"] == "Aarav"
    assert updated_prof["last_name"] == "Sharma"
    assert updated_prof["headline"] == "Lead Full-Stack Systems Engineer"
    assert len(updated_prof["education"]) == 1
    assert len(updated_prof["experience"]) == 1
    assert len(updated_prof["projects"]) == 1
    assert updated_prof["profile_completion_percentage"] >= 60

    # 4. Test Avatar Upload for User A
    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    avatar_upload = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", io.BytesIO(dummy_image), "image/png")},
        headers=headers_a,
    )
    assert avatar_upload.status_code == 200, avatar_upload.text
    avatar_url = avatar_upload.json()["avatar_url"]
    assert "/api/v1/users/media/" in avatar_url

    # Verify media streaming
    media_res = await client.get(avatar_url)
    assert media_res.status_code == 200
    assert media_res.headers["content-type"] == "image/png"

    # 5. Test Follow / Unfollow System
    # Self-follow must be forbidden/rejected with 400
    self_follow = await client.post(
        "/api/v1/following/toggle",
        json={"target_type": "USER", "target_id": user_a_id},
        headers=headers_a,
    )
    assert self_follow.status_code == 400

    # User A follows User B
    follow_res = await client.post(
        "/api/v1/following/toggle",
        json={"target_type": "USER", "target_id": user_b_id},
        headers=headers_a,
    )
    assert follow_res.status_code == 200, follow_res.text
    follow_data = follow_res.json()
    assert follow_data["is_following"] is True
    assert follow_data["followers_count"] == 1

    # User A toggles unfollow User B
    unfollow_res = await client.post(
        "/api/v1/following/toggle",
        json={"target_type": "USER", "target_id": user_b_id},
        headers=headers_a,
    )
    assert unfollow_res.status_code == 200, unfollow_res.text
    unfollow_data = unfollow_res.json()
    assert unfollow_data["is_following"] is False
    assert unfollow_data["followers_count"] == 0

    # Re-follow User B for relationship testing
    await client.post(
        "/api/v1/following/toggle",
        json={"target_type": "USER", "target_id": user_b_id},
        headers=headers_a,
    )

    # 6. Test Direct Messaging & Requests Flow
    # Initial message from User A to User B -> should create conversation in REQUESTED status
    send_res = await client.post(
        "/api/v1/messages/send",
        json={
            "recipient_id": user_b_id,
            "content": "Hello! I saw your profile and would love to collaborate on open skills.",
        },
        headers=headers_a,
    )
    assert send_res.status_code == 201, send_res.text
    sent_msg = send_res.json()
    assert sent_msg["sender_id"] == user_a_id
    assert sent_msg["recipient_id"] == user_b_id
    conv_id = sent_msg["conversation_id"]

    # For User B: conversation should appear in "requests" folder
    reqs_b = await client.get(
        "/api/v1/messages/conversations?folder=requests",
        headers=headers_b,
    )
    assert reqs_b.status_code == 200, reqs_b.text
    requests_list = reqs_b.json()
    assert len(requests_list) == 1
    assert requests_list[0]["id"] == conv_id
    assert requests_list[0]["status"] == "REQUESTED"
    assert requests_list[0]["other_user"]["id"] == user_a_id

    # For User B: inbox should NOT show this unaccepted request
    inbox_b = await client.get(
        "/api/v1/messages/conversations?folder=inbox",
        headers=headers_b,
    )
    assert inbox_b.status_code == 200
    assert len(inbox_b.json()) == 0

    # User B checks unread counts
    counts_b = await client.get("/api/v1/messages/unread-counts", headers=headers_b)
    assert counts_b.status_code == 200
    assert counts_b.json()["pending_requests_count"] == 1

    # User B accepts the request
    accept_res = await client.post(
        f"/api/v1/messages/conversations/{conv_id}/accept",
        headers=headers_b,
    )
    assert accept_res.status_code == 200, accept_res.text
    assert accept_res.json()["status"] == "ACCEPTED"

    # Now User B's inbox contains the conversation
    inbox_b_after = await client.get(
        "/api/v1/messages/conversations?folder=inbox",
        headers=headers_b,
    )
    assert inbox_b_after.status_code == 200
    assert len(inbox_b_after.json()) == 1

    # User B replies to User A
    reply_res = await client.post(
        "/api/v1/messages/send",
        json={
            "recipient_id": user_a_id,
            "content": "Thanks for reaching out! Delighted to connect.",
        },
        headers=headers_b,
    )
    assert reply_res.status_code == 201

    # User A opens the conversation detail (should return both messages and mark incoming read)
    thread_res = await client.get(
        f"/api/v1/messages/conversations/{conv_id}",
        headers=headers_a,
    )
    assert thread_res.status_code == 200, thread_res.text
    thread = thread_res.json()
    assert len(thread["messages"]) == 2
    assert thread["messages"][0]["content"] == "Hello! I saw your profile and would love to collaborate on open skills."
    assert thread["messages"][1]["content"] == "Thanks for reaching out! Delighted to connect."

    # 7. Test Public Profile for User A
    # Own profile: includes email according to privacy rules
    pub_res_self = await client.get(
        f"/api/v1/users/public/@{u_a_username}",
        headers=headers_a,
    )
    assert pub_res_self.status_code == 200, pub_res_self.text
    pub_self_profile = pub_res_self.json()
    assert pub_self_profile["name"] == "Aarav Sharma"
    assert pub_self_profile["headline"] == "Lead Full-Stack Systems Engineer"
    assert pub_self_profile["location"] == "New Delhi, India"
    assert pub_self_profile["email"] == u_a_email
    assert pub_self_profile["avatar"] == avatar_url
    assert pub_self_profile["is_self"] is True

    # Other user viewing profile: sensitive email is stripped according to privacy rules
    pub_res = await client.get(
        f"/api/v1/users/public/@{u_a_username}",
        headers=headers_b,
    )
    assert pub_res.status_code == 200, pub_res.text
    pub_profile = pub_res.json()
    assert pub_profile["name"] == "Aarav Sharma"
    assert pub_profile["headline"] == "Lead Full-Stack Systems Engineer"
    assert pub_profile["location"] == "New Delhi, India"
    assert "email" not in pub_profile or pub_profile.get("email") is None
    assert pub_profile["avatar"] == avatar_url
    assert pub_profile["followers_count"] == 0  # User B is not following A
    assert pub_profile["is_self"] is False
    assert "employer_details" not in pub_profile or pub_profile.get("employer_details") is None
    assert len(pub_profile["candidate_details"]["education"]) == 1
    assert len(pub_profile["candidate_details"]["experience"]) == 1
    assert len(pub_profile["candidate_details"]["projects"]) == 1
