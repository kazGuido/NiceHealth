"""
V2: Measurement assignment (machine owner assigns pending measurements to retail users).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from uuid import UUID
import logging

from ...database import get_db
from ...models import User, HealthMeasurement, Device
from ...models_v2 import DeviceOwner, Organization
from ...schemas_v2 import MeasurementAssignBody, HealthMeasurementV2Response, HealthMeasurementV2List
from ...auth_v2 import get_current_customer_user, get_organization_ids_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/measurements", tags=["v2-measurements"])


def _measurement_accessible(db: Session, user: User, m: HealthMeasurement) -> bool:
    """Check if user can access this measurement (for assignment)."""
    if user.role == "admin":
        return True
    if m.organization_id and m.organization_id in get_organization_ids_for_user(db, user):
        return True
    if m.device_id:
        device = db.query(Device).filter(Device.device_id == m.device_id).first()
        if device:
            owners = db.query(DeviceOwner).filter(DeviceOwner.device_id == device.id).all()
            if not owners:
                return True
            for do in owners:
                if do.organization_id in get_organization_ids_for_user(db, user):
                    return True
    return False


@router.get("/", response_model=HealthMeasurementV2List)
async def list_measurements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="pending | assigned"),
    organization_id: Optional[UUID] = Query(None),
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """List measurements accessible to current customer (machine owner)."""
    org_ids = get_organization_ids_for_user(db, current_user)
    query = db.query(HealthMeasurement).filter(HealthMeasurement.deleted_at == None)

    if current_user.role != "admin":
        # Device IDs (string) that belong to our orgs
        device_ids_owned = {
            row[0] for row in db.query(Device.device_id).join(
                DeviceOwner, Device.id == DeviceOwner.device_id
            ).filter(DeviceOwner.organization_id.in_(org_ids)).distinct().all()
        }
        # Device IDs (string) with no owners (public)
        device_ids_with_owners = {
            row[0] for row in db.query(Device.device_id).join(
                DeviceOwner, Device.id == DeviceOwner.device_id
            ).distinct().all()
        }
        all_device_ids = {row[0] for row in db.query(Device.device_id).all()}
        device_ids_public = all_device_ids - device_ids_with_owners

        conditions = [HealthMeasurement.organization_id.in_(org_ids)]
        if device_ids_owned:
            conditions.append(HealthMeasurement.device_id.in_(device_ids_owned))
        if device_ids_public:
            conditions.append(HealthMeasurement.device_id.in_(device_ids_public))
        conditions.append(
            (HealthMeasurement.device_id == None) & (HealthMeasurement.organization_id == None)
        )
        query = query.filter(or_(*conditions))

    if status:
        query = query.filter(HealthMeasurement.status == status)
    if organization_id:
        query = query.filter(HealthMeasurement.organization_id == organization_id)
    if device_id:
        query = query.filter(HealthMeasurement.device_id.ilike(f"%{device_id}%"))

    total = query.count()
    items = query.order_by(HealthMeasurement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return HealthMeasurementV2List(items=items, total=total, page=page, page_size=page_size)


@router.get("/{measurement_id}", response_model=HealthMeasurementV2Response)
async def get_measurement(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Get measurement details."""
    m = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Measurement not found")
    if not _measurement_accessible(db, current_user, m):
        raise HTTPException(status_code=403, detail="Not authorized to access this measurement")
    return m


@router.patch("/{measurement_id}/assign", response_model=HealthMeasurementV2Response)
async def assign_measurement(
    measurement_id: UUID,
    body: MeasurementAssignBody,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Assign a pending measurement to a retail user."""
    m = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Measurement not found")
    if not _measurement_accessible(db, current_user, m):
        raise HTTPException(status_code=403, detail="Not authorized to assign this measurement")
    if m.status == "assigned":
        raise HTTPException(status_code=400, detail="Measurement already assigned")

    org_ids = get_organization_ids_for_user(db, current_user)
    target_org_id = organization_id or m.organization_id
    if not target_org_id and org_ids:
        target_org_id = org_ids[0]
    if target_org_id and target_org_id not in org_ids and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    m.retail_user_id = body.retail_user_id
    m.organization_id = target_org_id
    m.status = "assigned"
    db.commit()
    db.refresh(m)
    logger.info(f"User {current_user.email} assigned measurement {measurement_id} to retail user {body.retail_user_id}")
    return m
