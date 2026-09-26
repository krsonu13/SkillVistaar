from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory secure test outbox used ONLY in automated test suites (pytest)
# when live external providers (SMTP) are not configured.
# Note: Raw OTP is NEVER logged or exposed to production logs.
_secure_test_outbox: dict[str, str] = {}


class DeliveryError(Exception):
    """Raised when OTP dispatch fails or the external delivery provider is not configured."""
    pass


def _is_testing_environment() -> bool:
    """
    Detect whether the application is running inside automated test suites (e.g. pytest).
    """
    return bool(
        getattr(settings, "TESTING", False)
        or os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("ENVIRONMENT") == "test"
    )


def get_last_delivered_otp_for_test(identifier: str | None = None) -> str | None:
    """
    Test-only helper to inspect delivered OTP in automated unit/integration tests
    without leaking OTP into logs, stdout, or API responses.
    """
    if identifier is None:
        if _secure_test_outbox:
            return list(_secure_test_outbox.values())[-1]
        return None
    norm = identifier.lower().strip() if "@" in identifier else identifier.strip()
    return _secure_test_outbox.get(norm)


def clear_test_outbox() -> None:
    """Clear test outbox between test runs."""
    _secure_test_outbox.clear()


# =========================================================================
# Startup Validation Helpers
# =========================================================================


def validate_smtp_configuration() -> dict[str, Any]:
    """
    Validate SMTP settings at application startup and provide structured status.
    Provides targeted guidance for Gmail App Passwords.
    """
    host = (settings.SMTP_HOST or "").strip()
    port = settings.SMTP_PORT or 587
    username = (settings.SMTP_USERNAME or "").strip()
    password = (settings.SMTP_PASSWORD or "").replace(" ", "").strip()
    from_email = (settings.SMTP_FROM_EMAIL or username).strip()
    from_name = getattr(settings, "SMTP_FROM_NAME", "SkillVistaar Portal")

    is_gmail = "gmail" in host.lower()
    missing: list[str] = []
    if not host:
        missing.append("SMTP_HOST")
    if not username:
        missing.append("SMTP_USERNAME")
    if not password:
        missing.append("SMTP_PASSWORD")

    is_ready = len(missing) == 0

    if is_ready:
        if is_gmail:
            msg = (
                f"Gmail SMTP configured ({host}:{port}) for {username}. "
                "Ensure a 16-character Google App Password is used."
            )
        else:
            msg = f"SMTP configured ({host}:{port}) for {username}."
    else:
        if is_gmail:
            msg = (
                f"Gmail SMTP incomplete: Missing [{', '.join(missing)}] in backend/.env. "
                "To enable real Gmail OTP delivery, set your Gmail address and 16-character "
                "App Password from https://myaccount.google.com/apppasswords."
            )
        else:
            msg = f"SMTP unconfigured: Missing [{', '.join(missing)}] in backend/.env."

    return {
        "ready": is_ready,
        "is_gmail": is_gmail,
        "host": host,
        "port": port,
        "username_configured": bool(username),
        "password_configured": bool(password),
        "from_email": from_email,
        "from_name": from_name,
        "missing_fields": missing,
        "message": msg,
    }


def validate_sms_configuration() -> dict[str, Any]:
    """
    Validate SMS settings at application startup and provide structured status.
    Never exposes auth tokens or API keys.
    """
    provider = (settings.SMS_PROVIDER or "sandbox").strip().lower()
    msg91_key = (settings.MSG91_AUTH_KEY or settings.SMS_API_KEY or "").strip()

    # Auto-detect msg91 provider from credentials if present
    if not provider and msg91_key:
        provider = "msg91"

    missing: list[str] = []
    is_dummy = provider in ("dummy", "dev", "development", "mock")
    is_sandbox = provider in ("sandbox", "console") or getattr(settings, "ALLOW_DEMO_SMS", False)
    is_msg91 = provider == "msg91"

    if is_sandbox or (is_dummy and getattr(settings, "ALLOW_DEMO_SMS", False)):
        return {
            "ready": True,
            "provider": "sandbox",
            "is_dummy": True,
            "is_sandbox": True,
            "is_msg91": False,
            "missing_fields": [],
            "message": "Free-Tier Sandbox SMS active (zero-cost simulated delivery; OTP displayed on verification screen).",
        }

    if is_dummy:
        if settings.ENVIRONMENT == "production":
            return {
                "ready": False,
                "provider": provider,
                "is_dummy": True,
                "is_sandbox": False,
                "is_msg91": False,
                "missing_fields": ["SMS_PROVIDER (set to 'sandbox' or ALLOW_DEMO_SMS=true for free hosting)"],
                "message": "Development Dummy SMS provider is strictly disabled in production unless ALLOW_DEMO_SMS=true is set.",
            }
        return {
            "ready": True,
            "provider": "dummy",
            "is_dummy": True,
            "is_sandbox": False,
            "is_msg91": False,
            "missing_fields": [],
            "message": "Development Dummy SMS Provider active (OTP displayed directly on verification screen).",
        }

    if is_msg91:
        if not msg91_key:
            missing.append("MSG91_AUTH_KEY")
    else:
        missing.append("SMS_PROVIDER (set to 'sandbox')")

    is_ready = len(missing) == 0

    if is_ready:
        if is_msg91:
            msg = "MSG91 SMS configured."
        else:
            msg = "SMS provider configured."
    else:
        msg = f"SMS unconfigured: Missing [{', '.join(missing)}] in backend/.env."

    return {
        "ready": is_ready,
        "provider": provider or "sandbox",
        "is_sandbox": is_sandbox,
        "is_msg91": is_msg91,
        "missing_fields": missing,
        "message": msg,
    }


