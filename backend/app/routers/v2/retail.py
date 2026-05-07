"""
V2: Retail user endpoints (measurement history, data deletion, workspace).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

from ...database import get_db
from ...models import User, HealthMeasurement
from ...models_v2 import Organization, WorkspaceConfig
from ...schemas_v2 import HealthMeasurementV2Response, HealthMeasurementV2List
from ...auth_v2 import get_current_retail_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retail", tags=["v2-retail"])


@router.get("/me/measurements", response_model=HealthMeasurementV2List)
async def list_my_measurements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_retail_user)
):
    """Retail user: List my measurement history (assigned to me)."""
    query = db.query(HealthMeasurement).filter(
        HealthMeasurement.retail_user_id == current_user.id,
        HealthMeasurement.deleted_at == None
    )
    total = query.count()
    items = query.order_by(HealthMeasurement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return HealthMeasurementV2List(items=items, total=total, page=page, page_size=page_size)


@router.get("/me/measurements/{measurement_id}", response_model=HealthMeasurementV2Response)
async def get_my_measurement(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_retail_user)
):
    """Retail user: Get measurement details."""
    m = db.query(HealthMeasurement).filter(
        HealthMeasurement.id == measurement_id,
        HealthMeasurement.retail_user_id == current_user.id,
        HealthMeasurement.deleted_at == None
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Measurement not found")
    return m


@router.get("/me/workspace")
async def get_my_workspace(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_retail_user)
):
    """Retail user: Get workspace branding for an organization (for report display)."""
    # For retail users we get org from their most recent measurement or from query param
    if organization_id:
        org = db.query(Organization).filter(Organization.id == organization_id).first()
    else:
        m = db.query(HealthMeasurement).filter(
            HealthMeasurement.retail_user_id == current_user.id,
            HealthMeasurement.organization_id != None
        ).order_by(HealthMeasurement.created_at.desc()).first()
        org = db.query(Organization).filter(Organization.id == m.organization_id).first() if (m and m.organization_id) else None
    if not org:
        return {"brand_name": "NiceDay Health", "brand_color": "#3B82F6", "logo_url": None}
    config = db.query(WorkspaceConfig).filter(WorkspaceConfig.organization_id == org.id).first()
    if not config:
        return {"brand_name": org.name, "brand_color": "#3B82F6", "logo_url": None}
    return {
        "brand_name": config.brand_name or org.name,
        "brand_color": config.brand_color or "#3B82F6",
        "logo_url": config.logo_url,
        "favicon_url": config.favicon_url,
        "custom_domain": config.custom_domain,
    }


@router.delete("/me", status_code=204)
async def soft_delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_retail_user)
):
    """Retail user: Soft delete account and all measurement data."""
    now = datetime.now(timezone.utc)
    db.query(HealthMeasurement).filter(
        HealthMeasurement.retail_user_id == current_user.id
    ).update({"deleted_at": now, "status": "deleted", "retail_user_id": None})
    current_user.is_active = False
    db.commit()
    logger.info(f"Retail user {current_user.email} soft-deleted account")
    return None


@router.delete("/me/data", status_code=204)
async def soft_delete_my_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_retail_user)
):
    """Retail user: Soft delete all my measurement data (keep account)."""
    now = datetime.now(timezone.utc)
    db.query(HealthMeasurement).filter(
        HealthMeasurement.retail_user_id == current_user.id
    ).update({"deleted_at": now, "status": "deleted", "retail_user_id": None})
    db.commit()
    logger.info(f"Retail user {current_user.email} soft-deleted all data")
    return None
