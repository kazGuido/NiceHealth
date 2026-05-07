"""Inbound webhooks from internal services (e.g. WhatsApp Baileys bridge)."""
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..email_service import send_whatsapp_monitor_emails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WhatsAppBridgeEvent(BaseModel):
    event: str = Field(..., description="session_lost | session_restored")
    reason: Optional[str] = None
    at: Optional[str] = None


def _monitor_recipient_emails(db: Session) -> List[str]:
    """Admins plus WHATSAPP_MONITOR_EMAILS (deployment / product owners)."""
    emails: List[str] = []
    if os.getenv("WHATSAPP_MONITOR_NOTIFY_ADMINS", "true").lower() in ("1", "true", "yes"):
        for u in db.query(User).filter(User.role == "admin", User.is_active == True).all():  # noqa: E712
            if u.email:
                emails.append(u.email.strip().lower())
    extra = os.getenv("WHATSAPP_MONITOR_EMAILS", "")
    for part in extra.split(","):
        e = part.strip().lower()
        if e and e not in emails:
            emails.append(e)
    return emails


@router.post("/whatsapp-bridge")
async def whatsapp_bridge_webhook(
    body: WhatsAppBridgeEvent,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Called by the Node Baileys bridge when the WhatsApp session disconnects or reconnects.
    Protected by WHATSAPP_BRIDGE_WEBHOOK_SECRET (must match bridge WEBHOOK_SECRET).
    """
    expected = os.getenv("WHATSAPP_BRIDGE_WEBHOOK_SECRET", "").strip()
    if not expected or (x_webhook_secret or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret")

    if body.event not in ("session_lost", "session_restored"):
        raise HTTPException(status_code=400, detail="event must be session_lost or session_restored")

    recipients = _monitor_recipient_emails(db)
    if not recipients:
        logger.warning("WhatsApp monitor webhook: no recipients (no admins / WHATSAPP_MONITOR_EMAILS)")
        return {"ok": True, "notified": 0, "warning": "no_recipients"}

    subject = (
        "[NiceHealth] WhatsApp session perdue — alerte pont Baileys"
        if body.event == "session_lost"
        else "[NiceHealth] WhatsApp session rétablie — pont Baileys"
    )
    detail_reason = body.reason or "—"
    detail_time = body.at or "—"
    if body.event == "session_lost":
        html = f"""
        <html><body style="font-family: sans-serif; color: #334155;">
        <h2 style="color: #b91c1c;">Session WhatsApp interrompue</h2>
        <p>Le pont Baileys (WhatsApp Web) n'est plus connecté. Les envois automatiques de rapports PDF vers les propriétaires de machines peuvent échouer jusqu'à reconnexion.</p>
        <ul>
          <li><strong>Raison signalée :</strong> {detail_reason}</li>
          <li><strong>Horodatage :</strong> {detail_time}</li>
        </ul>
        <p><strong>Action :</strong> consultez les logs du conteneur <code>whatsapp-bridge</code>, vérifiez la session (QR si nécessaire), puis redémarrez le service si besoin.</p>
        <hr><p style="font-size: 12px; color: #64748b;">Message automatique — monitoring WhatsApp NiceHealth</p>
        </body></html>
        """
    else:
        html = f"""
        <html><body style="font-family: sans-serif; color: #334155;">
        <h2 style="color: #15803d;">Session WhatsApp rétablie</h2>
        <p>Le pont Baileys est à nouveau connecté. Les envois PDF peuvent reprendre normalement.</p>
        <ul>
          <li><strong>Horodatage :</strong> {detail_time}</li>
        </ul>
        <hr><p style="font-size: 12px; color: #64748b;">Message automatique — monitoring WhatsApp NiceHealth</p>
        </body></html>
        """

    n = await send_whatsapp_monitor_emails(recipients, subject, html)
    logger.info(
        "WhatsApp bridge webhook: event=%s reason=%s notified=%s recipients=%s",
        body.event,
        body.reason,
        n,
        len(recipients),
    )
    return {"ok": True, "notified": n, "recipients": len(recipients)}
