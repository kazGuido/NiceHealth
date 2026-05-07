"""Resolve machine owners and send PDF via WhatsApp bridge; audit log rows."""
from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Set, Tuple
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User, Device, HealthMeasurement, OwnerNotificationLog, DeviceUserOwner
from .pdf_report import build_measurement_pdf

logger = logging.getLogger(__name__)

# Lazily import V2 models when DB has org linkage
try:
    from .models_v2 import Organization, DeviceOwner, AlertPreference  # noqa: F401
except Exception:  # pragma: no cover
    Organization = DeviceOwner = AlertPreference = None  # type: ignore


def _normalize_phone(raw: Optional[str]) -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) < 8:
        return None
    return digits


def _whatsapp_enabled() -> bool:
    return os.getenv("WHATSAPP_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _bridge_url() -> Optional[str]:
    u = os.getenv("WHATSAPP_BRIDGE_URL", "").strip()
    return u or None


def collect_whatsapp_targets(db: Session, device_id_str: Optional[str]) -> List[Tuple[Optional[UUID], Optional[UUID], str]]:
    """
    Returns deduped list of (user_id, organization_id, digits_only_phone) for WhatsApp sends.
    """
    if not device_id_str:
        return []
    dev = db.query(Device).filter(Device.device_id == device_id_str).first()
    if not dev:
        return []

    out: List[Tuple[Optional[UUID], Optional[UUID], str]] = []
    seen_phones: Set[str] = set()

    def add(uid: Optional[UUID], oid: Optional[UUID], phone_raw: Optional[str]) -> None:
        dig = _normalize_phone(phone_raw)
        if not dig or dig in seen_phones:
            return
        seen_phones.add(dig)
        out.append((uid, oid, dig))

    for duo in db.query(DeviceUserOwner).filter(DeviceUserOwner.device_id == dev.id).all():
        u = db.query(User).filter(User.id == duo.user_id).first()
        if u:
            add(u.id, None, u.whatsapp_phone_e164)

    if dev.owner_id:
        u = db.query(User).filter(User.id == dev.owner_id).first()
        if u:
            add(u.id, None, u.whatsapp_phone_e164)

    if AlertPreference and DeviceOwner and Organization:
        owner_rows = db.query(DeviceOwner).filter(DeviceOwner.device_id == dev.id).all()
        for ow in owner_rows:
            pref = (
                db.query(AlertPreference)
                .filter(AlertPreference.organization_id == ow.organization_id)
                .first()
            )
            if pref and pref.whatsapp_enabled and pref.whatsapp_number:
                add(None, ow.organization_id, pref.whatsapp_number)
            else:
                org = db.query(Organization).filter(Organization.id == ow.organization_id).first()
                if org and org.primary_user_id:
                    pu = db.query(User).filter(User.id == org.primary_user_id).first()
                    if pu:
                        add(pu.id, ow.organization_id, pu.whatsapp_phone_e164)

    return out


async def send_pdf_to_bridge(phone_digits: str, pdf_bytes: bytes, caption: str) -> Tuple[bool, str]:
    base = _bridge_url()
    if not base:
        return False, "WHATSAPP_BRIDGE_URL not set"
    url = base.rstrip("/") + "/send-document"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                url,
                data={"to": phone_digits, "caption": caption},
                files={"file": ("rapport.pdf", pdf_bytes, "application/pdf")},
            )
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:500]}"
        return True, r.text[:200]
    except Exception as e:
        logger.exception("WhatsApp bridge request failed")
        return False, str(e)[:500]


def log_notification(
    db: Session,
    measurement_id: UUID,
    user_id: Optional[UUID],
    organization_id: Optional[UUID],
    phone_e164: str,
    status: str,
    detail: Optional[str],
) -> None:
    row = OwnerNotificationLog(
        measurement_id=measurement_id,
        user_id=user_id,
        organization_id=organization_id,
        phone_e164=phone_e164,
        channel="whatsapp",
        status=status,
        detail=detail,
    )
    db.add(row)
    db.commit()


async def notify_owners_for_measurement(measurement_id: UUID) -> None:
    """Background task: PDF + WhatsApp for all targets; always audit-log."""
    db = SessionLocal()
    try:
        m = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
        if not m:
            logger.warning("notify_owners: measurement %s not found", measurement_id)
            return

        device_id_str = m.device_id
        if not device_id_str and m.measurement_data:
            device_id_str = (
                m.measurement_data.get("deviceNo")
                or m.measurement_data.get("deviceID")
                or m.measurement_data.get("device_id")
            )
            if not device_id_str and isinstance(m.measurement_data.get("datas"), list):
                d0 = m.measurement_data["datas"][0] if m.measurement_data["datas"] else {}
                if isinstance(d0, dict):
                    device_id_str = d0.get("deviceNo") or d0.get("deviceID")

        targets = collect_whatsapp_targets(db, device_id_str)
        caption = f"Nouveau rapport de mesure ({device_id_str or 'appareil'})"

        if not _whatsapp_enabled():
            for uid, oid, dig in targets:
                log_notification(
                    db,
                    measurement_id,
                    uid,
                    oid,
                    "+" + dig,
                    "skipped",
                    "WHATSAPP_ENABLED is off",
                )
            if not targets:
                log_notification(db, measurement_id, None, None, "+0", "skipped", "No owners or WhatsApp numbers")
            return

        if not _bridge_url():
            for uid, oid, dig in targets:
                log_notification(
                    db,
                    measurement_id,
                    uid,
                    oid,
                    "+" + dig,
                    "skipped",
                    "WHATSAPP_BRIDGE_URL not configured",
                )
            if not targets:
                log_notification(db, measurement_id, None, None, "+0", "skipped", "No WhatsApp targets")
            return

        if not targets:
            log_notification(db, measurement_id, None, None, "+0", "skipped", "No owners with WhatsApp numbers")
            return

        pdf_bytes = build_measurement_pdf(m)

        for uid, oid, dig in targets:
            ok, msg = await send_pdf_to_bridge(dig, pdf_bytes, caption)
            log_notification(
                db,
                measurement_id,
                uid,
                oid,
                "+" + dig,
                "sent" if ok else "failed",
                msg if not ok else None,
            )
    except Exception as e:
        logger.exception("notify_owners_for_measurement: %s", e)
        try:
            log_notification(db, measurement_id, None, None, "+0", "failed", str(e)[:500])
        except Exception:
            db.rollback()
    finally:
        db.close()
