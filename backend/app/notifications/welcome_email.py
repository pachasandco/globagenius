import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def _send_via_brevo_template(to_email: str, prenom: str | None) -> bool:
    """Send welcome email via Brevo transactional API using the template ID.

    Returns True on success, False if Brevo path can't be used (falls back to SMTP).
    """
    if not settings.BREVO_API_KEY or not settings.BREVO_WELCOME_TEMPLATE_ID:
        return False

    payload = {
        "to": [{"email": to_email}],
        "templateId": settings.BREVO_WELCOME_TEMPLATE_ID,
        "params": {"PRENOM": prenom or "toi"},
        "sender": {
            "email": settings.BREVO_SENDER_EMAIL,
            "name": settings.BREVO_SENDER_NAME,
        },
    }
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(BREVO_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        logger.info(f"Welcome email (Brevo template {settings.BREVO_WELCOME_TEMPLATE_ID}) sent to {to_email}")
        return True


async def _send_via_smtp_fallback(to_email: str) -> None:
    """Legacy SMTP fallback for environments without Brevo API configured.

    Sends a minimal plain-text welcome so the signup flow still gives feedback.
    The rich HTML version lives in the Brevo template.
    """
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_host or not smtp_user:
        logger.info(f"No email transport configured, skipping welcome email to {to_email}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Bienvenue sur Globe Genius ! ✈️"
    msg["From"] = f"Globe Genius <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(
        "Bienvenue sur Globe Genius ! Ton compte est créé. "
        "Connecte ton Telegram depuis ton profil pour recevoir les alertes : "
        "https://globegenius.app/profile",
        "plain",
    ))

    try:
        import aiosmtplib
        send_kwargs = dict(
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
        )
        if smtp_port == 465:
            send_kwargs["use_tls"] = True
        else:
            send_kwargs["start_tls"] = True
        await aiosmtplib.send(msg, **send_kwargs)
        logger.info(f"Welcome email (SMTP fallback) sent to {to_email}")
    except Exception as e:
        logger.error(f"SMTP fallback failed for {to_email}: {e}")


async def send_welcome_email(to_email: str, prenom: str | None = None):
    """Send welcome email to a new user.

    Primary path: Brevo transactional API with template (BREVO_WELCOME_TEMPLATE_ID).
    Fallback: plain-text SMTP — the rich design only lives in the Brevo template.
    """
    try:
        sent = await _send_via_brevo_template(to_email, prenom)
        if sent:
            return
    except Exception as e:
        logger.error(f"Brevo template send failed for {to_email}, falling back to SMTP: {e}")

    await _send_via_smtp_fallback(to_email)
