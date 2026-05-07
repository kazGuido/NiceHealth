import aiosmtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Health Data App")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://niceq-app.nicedaytech.com")

async def send_pin_email(email: str, pin_code: str, is_registration: bool = False):
    """Send PIN code via email"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured. PIN code would be: %s", pin_code)
        return False
    
    try:
        subject = "Your PIN Code" if not is_registration else "Welcome - Your PIN Code"
        
        body = f"""
        <html>
        <body>
            <h2>{'Welcome to Health Data App!' if is_registration else 'Your PIN Code'}</h2>
            <p>Your PIN code is: <strong style="font-size: 24px; color: #2563eb;">{pin_code}</strong></p>
            <p>This PIN will expire in 10 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">This is an automated message from Health Data App.</p>
        </body>
        </html>
        """
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = email
        
        text_part = MIMEText(f"Your PIN code is: {pin_code}. This PIN will expire in 10 minutes.", "plain")
        html_part = MIMEText(body, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        # Determine TLS settings based on port
        use_tls = SMTP_PORT == 465
        start_tls = SMTP_PORT == 587 or SMTP_PORT == 25
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=start_tls,
        )
        
        logger.info(f"PIN email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send PIN email to {email}: {str(e)}", exc_info=True)
        return False

async def send_report_email(email: str, customer_name: str, measurement_data: dict, created_at: datetime, measurement_id: str = None):
    """Send health report via email with a link to the v2 portal"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured. Cannot send report email.")
        return False
    
    try:
        from datetime import datetime as dt
        subject = f"Votre Rapport de Santé - {customer_name}"
        date_str = created_at.strftime("%d/%m/%Y à %H:%M")
        
        # Simple HTML summary of metrics
        metrics_html = ""
        # Filter for simple numeric or string values to display in summary
        for key, value in measurement_data.items():
            if isinstance(value, (int, float, str)) and len(str(value)) < 20:
                metrics_html += f"<li><strong>{key.replace('_', ' ').capitalize()}:</strong> {value}</li>"
        
        # Add v2 report link if available
        report_link_html = ""
        if measurement_id:
            report_link = f"{FRONTEND_URL}/v2/report/{measurement_id}"
            report_link_html = f"""
                <div style="margin-top: 30px; text-align: center;">
                    <a href="{report_link}" 
                       style="background: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 14px; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);">
                        Voir mon rapport interactif
                    </a>
                </div>
            """

        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #334155; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 32px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);">
                <h2 style="color: #2563eb; margin-top: 0; font-size: 24px;">Votre Rapport de Santé</h2>
                <p>Bonjour <strong>{customer_name}</strong>,</p>
                <p>Voici le résumé de votre mesure effectuée le {date_str} :</p>
                <ul style="background: #f8fafc; padding: 25px; border-radius: 20px; list-style: none; margin: 25px 0; border: 1px solid #f1f5f9;">
                    {metrics_html}
                </ul>
                
                {report_link_html}

                <p style="margin-top: 30px; font-size: 14px; color: #64748b;">Consultez votre professionnel de santé pour une analyse médicale approfondie.</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="color: #94a3b8; font-size: 11px; text-align: center;">Ceci est un message automatique de Health Data App.</p>
            </div>
        </body>
        </html>
        """
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = email
        
        html_part = MIMEText(body, "html")
        message.attach(html_part)
        
        # Determine TLS settings based on port
        use_tls = SMTP_PORT == 465
        start_tls = SMTP_PORT == 587 or SMTP_PORT == 25
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=start_tls,
        )
        
        logger.info(f"Report email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send report email to {email}: {str(e)}", exc_info=True)
        return False

async def send_daily_summary_email(
    email: str,
    is_admin: bool,
    report_count: int,
    device_summaries: list = None,
    cc: list = None,
):
    """Send daily summary of reports to admin or machine owner. Machine owner emails can CC admins."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured. Cannot send summary email.")
        return False

    cc = cc or []
    cc = [a for a in cc if a and a.strip() and a != email]  # skip empty and To

    try:
        subject = "Résumé Quotidien des Rapports de Santé"

        device_html = ""
        if device_summaries:
            device_html = "<h3>Détails par appareil :</h3><ul style='list-style: none; padding: 0;'>"
            for ds in device_summaries:
                device_html += f"<li style='margin-bottom: 10px; padding: 10px; background: #f1f5f9; border-radius: 8px;'><strong>{ds['name']}</strong> ({ds['id']}): {ds['count']} nouveaux rapports</li>"
            device_html += "</ul>"

        body = f"""
        <html>
        <body style="font-family: sans-serif; color: #334155; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 24px;">
                <h2 style="color: #2563eb; margin-top: 0;">{ "Résumé Global" if is_admin else "Résumé de vos Appareils" }</h2>
                <p>Bonjour,</p>
                <p>Il y a eu <strong>{report_count}</strong> nouveaux rapports enregistrés depuis votre dernière notification.</p>

                {device_html}

                <div style="margin-top: 30px; text-align: center;">
                    <a href="https://niceq-app.nicedaytech.com/"
                       style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 12px; font-weight: bold; display: inline-block;">
                        Accéder à la plateforme
                    </a>
                </div>

                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="color: #64748b; font-size: 12px; text-align: center;">Ceci est un message automatique de Health Data App.</p>
            </div>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = email
        if cc:
            message["Cc"] = ", ".join(cc)

        html_part = MIMEText(body, "html")
        message.attach(html_part)

        # Determine TLS settings
        use_tls = SMTP_PORT == 465
        start_tls = SMTP_PORT == 587 or SMTP_PORT == 25

        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=start_tls,
        )

        logger.info(f"Summary email sent successfully to {email}" + (f" (CC: {cc})" if cc else ""))
        return True

    except Exception as e:
        logger.error(f"Failed to send summary email to {email}: {str(e)}", exc_info=True)
        return False


async def send_whatsapp_monitor_emails(recipient_emails: list, subject: str, html_body: str) -> int:
    """
    Send the same monitor alert to each recipient (admin / WHATSAPP_MONITOR_EMAILS).
    Returns count of successful sends.
    """
    if not recipient_emails:
        return 0
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured. WhatsApp monitor email skipped (would send to %s).", recipient_emails)
        return 0

    use_tls = SMTP_PORT == 465
    start_tls = SMTP_PORT == 587 or SMTP_PORT == 25
    sent = 0
    for email in recipient_emails:
        if not email or not str(email).strip():
            continue
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            message["To"] = str(email).strip()
            message.attach(MIMEText(html_body, "html"))
            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASSWORD,
                use_tls=use_tls,
                start_tls=start_tls,
            )
            sent += 1
            logger.info("WhatsApp monitor email sent to %s", email)
        except Exception as e:
            logger.error("Failed to send WhatsApp monitor email to %s: %s", email, e, exc_info=True)
    return sent

