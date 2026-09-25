from uuid import uuid4

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.services.mfa_service import MFAService


def test_password_hashing():
    password = "SkillVistaar@123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password(
        "WrongPassword@123",
        hashed,
    )


def test_password_strength():
    validate_password_strength(
        "SkillVistaar@123"
    )

    with pytest.raises(ValueError):
        validate_password_strength("weak")

    with pytest.raises(ValueError):
        validate_password_strength("password123")

    with pytest.raises(ValueError):
        validate_password_strength("PASSWORD123")

    with pytest.raises(ValueError):
        validate_password_strength("PasswordOnly")


def test_access_token():
    user_id = uuid4()

    token = create_access_token(user_id)

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token():
    user_id = uuid4()

    token = create_refresh_token(user_id)

    payload = decode_refresh_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_access_token_cannot_be_used_as_refresh_token():
    user_id = uuid4()

    access_token = create_access_token(user_id)

    with pytest.raises(JWTError):
        decode_refresh_token(access_token)


def test_refresh_token_cannot_be_used_as_access_token():
    user_id = uuid4()

    refresh_token = create_refresh_token(user_id)

    with pytest.raises(JWTError):
        decode_access_token(refresh_token)


def test_mfa_secret_generation():
    secret = MFAService.generate_secret()

    assert secret
    assert len(secret) >= 16


def test_mfa_provisioning_uri():
    secret = MFAService.generate_secret()

    uri = MFAService.generate_provisioning_uri(
        "test@skillvistaar.local",
        secret,
    )

    assert uri.startswith("otpauth://")
    assert "SkillVistaar" in uri