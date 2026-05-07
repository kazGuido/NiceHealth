from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List
from uuid import UUID
import logging

from ..database import get_db
from ..models import Device, User, DeviceUserOwner, HealthMeasurement
from ..schemas import DeviceResponse, DeviceCreate, DeviceOwnersUpdate, MyMachineStatusItem
from ..auth import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


def _device_response(device: Device) -> DeviceResponse:
    """Build response with owner_ids from user_owners + legacy owner_id."""
    owner_ids = list({a.user_id for a in device.user_owners} | ({device.owner_id} if device.owner_id else set()))
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        name=device.name,
        device_model=device.device_model,
        mac_addr=device.mac_addr,
        unit_no=device.unit_no,
        unit_name=device.unit_name,
        owner_id=device.owner_id,
        owner_ids=owner_ids,
        created_at=device.created_at,
    )


def _allowed_device_ids_for_user(db: Session, user: User) -> List[str]:
    """Device_id strings (for HealthMeasurement) the user can access."""
    owned_uuids = {r[0] for r in db.query(DeviceUserOwner.device_id).filter(DeviceUserOwner.user_id == user.id)}
    owned_uuids |= {d.id for d in db.query(Device).filter(Device.owner_id == user.id).all()}
    subq = db.query(DeviceUserOwner.device_id).distinct()
    public = db.query(Device).filter(Device.id.notin_(subq), Device.owner_id.is_(None)).all()
    owned_uuids |= {d.id for d in public}
    if not owned_uuids:
        return []
    return [d.device_id for d in db.query(Device).filter(Device.id.in_(owned_uuids)).all()]


def _owned_devices_strict(db: Session, user: User) -> List[Device]:
    """Devices this user owns (assigned owner). Admins: all devices."""
    if user.role == "admin":
        return db.query(Device).order_by(Device.device_id).all()
    owned_uuids = {r[0] for r in db.query(DeviceUserOwner.device_id).filter(DeviceUserOwner.user_id == user.id)}
    owned_uuids |= {d.id for d in db.query(Device).filter(Device.owner_id == user.id).all()}
    if not owned_uuids:
        return []
    return db.query(Device).filter(Device.id.in_(owned_uuids)).order_by(Device.device_id).all()


def _measurements_for_device_string(device_id_str: str):
    return or_(
        HealthMeasurement.device_id == device_id_str,
        HealthMeasurement.measurement_data["deviceNo"].astext == device_id_str,
    )


def _devices_for_user(db: Session, user: User) -> List[Device]:
    """Devices the user can see: they own (user_owners or owner_id) or device is public."""
    owned_uuids = {r[0] for r in db.query(DeviceUserOwner.device_id).filter(DeviceUserOwner.user_id == user.id)}
    owned_uuids |= {d.id for d in db.query(Device).filter(Device.owner_id == user.id).all()}
    subq = db.query(DeviceUserOwner.device_id).distinct()
    public = db.query(Device).filter(Device.id.notin_(subq), Device.owner_id.is_(None)).all()
    owned_uuids |= {d.id for d in public}
    if not owned_uuids:
        return []
    return db.query(Device).filter(Device.id.in_(owned_uuids)).all()


@router.post("/", response_model=DeviceResponse)
async def create_device(
    device_in: DeviceCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Admin: Register a new device."""
    existing = db.query(Device).filter(Device.device_id == device_in.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device ID already registered")
    db_device = Device(**device_in.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    logger.info(f"Admin {admin_user.email} registered device {db_device.device_id}")
    return _device_response(db_device)


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List devices. Admins see all; others see devices they own or public devices."""
    if current_user.role == "admin":
        devices = db.query(Device).all()
        return [_device_response(d) for d in devices]
    devices = _devices_for_user(db, current_user)
    return [_device_response(d) for d in devices]


@router.get("/my-machines-status", response_model=List[MyMachineStatusItem])
async def my_machines_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Per owned machine: last report time and counts (24h / 7d). Used for the owner dashboard strip.
    Admins see all devices; other users only see machines they own.
    """
    now = datetime.now(timezone.utc)
    d24 = now - timedelta(hours=24)
    d7 = now - timedelta(days=7)
    devices = _owned_devices_strict(db, current_user)
    out: List[MyMachineStatusItem] = []
    for dev in devices:
        base = _measurements_for_device_string(dev.device_id)
        last_at = db.query(func.max(HealthMeasurement.created_at)).filter(base).scalar()
        c24 = db.query(HealthMeasurement).filter(base, HealthMeasurement.created_at >= d24).count()
        c7 = db.query(HealthMeasurement).filter(base, HealthMeasurement.created_at >= d7).count()
        out.append(
            MyMachineStatusItem(
                device_id=dev.device_id,
                name=dev.name or dev.device_id,
                last_measurement_at=last_at,
                count_24h=c24,
                count_7d=c7,
            )
        )
    return out


@router.put("/{device_id}/owners", response_model=DeviceResponse)
async def set_device_owners(
    device_id: UUID,
    body: DeviceOwnersUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Admin: Set the list of owners for a device. Empty list = public (no owners)."""
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    # Replace all device_user_owners for this device
    db.query(DeviceUserOwner).filter(DeviceUserOwner.device_id == device_id).delete()
    for uid in body.owner_ids:
        db.add(DeviceUserOwner(device_id=device_id, user_id=uid))
    db_device.owner_id = body.owner_ids[0] if body.owner_ids else None
    db.commit()
    db.refresh(db_device)
    logger.info(
        f"Admin {admin_user.email} set device {db_device.device_id} owners to "
        f"{[str(u) for u in body.owner_ids]}"
    )
    return _device_response(db_device)

