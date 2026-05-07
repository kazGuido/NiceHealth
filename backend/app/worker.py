import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
import logging

from .database import SessionLocal
from .models import User, HealthMeasurement, Device
from .email_service import send_daily_summary_email

logger = logging.getLogger(__name__)


def _get_device_ids_for_machine_owner(db: Session, user: User):
    """
    Return the list of device_id strings (HealthMeasurement.device_id) for which
    this user is a "machine owner":
    - V1: devices where Device.owner_id == user.id
    - V2: devices assigned to any organization the user belongs to (primary or member)
    """
    device_id_strs = set()

    # V1: devices assigned to this user (device_user_owners or legacy owner_id)
    from .models import DeviceUserOwner
    for a in db.query(DeviceUserOwner).filter(DeviceUserOwner.user_id == user.id).all():
        dev = db.query(Device).filter(Device.id == a.device_id).first()
        if dev:
            device_id_strs.add(dev.device_id)
    for d in user.owned_devices:
        device_id_strs.add(d.device_id)

    # V2: devices assigned to orgs where user is primary or member
    try:
        from .models_v2 import Organization, OrganizationUser, DeviceOwner
        # Orgs where user is primary
        orgs_primary = db.query(Organization.id).filter(
            Organization.primary_user_id == user.id,
            Organization.is_active == True
        ).all()
        org_ids = [o[0] for o in orgs_primary]
        # Orgs where user is member (OrganizationUser)
        org_members = db.query(OrganizationUser.organization_id).filter(
            OrganizationUser.user_id == user.id
        ).all()
        org_ids.extend(o[0] for o in org_members)
        org_ids = list(set(org_ids))
        if org_ids:
            # DeviceOwner.device_id is FK to devices.id (UUID); we need Device.device_id (string)
            owner_rows = db.query(DeviceOwner.device_id).filter(
                DeviceOwner.organization_id.in_(org_ids)
            ).distinct().all()
            device_uuids = [r[0] for r in owner_rows]
            if device_uuids:
                devices = db.query(Device).filter(Device.id.in_(device_uuids)).all()
                for d in devices:
                    device_id_strs.add(d.device_id)
    except Exception as e:
        logger.warning(f"V2 device resolution for user {user.id}: {e}")

    return list(device_id_strs)


async def process_daily_notifications():
    """
    Worker task to send daily report summaries to admins and machine owners.

    Recipients:
    - Admins (role=admin): email with counts for all new measurements since last_notified.
    - Machine owners: non-admin users who have at least one assigned device (V1 device_user_owners
      / legacy owner_id, or V2 org device assignment). Staff/customer/regular with no devices
      are skipped. Daily digest is email-only (WhatsApp PDF is separate, on each new save).

    Schedule: configurable via DAILY_SUMMARY_HOUR, DAILY_SUMMARY_MINUTE, DAILY_SUMMARY_TZ (default 14:00 UTC).
    """
    logger.info("Starting daily notification process...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        admin_emails = [u.email for u in users if u.role == "admin" and u.email]

        for user in users:
            last_notified = user.last_notified_at or datetime(2000, 1, 1, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            report_count = 0
            device_summaries = []

            if user.role == "admin":
                # Admins: global summary of ALL new reports
                new_reports = db.query(HealthMeasurement).filter(
                    HealthMeasurement.created_at > last_notified
                ).all()
                report_count = len(new_reports)
                if report_count > 0:
                    device_counts = {}
                    for r in new_reports:
                        d_id = r.device_id or "Inconnu"
                        device_counts[d_id] = device_counts.get(d_id, 0) + 1
                    for d_id, count in device_counts.items():
                        device = db.query(Device).filter(Device.device_id == d_id).first()
                        device_summaries.append({
                            "id": d_id,
                            "name": device.name if device else "Appareil sans nom",
                            "count": count
                        })
            else:
                # Machine owners (V1 and/or V2): only devices assigned to them
                device_id_strs = _get_device_ids_for_machine_owner(db, user)
                if not device_id_strs:
                    continue

                dev_filters = [
                    or_(
                        HealthMeasurement.device_id == d,
                        HealthMeasurement.measurement_data["deviceNo"].astext == d,
                    )
                    for d in device_id_strs
                ]
                new_reports = db.query(HealthMeasurement).filter(
                    or_(*dev_filters),
                    HealthMeasurement.created_at > last_notified,
                ).all()
                report_count = len(new_reports)
                if report_count > 0:
                    device_counts = {}
                    for r in new_reports:
                        md = r.measurement_data or {}
                        d_id = r.device_id or md.get("deviceNo") or md.get("deviceID") or "Inconnu"
                        device_counts[d_id] = device_counts.get(d_id, 0) + 1
                    for d_id, count in device_counts.items():
                        device = db.query(Device).filter(Device.device_id == d_id).first()
                        device_summaries.append({
                            "id": d_id,
                            "name": device.name if device else "Appareil sans nom",
                            "count": count
                        })
                    logger.info(f"Machine owner summary: {user.email} has {report_count} new reports on {len(device_summaries)} device(s)")

            if report_count > 0:
                success = await send_daily_summary_email(
                    user.email,
                    is_admin=(user.role == "admin"),
                    report_count=report_count,
                    device_summaries=device_summaries,
                    cc=admin_emails if user.role != "admin" else None,
                )
                if success:
                    user.last_notified_at = now
                    db.commit()
                    logger.info(f"Daily summary sent to {user.email} ({report_count} reports)")
    except Exception as e:
        logger.error(f"Error in daily notification worker: {str(e)}", exc_info=True)
    finally:
        db.close()

def setup_worker(app):
    """Initialize the scheduler and add the daily task"""
    scheduler = AsyncIOScheduler()

    hour = int(os.getenv("DAILY_SUMMARY_HOUR", "14"))
    minute = int(os.getenv("DAILY_SUMMARY_MINUTE", "0"))
    tz = os.getenv("DAILY_SUMMARY_TZ", "UTC")

    scheduler.add_job(
        process_daily_notifications,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_summary_notification",
        replace_existing=True
    )
    
    @app.on_event("startup")
    async def start_scheduler():
        scheduler.start()
        logger.info(
            "Background worker started (Daily summary at %02d:%02d %s)",
            hour,
            minute,
            tz,
        )

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
        logger.info("Background worker stopped")

