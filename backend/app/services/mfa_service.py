import pyotp

from app.core.config import settings


class MFAService:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def generate_provisioning_uri(
        email: str,
        secret: str,
    ) -> str:
        return pyotp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=settings.MFA_ISSUER,
        )

    @staticmethod
    def verify_code(
        secret: str,
        code: str,
    ) -> bool:
        if not secret or not code:
            return False

        return pyotp.TOTP(secret).verify(
            code,
            valid_window=1,
        )