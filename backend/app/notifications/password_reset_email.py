"""V7: password reset email — Brevo SMTP via aiosmtplib.

Same transport as welcome_email.py: SMTP_HOST/PORT/USER/PASS env vars.
On Brevo: SMTP_HOST=smtp-relay.brevo.com, SMTP_PORT=587, SMTP_USER=login,
SMTP_PASS=BREVO_SMTP_KEY value.
"""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def _build_html(reset_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background:#FFF8F0; font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#FFF8F0; padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 8px rgba(10,31,61,0.06);">

          <tr>
            <td style="padding:32px 40px 16px; text-align:left;">
              <div style="font-size:14px; color:#0A1F3D; font-weight:600; letter-spacing:-0.2px;">
                Globe<span style="color:#FF6B47;">Genius</span>
              </div>
            </td>
          </tr>

          <tr>
            <td style="padding:0 40px 8px;">
              <h1 style="color:#0A1F3D; font-size:22px; margin:0 0 12px; font-weight:600;">
                Réinitialisation de votre mot de passe
              </h1>
              <p style="color:#0A1F3D; font-size:15px; line-height:1.6; margin:0 0 20px;">
                Vous avez demandé à réinitialiser votre mot de passe Globe Genius.
                Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe&nbsp;:
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding:0 40px 24px;">
              <a href="{reset_url}" style="display:inline-block; background:#FF6B47; color:#ffffff; font-size:15px; font-weight:600; padding:14px 28px; border-radius:12px; text-decoration:none;">
                Réinitialiser mon mot de passe
              </a>
            </td>
          </tr>

          <tr>
            <td style="padding:0 40px 24px;">
              <p style="color:#0A1F3D; font-size:13px; line-height:1.6; margin:0;">
                Ce lien est valable <strong>1 heure</strong>. Si vous n'avez pas demandé cette
                réinitialisation, ignorez simplement cet email — votre mot de passe ne sera pas modifié.
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding:20px 40px; background:#FFF8F0; border-top:1px solid #F0E6D8; text-align:center;">
              <p style="color:#0A1F3D; opacity:0.5; font-size:11px; margin:0;">
                Globe Genius — Vols à prix cassés au départ de la France
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""".strip()


def _build_text(reset_url: str) -> str:
    return (
        "Réinitialisation de votre mot de passe Globe Genius\n\n"
        "Vous avez demandé à réinitialiser votre mot de passe.\n"
        "Cliquez ou copiez le lien ci-dessous (valable 1 heure) :\n\n"
        f"{reset_url}\n\n"
        "Si vous n'avez pas fait cette demande, ignorez cet email."
    )


async def _send_via_brevo_api(to_email: str, reset_url: str) -> bool:
    """Primary transport: Brevo transactional HTTP API.

    2026-07-31 : Railway bloque les ports SMTP sortants (587/465) — le
    transport aiosmtplib pendait ~60s puis échouait, l'écran restait sur
    « envoi en cours » et AUCUN email de reset ne partait. Tous les
    autres emails de l'app passent déjà par l'API HTTP Brevo ; celui-ci
    était le dernier en SMTP brut. Timeout court : cet appel ne doit
    jamais suspendre une requête."""
    if not settings.BREVO_API_KEY:
        return False
    import httpx
    payload = {
        "sender": {"name": "Globe Genius", "email": "fode@globegenius.app"},
        "to": [{"email": to_email}],
        "subject": "Réinitialiser votre mot de passe Globe Genius",
        "htmlContent": _build_html(reset_url),
        "textContent": _build_text(reset_url),
    }
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
            resp.raise_for_status()
        logger.info(f"Password reset email sent to {to_email} (Brevo API)")
        return True
    except Exception as e:
        logger.error(f"Brevo API reset email failed for {to_email}: {e}")
        return False


async def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send the password-reset email. Returns True iff the message went out.

    Primary: Brevo HTTP API (SMTP ports are blocked on Railway).
    Fallback: SMTP with a hard 10s timeout — never hangs the caller.
    Returns False (no exception) on failure — callers do NOT surface
    this to the user (anti-enumeration)."""
    if await _send_via_brevo_api(to_email, reset_url):
        return True

    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_host or not smtp_user:
        logger.info(f"SMTP not configured, skipping password reset email to {to_email}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Réinitialiser votre mot de passe Globe Genius"
    msg["From"] = f"Globe Genius <{smtp_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(_build_text(reset_url), "plain"))
    msg.attach(MIMEText(_build_html(reset_url), "html"))

    try:
        import aiosmtplib
        # Port 587 → STARTTLS (Brevo default), port 465 → TLS direct.
        send_kwargs = dict(
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
            timeout=10,  # jamais pendre une requête sur un port bloqué
        )
        if smtp_port == 465:
            send_kwargs["use_tls"] = True
        else:
            send_kwargs["start_tls"] = True
        await aiosmtplib.send(msg, **send_kwargs)
        logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False
