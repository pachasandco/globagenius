import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger(__name__)

WELCOME_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background:#f4f4f4; font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4; padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#0891b2,#f59e0b); padding:40px 40px 30px; text-align:center;">
              <h1 style="color:#ffffff; font-size:28px; margin:0 0 8px;">Bienvenue sur Globe Genius !</h1>
              <p style="color:rgba(255,255,255,0.85); font-size:15px; margin:0;">Votre chasseur de deals voyage intelligent</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <p style="color:#333; font-size:15px; line-height:1.6; margin:0 0 20px;">
                Bonjour,<br><br>
                Votre compte Globe Genius est cree ! Voici comment profiter au maximum de notre service :
              </p>

              <!-- Step 1 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#0891b2,#06b6d4); color:#fff; font-size:16px; font-weight:bold; text-align:center; line-height:36px;">1</div>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="color:#333; font-size:14px; margin:0;"><strong>Configurez vos preferences</strong></p>
                    <p style="color:#888; font-size:13px; margin:4px 0 0;">Choisissez vos aeroports de depart, types d'offres et destinations preferees.</p>
                  </td>
                </tr>
              </table>

              <!-- Step 2 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#f59e0b,#f97316); color:#fff; font-size:16px; font-weight:bold; text-align:center; line-height:36px;">2</div>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="color:#333; font-size:14px; margin:0;"><strong>Connectez Telegram</strong></p>
                    <p style="color:#888; font-size:13px; margin:4px 0 0;">Reliez votre compte Telegram pour recevoir les alertes de deals en temps reel.</p>
                  </td>
                </tr>
              </table>

              <!-- Step 3 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td width="48" valign="top">
                    <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#10b981,#06b6d4); color:#fff; font-size:16px; font-weight:bold; text-align:center; line-height:36px;">3</div>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="color:#333; font-size:14px; margin:0;"><strong>Recevez vos deals</strong></p>
                    <p style="color:#888; font-size:13px; margin:4px 0 0;">Notre IA scanne les prix 24h/24. Des qu'un deal a -40% est detecte, vous etes alerte.</p>
                  </td>
                </tr>
              </table>

              <!-- Info box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdfa; border-radius:12px; border:1px solid #ccfbf1;">
                <tr>
                  <td style="padding:20px;">
                    <p style="color:#0d9488; font-size:14px; font-weight:bold; margin:0 0 8px;">Ce que vous allez recevoir :</p>
                    <p style="color:#666; font-size:13px; line-height:1.6; margin:0;">
                      🔥 <strong>Alertes instantanees</strong> — deals avec score superieur a 70/100<br>
                      📬 <strong>Digest quotidien</strong> — top 5 deals du jour a 8h<br>
                      ✈️ <strong>3 types d'offres</strong> — packages, vols seuls, hebergements seuls<br>
                      🌍 <strong>24 destinations</strong> — Europe, Maghreb et long-courrier
                    </p>
                  </td>
                </tr>
              </table>

              <!-- CTA -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;">
                <tr>
                  <td align="center">
                    <a href="https://globegenius.com/dashboard" style="display:inline-block; background:#222; color:#fff; font-size:15px; font-weight:600; padding:14px 32px; border-radius:12px; text-decoration:none;">
                      Acceder a mon dashboard →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px; background:#fafafa; border-top:1px solid #eee; text-align:center;">
              <p style="color:#aaa; font-size:12px; margin:0;">
                Globe Genius © 2026 — Packages voyage a prix casses<br>
                Vous recevez cet email car vous venez de creer un compte.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


async def send_welcome_email(to_email: str):
    """Send HTML welcome email to new user."""
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_host or not smtp_user:
        logger.info(f"SMTP not configured, skipping welcome email to {to_email}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Bienvenue sur Globe Genius ! ✈️"
    msg["From"] = f"Globe Genius <{smtp_user}>"
    msg["To"] = to_email

    text_part = MIMEText(
        "Bienvenue sur Globe Genius ! Votre compte est cree. "
        "Configurez vos preferences et connectez Telegram pour recevoir les deals.",
        "plain",
    )
    html_part = MIMEText(WELCOME_HTML, "html")

    msg.attach(text_part)
    msg.attach(html_part)

    try:
        import aiosmtplib
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
            use_tls=True,
        )
        logger.info(f"Welcome email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {to_email}: {e}")