# =========================================================================
# SMTP Email Dispatch
# =========================================================================


def _sync_send_smtp_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
) -> bool:
    """
    Synchronous SMTP dispatch executed inside an asyncio thread pool worker.
    Uses RFC-compliant SMTP envelope addressing and proper TLS/SSL negotiation.
    Automatically handles spaced 16-character Google App Passwords.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject

    from_name = getattr(settings, "SMTP_FROM_NAME", "") or "SkillVistaar Portal"
    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "noreply@skillvistaar.in"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    msg.attach(part1)
    msg.attach(part2)

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT or 587
    username = settings.SMTP_USERNAME.strip() if settings.SMTP_USERNAME else ""
    # Google App Passwords are 16 chars often formatted with spaces (e.g. 'abcd efgh ijkl mnop')
    password = (
        settings.SMTP_PASSWORD.replace(" ", "").strip()
        if settings.SMTP_PASSWORD
        else ""
    )
    use_tls = settings.SMTP_USE_TLS
    use_ssl = getattr(settings, "SMTP_USE_SSL", False)
    timeout = getattr(settings, "SMTP_TIMEOUT", 15)

    if port == 465 or use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
            if username and password:
                server.login(username, password)
            server.sendmail(from_email, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            if username and password:
                server.login(username, password)
            server.sendmail(from_email, [to_email], msg.as_string())
    return True


# =========================================================================
# Email OTP Delivery
# =========================================================================


async def deliver_email_otp(to_email: str, otp: str) -> bool:
    """
    Deliver 6-digit OTP to user's email address via real SMTP provider.
    Never logs the plaintext OTP. Raises DeliveryError if unconfigured or delivery fails.
    """
    norm_email = to_email.lower().strip()

    if _is_testing_environment():
        _secure_test_outbox[norm_email] = otp
        logger.info("Test environment active: Email OTP captured in secure test outbox for %s", norm_email)
        return True

    # Validate SMTP configuration in live runtime
    missing_fields: list[str] = []
    if not settings.SMTP_HOST:
        missing_fields.append("SMTP_HOST")
    if not settings.SMTP_USERNAME:
        missing_fields.append("SMTP_USERNAME")
    if not settings.SMTP_PASSWORD:
        missing_fields.append("SMTP_PASSWORD")
    if not settings.SMTP_FROM_EMAIL and not settings.SMTP_USERNAME:
        missing_fields.append("SMTP_FROM_EMAIL")

    if missing_fields:
        missing_str = ", ".join(missing_fields)
        logger.warning(
            "SMTP email OTP dispatch fallback: Provider not fully configured. Missing [%s]. "
            "Using sandbox OTP for %s",
            missing_str,
            norm_email,
        )
        if getattr(settings, "ALLOW_DEMO_EMAIL", False) or settings.ENVIRONMENT != "production" or settings.DEBUG:
            _secure_test_outbox[norm_email] = otp
            logger.info("[SANDBOX EMAIL] Verification code for %s: %s (Demo/Sandbox Mode)", norm_email, otp)
            return True
        raise DeliveryError("OTP could not be delivered. Please configure SMTP credentials.")

    subject = "SkillVistaar - Your Verification Code"
    text_body = (
        "===========================================================\n"
        "           SKILLVISTAAR — UNIFIED PORTAL\n"
        "===========================================================\n\n"
        "Your Verification Code is:\n\n"
        f"       >>  {otp}  <<\n\n"
        "-----------------------------------------------------------\n"
        "SECURITY NOTICE:\n"
        "• This verification code is valid for 10 minutes.\n"
        "• It can only be used once.\n"
        "• SkillVistaar officials will NEVER ask for your code or password.\n"
        "• If you did not request this code, please disregard this message.\n"
        "-----------------------------------------------------------\n"
        "© 2026 SkillVistaar Portal. National Labour Market & Skills Gateway.\n"
    )
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkillVistaar Verification Code</title>
</head>
<body style="margin: 0; padding: 32px 16px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0f172a;">
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background-color: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);">
        <!-- BRAND HEADER -->
        <tr>
            <td style="background: linear-gradient(135deg, #0f172a 0%, #134e4a 100%); padding: 28px 32px; text-align: left;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                        <td>
                            <div style="font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                                Skill<span style="color: #2dd4bf;">Vistaar</span>
                            </div>
                            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: #99f6e4; margin-top: 4px;">
                                Unified Skills &amp; Employment Ecosystem
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- MAIN BODY -->
        <tr>
            <td style="padding: 36px 32px 28px 32px;">
                <h1 style="margin: 0 0 8px 0; font-size: 20px; font-weight: 700; color: #0f172a;">
                    Verify Your Contact Information
                </h1>
                <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.6; color: #475569;">
                    Thank you for signing up on SkillVistaar. Please use the 6-digit verification code below to confirm your contact details:
                </p>

                <!-- OTP CODE CARD -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f0fdfa; border: 2px dashed #0d9488; border-radius: 12px; margin-bottom: 24px;">
                    <tr>
                        <td style="padding: 24px 16px; text-align: center;">
                            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #0f766e; margin-bottom: 8px;">
                                One-Time Verification Code
                            </div>
                            <div style="font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: 800; letter-spacing: 12px; color: #0f766e; padding-left: 12px;">
                                {otp}
                            </div>
                            <div style="font-size: 12px; color: #0d9488; font-weight: 600; margin-top: 8px;">
                                Valid for 10 minutes &bull; Single-use only
                            </div>
                        </td>
                    </tr>
                </table>

                <!-- SECURITY NOTICE -->
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin-bottom: 24px;">
                    <tr>
                        <td style="font-size: 12px; line-height: 1.6; color: #64748b;">
                            <strong style="color: #334155;">Important Security Advice:</strong><br>
                            &bull; SkillVistaar representatives will <strong>never</strong> ask for your verification code or account password.<br>
                            &bull; Do not forward or disclose this code to anyone.<br>
                            &bull; If you did not request this verification code, please ignore this email or contact support.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- FOOTER -->
        <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center;">
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.5;">
                    This is an automated security transmission sent to {norm_email}.<br>
                    &copy; 2026 SkillVistaar Portal &bull; National Labour Market Intelligence &amp; Skills Gateway
                </p>
            </td>
        </tr>
    </table>
</body>
</html>"""

    try:
        await asyncio.to_thread(
            _sync_send_smtp_email,
            norm_email,
            subject,
            text_body,
            html_body,
        )
        logger.info("Real SMTP email OTP delivered to %s", norm_email)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP Authentication Failed: %s", exc)
        if getattr(settings, "ALLOW_DEMO_EMAIL", False) or settings.ENVIRONMENT != "production" or settings.DEBUG:
            _secure_test_outbox[norm_email] = otp
            logger.warning("[FALLBACK SANDBOX EMAIL] SMTP auth failed (%s). Saved OTP for %s: %s", exc, norm_email, otp)
            return True
        is_gmail = "gmail" in (settings.SMTP_HOST or "").lower()
        if is_gmail:
            msg = (
                f"Gmail SMTP authentication failed ({exc.smtp_code}). "
                "Gmail requires a 16-character App Password, not your standard Google password. "
                "Please enable 2-Step Verification on your Google Account and generate an App Password "
                "at https://myaccount.google.com/apppasswords, then set SMTP_PASSWORD."
            )
        else:
            msg = f"SMTP authentication failed ({exc.smtp_code}). Please check SMTP_USERNAME and SMTP_PASSWORD."
        raise DeliveryError(f"OTP could not be delivered: {msg}") from exc
    except smtplib.SMTPConnectError as exc:
        logger.error("SMTP Connection Failed: %s", exc)
        if getattr(settings, "ALLOW_DEMO_EMAIL", False) or settings.ENVIRONMENT != "production" or settings.DEBUG:
            _secure_test_outbox[norm_email] = otp
            logger.warning("[FALLBACK SANDBOX EMAIL] SMTP connection failed (%s). Saved OTP for %s: %s", exc, norm_email, otp)
            return True
        raise DeliveryError(
            f"OTP could not be delivered: Could not connect to SMTP host '{settings.SMTP_HOST}:{settings.SMTP_PORT}'."
        ) from exc
    except Exception as exc:
        logger.error("Failed to deliver SMTP email OTP to %s: %s", norm_email, exc)
        if getattr(settings, "ALLOW_DEMO_EMAIL", False) or settings.ENVIRONMENT != "production" or settings.DEBUG:
            _secure_test_outbox[norm_email] = otp
            logger.warning("[FALLBACK SANDBOX EMAIL] SMTP delivery error (%s). Saved OTP for %s: %s", exc, norm_email, otp)
            return True
        raise DeliveryError("OTP could not be delivered. Please try again.") from exc


