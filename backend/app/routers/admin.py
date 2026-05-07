from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from ..database import get_db
from ..models import HealthMeasurement, User
from ..schemas import (
    HealthMeasurementResponse,
    HealthMeasurementList,
    HealthMeasurementUpdate,
    UserResponse,
    UserUpdate,
    UserCreate,
)
from ..auth import get_current_admin_user, generate_pin, hash_pin, PIN_EXPIRE_MINUTES
from ..email_service import send_pin_email
from ..models import User as UserModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Health Measurement Management
@router.get("/measurements", response_model=HealthMeasurementList)
async def list_all_measurements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: List all health measurements"""
    query = db.query(HealthMeasurement)
    
    if patient_id:
        query = query.filter(HealthMeasurement.patient_id.ilike(f"%{patient_id}%"))
    
    total = query.count()
    items = query.order_by(HealthMeasurement.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    logger.info(f"Admin {admin_user.email} listed measurements (page {page})")
    
    return HealthMeasurementList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/measurements/{measurement_id}", response_model=HealthMeasurementResponse)
async def get_measurement(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Get a single measurement"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    logger.info(f"Admin {admin_user.email} viewed measurement {measurement_id}")
    return measurement

@router.delete("/measurements/{measurement_id}", status_code=204)
async def delete_measurement(
    measurement_id: UUID,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Delete a measurement"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    db.delete(measurement)
    db.commit()
    
    logger.info(f"Admin {admin_user.email} deleted measurement {measurement_id}")
    return None

@router.put("/measurements/{measurement_id}", response_model=HealthMeasurementResponse)
async def update_measurement(
    measurement_id: UUID,
    body: HealthMeasurementUpdate,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Update a measurement (including attribution to customer via customer_id)"""
    measurement = db.query(HealthMeasurement).filter(HealthMeasurement.id == measurement_id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    if body.patient_id is not None:
        measurement.patient_id = body.patient_id
    if body.kiosk_location is not None:
        measurement.kiosk_location = body.kiosk_location
    if 'customer_id' in body.model_dump(exclude_unset=True):
        measurement.customer_id = body.customer_id
    if body.measurement_data is not None:
        measurement.measurement_data = body.measurement_data
    
    db.commit()
    db.refresh(measurement)
    
    logger.info(f"Admin {admin_user.email} updated measurement {measurement_id}")
    return measurement

# User Management
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user),
):
    """Admin: Create a user (e.g. machine owner) by email. Optionally send PIN so they can log in."""
    from datetime import datetime, timedelta
    from ..models import User

    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pin_code = None
    pin_expires = None
    if body.send_pin:
        pin_code = generate_pin()
        pin_hash = hash_pin(pin_code)
        pin_expires = datetime.utcnow() + timedelta(minutes=PIN_EXPIRE_MINUTES)
    else:
        pin_hash = None

    new_user = User(
        email=body.email.lower(),
        role=body.role,
        pin_code=pin_hash,
        pin_expires_at=pin_expires,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if body.send_pin and pin_code:
        email_sent = await send_pin_email(new_user.email, pin_code, is_registration=True)
        if not email_sent:
            logger.warning(f"Failed to send PIN email to {new_user.email}, but user created. PIN: {pin_code}")

    logger.info(f"Admin {admin_user.email} created user {new_user.email} (role={body.role})")
    return UserResponse.model_validate(new_user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: List all users"""
    users = db.query(User).all()
    logger.info(f"Admin {admin_user.email} listed users")
    return [UserResponse.model_validate(user) for user in users]

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Get a single user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"Admin {admin_user.email} viewed user {user_id}")
    return UserResponse.model_validate(user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Update a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deactivating themselves
    if user_id == admin_user.id and user_update.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    if user_update.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == user_update.email.lower(), User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_update.email.lower()
    
    if user_update.role is not None:
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    # v2 Branding fields
    if user_update.business_name is not None:
        user.business_name = user_update.business_name
    if user_update.is_premium is not None:
        user.is_premium = user_update.is_premium
    if user_update.branding_logo_url is not None:
        user.branding_logo_url = user_update.branding_logo_url
    if user_update.branding_primary_color is not None:
        user.branding_primary_color = user_update.branding_primary_color
    if user_update.custom_cta_text is not None:
        user.custom_cta_text = user_update.custom_cta_text
    if user_update.custom_cta_link is not None:
        user.custom_cta_link = user_update.custom_cta_link
    if user_update.whatsapp_phone_e164 is not None:
        user.whatsapp_phone_e164 = user_update.whatsapp_phone_e164.strip() or None

    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {admin_user.email} updated user {user_id}")
    return UserResponse.model_validate(user)

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Delete a user"""
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    logger.info(f"Admin {admin_user.email} deleted user {user_id}")
    return None

@router.post("/users/{user_id}/make-admin", response_model=UserResponse)
async def make_admin(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin_user: UserModel = Depends(get_current_admin_user)
):
    """Admin: Promote a user to admin role"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = "admin"
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin {admin_user.email} promoted user {user_id} to admin")
    return UserResponse.model_validate(user)

