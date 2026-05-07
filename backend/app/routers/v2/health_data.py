from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from typing import Optional, Dict, Any
from uuid import UUID
import logging
import json
from ...database import get_db
from ...models import HealthMeasurement, User, Device, Customer
from ...schemas import (
    HealthMeasurementCreate,
    HealthMeasurementResponse,
    HealthMeasurementList,
    StatsResponse
)
from ...auth import get_current_user
from ...ai_service import analyze_health_data
from ...error_handler import log_and_store_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2"])

@router.get("/report/{measurement_id}")
async def get_public_report(
    measurement_id: UUID,
    db: Session = Depends(get_db)
):
    """v2: Public unauthenticated endpoint for branded health reports"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    # Find the owner of the device to get branding info
    owner_branding = {
        "is_premium": False,
        "business_name": "NiceDay Health",
        "logo_url": None,
        "primary_color": "#3B82F6",
        "cta_text": "Learn more about NiceDay",
        "cta_link": "https://nicedaytech.com"
    }
    
    # Try to find device owner
    if measurement.device_id:
        device = db.query(Device).filter(Device.device_id == measurement.device_id).first()
        if device and device.owner:
            owner = device.owner
            owner_branding = {
                "is_premium": owner.is_premium,
                "business_name": owner.business_name or "NiceDay Health",
                "logo_url": owner.branding_logo_url if owner.is_premium else None,
                "primary_color": owner.branding_primary_color if owner.is_premium else "#3B82F6",
                "cta_text": owner.custom_cta_text if owner.is_premium else "Learn more about NiceDay",
                "cta_link": owner.custom_cta_link if owner.is_premium else "https://nicedaytech.com"
            }

    # Prepare customer info
    customer_info = None
    if measurement.customer:
        customer_info = {
            "name": measurement.customer.full_name,
            "photo_url": measurement.customer.photo_url
        }

    # Get AI analysis (cached or fresh)
    # For now, let's just trigger it or return what we have
    # In a real app, we might want to store the analysis in the DB to avoid re-calls
    analysis = await analyze_health_data(measurement.measurement_data, customer_info)

    return {
        "measurement": {
            "id": measurement.id,
            "data": measurement.measurement_data,
            "created_at": measurement.created_at,
        },
        "customer": customer_info,
        "branding": owner_branding,
        "analysis": analysis
    }

# We can also include the other endpoints if needed, or just let them stay in v1
# For this task, we'll focus on the new branded experience.