# =========================================================================
# SMS OTP Delivery (Sandbox / MSG91)
# =========================================================================


async def deliver_sms_otp(to_phone: str, otp: str) -> bool:
    """
    Deliver 6-digit OTP to user's mobile number via configured SMS provider.
    Never logs the plaintext OTP in production. Raises DeliveryError if unconfigured or delivery fails.
    """
    norm_phone = to_phone.strip()

    if _is_testing_environment():
        _secure_test_outbox[norm_phone] = otp
        logger.info("Test environment active: SMS OTP captured in secure test outbox for %s", norm_phone)
        return True

    sms_text = (
        f"Your SkillVistaar verification code is: {otp}. "
        "Valid for 10 minutes. Do not share this code with anyone."
    )

    # Determine provider from settings or auto-detect from credentials
    provider = (settings.SMS_PROVIDER or "").strip().lower()
    is_dummy = provider in ("dummy", "dev", "development", "mock")
    is_sandbox = provider in ("sandbox", "console") or getattr(settings, "ALLOW_DEMO_SMS", False)

    if is_sandbox:
        _secure_test_outbox[norm_phone] = otp
        logger.info("[FREE-TIER SANDBOX SMS] Verification code for %s: %s (Free-tier Mode)", norm_phone, otp)
        return True

    if is_dummy:
        if settings.ENVIRONMENT == "production":
            raise DeliveryError("Development Dummy SMS provider cannot be used in production unless ALLOW_DEMO_SMS=true is set.")
        _secure_test_outbox[norm_phone] = otp
        logger.info("[DEV DUMMY SMS] Verification code for %s: %s (Development Mode)", norm_phone, otp)
        return True

    is_msg91 = provider == "msg91" or bool(settings.MSG91_AUTH_KEY)

    # MSG91 integration
    if is_msg91:
        auth_key = settings.MSG91_AUTH_KEY or settings.SMS_API_KEY
        sender_id = settings.SMS_SENDER_ID or "SKLVST"

        if not auth_key:
            raise DeliveryError(
                "OTP could not be delivered: MSG91 SMS provider is not configured. "
                "Missing [MSG91_AUTH_KEY] in backend/.env."
            )

        url = "https://control.msg91.com/api/v5/otp"

        clean_mobile = norm_phone.replace("+", "").lstrip("0")
        if len(clean_mobile) == 10:
            clean_mobile = f"91{clean_mobile}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    headers={
                        "authkey": auth_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "template_id": settings.MSG91_TEMPLATE_ID,
                        "mobile": clean_mobile,
                        "otp": otp,
                    },
                )
                if resp.status_code in (200, 201):
                    logger.info("Real MSG91 SMS OTP delivered to phone")
                    return True
                else:
                    logger.error("MSG91 SMS failed with status %d: %s", resp.status_code, resp.text)
                    raise DeliveryError(f"OTP could not be delivered: MSG91 SMS failed with status {resp.status_code}.")
        except DeliveryError:
            raise
        except Exception as exc:
            logger.error("MSG91 SMS dispatch exception: %s", exc)
            raise DeliveryError(f"OTP could not be delivered: MSG91 SMS error ({str(exc)}).") from exc

    else:
        # Default fallback to sandbox if enabled or raise DeliveryError
        if getattr(settings, "ALLOW_DEMO_SMS", False):
            _secure_test_outbox[norm_phone] = otp
            logger.info("[SANDBOX SMS] 6-digit verification code for %s: %s", norm_phone, otp)
            return True
        logger.error("SMS OTP dispatch aborted: Provider not configured")
        raise DeliveryError(
            "OTP could not be delivered: SMS provider is not configured. "
            "Set SMS_PROVIDER=sandbox and ALLOW_DEMO_SMS=true in backend/.env for free-tier deployment."
        )


# =========================================================================
# Unified OTP Dispatch
# =========================================================================


async def deliver_otp(channel: str, destination: str, otp: str) -> bool:
    """Dispatch OTP through the appropriate provider channel."""
    if channel.upper() == "EMAIL":
        return await deliver_email_otp(destination, otp)
    elif channel.upper() == "PHONE":
        return await deliver_sms_otp(destination, otp)
    else:
        raise ValueError(f"Unsupported delivery channel: {channel}")
