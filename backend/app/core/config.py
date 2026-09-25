from functools import lru_cache
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve backend/.env from the location of this file (backend/app/core/config.py)
_ENV_FILE = str(Path(__file__).resolve().parent.parent.parent / ".env")

# Patterns that indicate a placeholder/dev secret — never safe for production.
_UNSAFE_SECRET_PATTERNS = re.compile(
    r"(CHANGE_ME|12345|placeholder|example|insecure|xxxxxxx)",
    re.IGNORECASE,
)


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables and the .env file.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================
    # Application
    # =========================================================

    PROJECT_NAME: str = "SkillVistaar"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # =========================================================
    # Server
    # =========================================================

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # =========================================================
    # Database
    # =========================================================

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "skillvistaar"
    POSTGRES_USER: str = "skillvistaar"
    POSTGRES_PASSWORD: str = ""

    # Optional complete database URL.
    # If provided, it takes priority over the individual
    # PostgreSQL settings above.
    DATABASE_URL: str = ""

    # =========================================================
    # JWT / Authentication
    # =========================================================

    JWT_SECRET_KEY: str = ""
    JWT_REFRESH_SECRET_KEY: str = ""

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    JWT_ALGORITHM: str = "HS256"

    # =========================================================
    # CORS
    # =========================================================

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator(
        "CORS_ORIGINS",
        mode="before",
    )
    @classmethod
    def parse_cors_origins(cls, value):
        """
        Supports both:

        JSON:
        ["http://localhost:5173", "http://127.0.0.1:5173"]

        Comma-separated:
        http://localhost:5173,http://127.0.0.1:5173
        """

        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(origin).strip()
                for origin in value
                if str(origin).strip()
            ]

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return []

            # First try JSON format.
            if value.startswith("["):
                try:
                    parsed = json.loads(value)

                    if isinstance(parsed, list):
                        return [
                            str(origin).strip()
                            for origin in parsed
                            if str(origin).strip()
                        ]
                except json.JSONDecodeError:
                    pass

            # Fall back to comma-separated format.
            return [
                origin.strip().strip('"').strip("'")
                for origin in value.split(",")
                if origin.strip()
            ]

        return []

    # =========================================================
    # Redis
    # =========================================================

    REDIS_URL: str = "redis://localhost:6379/0"

    # =========================================================
    # Storage (Local, S3, Cloudflare R2, Supabase)
    # =========================================================

    STORAGE_ROOT: str = "./storage"
    STORAGE_BACKEND: str = "local"  # "local" | "s3" | "r2" | "supabase"
    STORAGE_S3_ENDPOINT_URL: str = ""  # e.g. https://<account_id>.r2.cloudflarestorage.com
    STORAGE_S3_BUCKET_NAME: str = ""
    STORAGE_S3_ACCESS_KEY_ID: str = ""
    STORAGE_S3_SECRET_ACCESS_KEY: str = ""
    STORAGE_S3_REGION: str = "auto"
    STORAGE_S3_PUBLIC_URL_PREFIX: str = ""

    MAX_UPLOAD_SIZE_MB: int = 10

    # =========================================================
    # Email
    # =========================================================

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "SkillVistaar Portal"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT: int = 15
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_RESENDS: int = 3
    OTP_EXPIRY_MINUTES: int = 10
    TESTING: bool = False

    # =========================================================
    # SMS
    # =========================================================

    SMS_PROVIDER: str = "sandbox"
    SMS_API_KEY: str = ""
    SMS_SENDER_ID: str = ""
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    ALLOW_DEMO_SMS: bool = True

    # =========================================================
    # Blockchain
    # =========================================================

    BLOCKCHAIN_ENABLED: bool = False
    BLOCKCHAIN_RPC_URL: str = ""
    BLOCKCHAIN_NETWORK_ID: str = ""
    BLOCKCHAIN_PRIVATE_KEY: str = ""
    BLOCKCHAIN_CONTRACT_ADDRESS: str = ""

    # =========================================================
    # AI
    # =========================================================

    AI_ENABLED: bool = True
    AI_PROVIDER: str = ""
    AI_API_KEY: str = ""

    # =========================================================
    # Security
    # =========================================================

    PASSWORD_MIN_LENGTH: int = 8

    MAX_LOGIN_ATTEMPTS: int = 5

    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # =========================================================
    # MFA
    # =========================================================

    MFA_ISSUER: str = "SkillVistaar"

    # =========================================================
    # Logging
    # =========================================================

    LOG_LEVEL: str = "INFO"

    # =========================================================
    # Production Safety Validation
    # =========================================================

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """
        Prevent accidental production deployment without real secrets.
        """
        is_prod = self.ENVIRONMENT.lower() in ("production", "prod")

        if is_prod:
            # Force debug off in production.
            object.__setattr__(self, "DEBUG", False)

            for field_name in ("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY"):
                value = getattr(self, field_name, "")
                if not value or len(value) < 32:
                    raise ValueError(
                        f"{field_name} must be at least 32 characters in production. "
                        f"Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                    )
                if _UNSAFE_SECRET_PATTERNS.search(value):
                    raise ValueError(
                        f"{field_name} contains a placeholder pattern and is not safe for production."
                    )

        return self

    # =========================================================
    # Derived database URL
    # =========================================================

    @property
    def database_url_async(self) -> str:
        """
        Return the async PostgreSQL database URL.

        DATABASE_URL takes priority when configured.
        Otherwise the URL is constructed from PostgreSQL settings.
        Handles automatic normalization for cloud providers (Neon, Render, Supabase)
        by ensuring postgresql+asyncpg driver and converting libpq query params (sslmode)
        to asyncpg-compatible options (ssl=require).
        """

        if self.DATABASE_URL:
            raw = self.DATABASE_URL.strip()
            # Normalize scheme to postgresql+asyncpg://
            if raw.startswith("postgres://"):
                raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
            elif raw.startswith("postgresql://") and not raw.startswith("postgresql+asyncpg://"):
                raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

            parsed = urlparse(raw)
            if parsed.query:
                query_params = parse_qs(parsed.query)

                # Convert libpq sslmode to asyncpg ssl
                if "sslmode" in query_params:
                    sslmode_vals = query_params.pop("sslmode")
                    mode = sslmode_vals[0].lower() if sslmode_vals else "require"
                    if mode in ("require", "prefer", "verify-ca", "verify-full"):
                        query_params["ssl"] = ["require"]
                    elif mode == "disable":
                        query_params.pop("ssl", None)

                # Strip unsupported asyncpg parameters (e.g. channel_binding from Neon)
                query_params.pop("channel_binding", None)

                new_query = urlencode(query_params, doseq=True)
                raw = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                ))

            return raw

        return (
            "postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    # =========================================================
    # Security compatibility properties
    # =========================================================
    #
    # These properties keep the rest of the application clean.
    # Existing security code can use settings.SECRET_KEY,
    # settings.REFRESH_SECRET_KEY, etc., without duplicating
    # configuration values.
    # =========================================================

    @property
    def SECRET_KEY(self) -> str:
        """
        Access-token signing secret.
        """

        return self.JWT_SECRET_KEY

    @property
    def REFRESH_SECRET_KEY(self) -> str:
        """
        Refresh-token signing secret.
        """

        return self.JWT_REFRESH_SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        """
        JWT signing algorithm.
        """

        return self.JWT_ALGORITHM

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """
        Access-token lifetime in minutes.
        """

        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        """
        Refresh-token lifetime in days.
        """

        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached application settings instance.
    """

    return Settings()


settings = get_settings()