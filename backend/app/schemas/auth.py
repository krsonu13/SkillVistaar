from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class AccountType(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    GOVERNMENT = "GOVERNMENT"
    EMPLOYER = "EMPLOYER"
    TRAINING_INSTITUTE = "TRAINING_INSTITUTE"
    CANDIDATE = "CANDIDATE"


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr | None = None
    phone: str | None = None
    username: str | None = None
    password: str = Field(min_length=8, max_length=128)
    account_type: AccountType

    # Optional fields from frontend registration forms
    officialEmail: str | None = None
    contactPhone: str | None = None
    coordinatorPhone: str | None = None
    fullName: str | None = None
    companyName: str | None = None
    instituteName: str | None = None
    departmentName: str | None = None
    accountType: str | None = None

    @model_validator(mode="before")
    @classmethod
    def pre_normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("email") and data.get("officialEmail"):
                data["email"] = data["officialEmail"]
            if not data.get("phone"):
                data["phone"] = data.get("contactPhone") or data.get("coordinatorPhone")
            raw_acc = data.get("account_type") or data.get("accountType")
            if raw_acc:
                normalized = str(raw_acc).upper()
                if normalized == "INSTITUTE":
                    normalized = "TRAINING_INSTITUTE"
                elif normalized == "ADMIN":
                    normalized = "SUPER_ADMIN"
                data["account_type"] = normalized
        return data

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        if value is None:
            return None

        value = str(value).strip().lower()

        return value or None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Any) -> Any:
        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError(
                "Password must contain at least one uppercase letter."
            )

        if not any(char.islower() for char in value):
            raise ValueError(
                "Password must contain at least one lowercase letter."
            )

        if not any(char.isdigit() for char in value):
            raise ValueError(
                "Password must contain at least one digit."
            )

        return value

    def validate_contact_method(self) -> None:
        if not self.email and not self.phone:
            raise ValueError(
                "At least one of email or phone is required."
            )


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    token: str | None = None
    user: UserResponse | None = None
    success: bool = True
    message: str = "Authenticated successfully"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class SignupResponse(BaseModel):
    id: str
    account_type: AccountType
    email: EmailStr | None = None
    phone: str | None = None
    email_verified: bool
    phone_verified: bool

    # Short-lived token used only for account verification.
    verification_token: str | None = None

    message: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr | None = None
    phone: str | None = None
    username: str | None = None
    account_type: AccountType
    is_active: bool
    is_suspended: bool
    email_verified: bool
    phone_verified: bool
    verification_status: str = "PENDING"
    government_unit_id: str | None = None
    roles: list[str] = Field(default_factory=list)

    @field_validator("id", "government_unit_id", mode="before")
    @classmethod
    def convert_id_to_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


class OtpVerifyRequest(BaseModel):
    identifier: str = Field(min_length=1)
    otp: str = Field(min_length=4, max_length=10)
    accountType: str | None = None


class ResendOtpRequest(BaseModel):
    identifier: str = Field(min_length=1)
    accountType: str | None = None


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1)
    accountType: str | None = None