from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from ..database import get_db
from ..models import Customer, User
from ..schemas import CustomerResponse, CustomerCreate
from ..auth import get_current_user
from ..storage import upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/", response_model=CustomerResponse)
async def create_customer(
    full_name: str = Form(...),
    email: Optional[str] = Form(None),
    dob: Optional[datetime] = Form(None),
    user_id: Optional[UUID] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new customer profile"""
    photo_url = None
    if photo:
        try:
            photo_url = upload_file(photo.file, photo.filename, photo.content_type)
        except Exception as e:
            logger.error(f"Failed to upload photo: {e}")
            # Continue without photo
    
    db_customer = Customer(
        full_name=full_name,
        email=email,
        dob=dob,
        user_id=user_id,
        photo_url=photo_url,
        created_by=current_user.id
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    logger.info(f"User {current_user.email} created customer {full_name}")
    return db_customer

@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all customers"""
    return db.query(Customer).offset(skip).limit(limit).all()

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer details"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

