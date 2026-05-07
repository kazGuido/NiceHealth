"""
V2: Device ownership (add/remove organization owners for a device).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from ...database import get_db
from ...models import User, Device
from ...models_v2 import DeviceOwner, Organization
from ...schemas_v2 import DeviceOwnerCreate, DeviceOwnerResponse
from ...auth_v2 import get_current_admin_user_v2, get_organization_ids_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/device-owners", tags=["v2-device-owners"])


@router.post("/", response_model=DeviceOwnerResponse, status_code=201)
async def add_device_owner(
    body: DeviceOwnerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Add an organization as owner of a device."""
    device = db.query(Device).filter(Device.id == body.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    org = db.query(Organization).filter(Organization.id == body.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    existing = db.query(DeviceOwner).filter(
        DeviceOwner.device_id == body.device_id,
        DeviceOwner.organization_id == body.organization_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization already owns this device")

    if body.is_primary:
        db.query(DeviceOwner).filter(DeviceOwner.device_id == body.device_id).update({"is_primary": False})

    do = DeviceOwner(
        device_id=body.device_id,
        organization_id=body.organization_id,
        is_primary=body.is_primary,
        assigned_by=admin.id
    )
    db.add(do)
    db.commit()
    db.refresh(do)
    logger.info(f"Admin {admin.email} added org {body.organization_id} as owner of device {body.device_id}")
    return do


@router.get("/device/{device_id}", response_model=List[DeviceOwnerResponse])
async def list_device_owners(
    device_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: List owners of a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return db.query(DeviceOwner).filter(DeviceOwner.device_id == device_id).all()


@router.delete("/device/{device_id}/organization/{organization_id}", status_code=204)
async def remove_device_owner(
    device_id: UUID,
    organization_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Remove organization from device owners."""
    do = db.query(DeviceOwner).filter(
        DeviceOwner.device_id == device_id,
        DeviceOwner.organization_id == organization_id
    ).first()
    if not do:
        raise HTTPException(status_code=404, detail="Device owner not found")
    db.delete(do)
    db.commit()
    logger.info(f"Admin {admin.email} removed org {organization_id} from device {device_id}")
    return None
