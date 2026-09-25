from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator


class VerificationChannel(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"


class VerificationPurpose(str, Enum):
    SIGNUP = "SIGNUP"


class RequestVerificationCode(BaseModel):
    channel: VerificationChannel
    purpose: VerificationPurpose = VerificationPurpose.SIGNUP


class RequestVerificationResponse(BaseModel):
    message: str
    channel: VerificationChannel
    expires_in_seconds: int
    dev_otp: str | None = None


class VerifyVerificationCode(BaseModel):
    channel: VerificationChannel
    otp: str = Field(min_length=6, max_length=6)
    purpose: VerificationPurpose = VerificationPurpose.SIGNUP

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("OTP must contain only digits.")
        if len(value) != 6:
            raise ValueError("OTP must be exactly 6 digits.")
        return value


class VerifyVerificationResponse(BaseModel):
    message: str
    email_verified: bool
    phone_verified: bool
    verification_complete: bool


# =========================================================================
# Sequential Dual-Contact Signup Schemas
# =========================================================================

class StartSignupVerificationRequest(BaseModel):
    account_type: str = Field(..., description="CANDIDATE, EMPLOYER, TRAINING_INSTITUTE, GOVERNMENT")
    channel: str = Field(..., description="EMAIL or PHONE")
    identifier: str = Field(..., description="Email address or mobile phone number")


class StartSignupVerificationResponse(BaseModel):
    session_token: str
    channel: str
    identifier: str
    expires_in_seconds: int
    message: str
    dev_otp: str | None = None


class VerifySignupOtpRequest(BaseModel):
    session_token: str
    otp: str = Field(min_length=6, max_length=6)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("OTP must contain only digits.")
        if len(value) != 6:
            raise ValueError("OTP must be exactly 6 digits.")
        return value


class VerifyPrimaryResponse(BaseModel):
    session_token: str
    primary_verified: bool
    primary_channel: str
    next_channel: str
    message: str


class SendSecondaryOtpRequest(BaseModel):
    session_token: str
    channel: str = Field(..., description="EMAIL or PHONE")
    identifier: str = Field(..., description="The alternate contact")


class SendSecondaryOtpResponse(BaseModel):
    session_token: str
    channel: str
    identifier: str
    expires_in_seconds: int
    message: str
    dev_otp: str | None = None


class VerifySecondaryResponse(BaseModel):
    session_token: str
    both_verified: bool
    message: str


class CompleteSignupRequest(BaseModel):
    session_token: str
    password: str = Field(min_length=8)
    terms_accepted: bool
    additional_data: dict[str, Any] = Field(default_factory=dict)
