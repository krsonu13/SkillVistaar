import pytest
from unittest.mock import patch
from app.services.otp_delivery_service import (
    deliver_email_otp,
    deliver_sms_otp,
    DeliveryError,
    get_last_delivered_otp_for_test,
    clear_test_outbox,
)
from app.core.config import settings

@pytest.mark.asyncio
async def test_email_otp_test_environment_captures_in_outbox():
    clear_test_outbox()
    email = "candidate.real@example.com"
    otp = "849201"
    
    success = await deliver_email_otp(email, otp)
    assert success is True
    assert get_last_delivered_otp_for_test(email) == otp

@pytest.mark.asyncio
async def test_email_otp_unconfigured_raises_delivery_error_in_live_runtime():
    clear_test_outbox()
    email = "live.user@example.com"
    otp = "519382"
    
    # Simulate live runtime (non-testing) with missing SMTP_HOST
    with patch("app.services.otp_delivery_service._is_testing_environment", return_value=False):
        with patch.object(settings, "SMTP_HOST", ""):
            with pytest.raises(DeliveryError) as exc_info:
                await deliver_email_otp(email, otp)
            
            assert "OTP could not be delivered" in str(exc_info.value)
            assert "SMTP_HOST" in str(exc_info.value)

@pytest.mark.asyncio
async def test_sms_otp_unconfigured_raises_delivery_error_in_live_runtime():
    clear_test_outbox()
    phone = "+919876543210"
    otp = "638192"
    
    # Simulate live runtime (non-testing) with no SMS provider configured
    with patch("app.services.otp_delivery_service._is_testing_environment", return_value=False):
        with patch.object(settings, "SMS_PROVIDER", ""):
            with patch.object(settings, "ALLOW_DEMO_SMS", False):
                with patch.object(settings, "MSG91_AUTH_KEY", ""):
                    with pytest.raises(DeliveryError) as exc_info:
                        await deliver_sms_otp(phone, otp)
                    
                    assert "OTP could not be delivered" in str(exc_info.value)
                    assert "SMS provider is not configured" in str(exc_info.value)

@pytest.mark.asyncio
async def test_smtp_send_envelope_from_clean_email():
    """Verify _sync_send_smtp_email sends clean email in envelope, not RFC formatted name."""
    from app.services.otp_delivery_service import _sync_send_smtp_email
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value.__enter__.return_value
        with patch.object(settings, "SMTP_HOST", "smtp.test.com"):
            with patch.object(settings, "SMTP_PORT", 587):
                with patch.object(settings, "SMTP_FROM_EMAIL", "sender@domain.com"):
                    with patch.object(settings, "SMTP_FROM_NAME", "Test Sender"):
                        _sync_send_smtp_email(
                            "recipient@test.com",
                            "Subject",
                            "Text body",
                            "<html>HTML</html>",
                        )
                        # Envelope from must be "sender@domain.com", not "Test Sender <sender@domain.com>"
                        mock_server.sendmail.assert_called_once()
                        args, _kwargs = mock_server.sendmail.call_args
                        assert args[0] == "sender@domain.com"
                        assert args[1] == ["recipient@test.com"]

import smtplib
from app.services.otp_delivery_service import (
    validate_smtp_configuration,
    _sync_send_smtp_email,
)
from app.services.verification_service import ResendCooldownError

def test_validate_smtp_configuration_unconfigured():
    with patch.object(settings, "SMTP_HOST", "smtp.gmail.com"):
        with patch.object(settings, "SMTP_USERNAME", ""):
            with patch.object(settings, "SMTP_PASSWORD", ""):
                info = validate_smtp_configuration()
                assert info["ready"] is False
                assert info["is_gmail"] is True
                assert "SMTP_USERNAME" in info["missing_fields"]
                assert "SMTP_PASSWORD" in info["missing_fields"]
                assert "https://myaccount.google.com/apppasswords" in info["message"]

def test_validate_smtp_configuration_configured():
    with patch.object(settings, "SMTP_HOST", "smtp.gmail.com"):
        with patch.object(settings, "SMTP_PORT", 587):
            with patch.object(settings, "SMTP_USERNAME", "testuser@gmail.com"):
                with patch.object(settings, "SMTP_PASSWORD", "abcd efgh ijkl mnop"):
                    info = validate_smtp_configuration()
                    assert info["ready"] is True
                    assert info["is_gmail"] is True
                    assert info["username_configured"] is True
                    assert info["password_configured"] is True
                    assert len(info["missing_fields"]) == 0

def test_gmail_app_password_space_stripping():
    """Verify that 16-character spaced Google App Password has spaces stripped before login."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value.__enter__.return_value
        with patch.object(settings, "SMTP_HOST", "smtp.gmail.com"):
            with patch.object(settings, "SMTP_PORT", 587):
                with patch.object(settings, "SMTP_USERNAME", "myuser@gmail.com"):
                    with patch.object(settings, "SMTP_PASSWORD", "abcd efgh ijkl mnop"):
                        _sync_send_smtp_email(
                            "to@gmail.com",
                            "Subject",
                            "Text",
                            "<html></html>",
                        )
                        # The password passed to login must have spaces removed
                        mock_server.login.assert_called_once_with("myuser@gmail.com", "abcdefghijklmnop")

@pytest.mark.asyncio
async def test_gmail_535_auth_error_provides_app_password_advice():
    """Verify Gmail 535 authentication failure explains App Password requirement."""
    with patch("app.services.otp_delivery_service._is_testing_environment", return_value=False):
        with patch.object(settings, "SMTP_HOST", "smtp.gmail.com"):
            with patch.object(settings, "SMTP_USERNAME", "user@gmail.com"):
                with patch.object(settings, "SMTP_PASSWORD", "secret123"):
                    with patch("app.services.otp_delivery_service._sync_send_smtp_email", side_effect=smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")):
                        with pytest.raises(DeliveryError) as exc_info:
                            await deliver_email_otp("user@gmail.com", "123456")
                        
                        assert "App Password" in str(exc_info.value)
                        assert "myaccount.google.com/apppasswords" in str(exc_info.value)
