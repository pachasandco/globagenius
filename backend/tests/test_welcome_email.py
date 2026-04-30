"""Tests for the welcome email transport.

Brevo template path is the primary one; SMTP is the fallback only used when
BREVO_API_KEY or BREVO_WELCOME_TEMPLATE_ID are not configured.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.notifications import welcome_email


@pytest.mark.asyncio
async def test_brevo_template_used_when_configured():
    """When BREVO_API_KEY + template ID are set, we POST to Brevo's transactional API."""
    with patch.object(welcome_email.settings, "BREVO_API_KEY", "xkeysib-test"), \
         patch.object(welcome_email.settings, "BREVO_WELCOME_TEMPLATE_ID", 42), \
         patch.object(welcome_email.settings, "BREVO_SENDER_EMAIL", "contact@globegenius.app"), \
         patch.object(welcome_email.settings, "BREVO_SENDER_NAME", "Globe Genius"):

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.notifications.welcome_email.httpx.AsyncClient", return_value=mock_client):
            await welcome_email.send_welcome_email("user@example.com", prenom="Moussa")

        mock_client.post.assert_awaited_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == welcome_email.BREVO_API_URL
        payload = kwargs["json"]
        assert payload["to"] == [{"email": "user@example.com"}]
        assert payload["templateId"] == 42
        assert payload["params"] == {"PRENOM": "Moussa"}
        assert payload["sender"]["email"] == "contact@globegenius.app"
        assert kwargs["headers"]["api-key"] == "xkeysib-test"


@pytest.mark.asyncio
async def test_default_prenom_when_none_passed():
    """When no prenom is provided, the template should receive 'toi' as default."""
    with patch.object(welcome_email.settings, "BREVO_API_KEY", "xkeysib-test"), \
         patch.object(welcome_email.settings, "BREVO_WELCOME_TEMPLATE_ID", 42):

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.notifications.welcome_email.httpx.AsyncClient", return_value=mock_client):
            await welcome_email.send_welcome_email("user@example.com")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["params"] == {"PRENOM": "toi"}


@pytest.mark.asyncio
async def test_smtp_fallback_when_brevo_not_configured():
    """When BREVO_API_KEY is empty, fall back to SMTP."""
    with patch.object(welcome_email.settings, "BREVO_API_KEY", ""), \
         patch.object(welcome_email.settings, "BREVO_WELCOME_TEMPLATE_ID", 0), \
         patch.object(welcome_email.settings, "SMTP_HOST", "smtp-relay.brevo.com"), \
         patch.object(welcome_email.settings, "SMTP_USER", "user@example.com"), \
         patch.object(welcome_email.settings, "SMTP_PASS", "secret"), \
         patch.object(welcome_email.settings, "SMTP_PORT", 587):

        with patch("aiosmtplib.send", new=AsyncMock()) as mock_send:
            await welcome_email.send_welcome_email("user@example.com")

        mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_transport_configured_is_silent_noop():
    """If neither Brevo nor SMTP is set, signup must not crash."""
    with patch.object(welcome_email.settings, "BREVO_API_KEY", ""), \
         patch.object(welcome_email.settings, "BREVO_WELCOME_TEMPLATE_ID", 0), \
         patch.object(welcome_email.settings, "SMTP_HOST", ""), \
         patch.object(welcome_email.settings, "SMTP_USER", ""):
        # Should not raise.
        await welcome_email.send_welcome_email("user@example.com")


@pytest.mark.asyncio
async def test_brevo_failure_falls_back_to_smtp():
    """If Brevo API raises, the SMTP fallback must run so the user still gets something."""
    with patch.object(welcome_email.settings, "BREVO_API_KEY", "xkeysib-test"), \
         patch.object(welcome_email.settings, "BREVO_WELCOME_TEMPLATE_ID", 42), \
         patch.object(welcome_email.settings, "SMTP_HOST", "smtp-relay.brevo.com"), \
         patch.object(welcome_email.settings, "SMTP_USER", "user@example.com"), \
         patch.object(welcome_email.settings, "SMTP_PASS", "secret"), \
         patch.object(welcome_email.settings, "SMTP_PORT", 587):

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.notifications.welcome_email.httpx.AsyncClient", return_value=mock_client), \
             patch("aiosmtplib.send", new=AsyncMock()) as mock_smtp:
            await welcome_email.send_welcome_email("user@example.com")

        mock_smtp.assert_awaited_once()
