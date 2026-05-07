from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..database import get_db
from ..models import User
from ..schemas import (
    UserRegister,
    UserLogin,
    PINVerify,
    PINResponse,
    TokenResponse,
    UserResponse
)
from ..auth import (
    generate_pin,
    hash_pin,
    verify_pin,
    create_access_token,
    get_current_user,
    PIN_EXPIRE_MINUTES
)
from ..email_service import send_pin_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=PINResponse, status_code=201)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user - sends PIN code via email"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate PIN
    pin_code = generate_pin()
    logger.info(f"Generated PIN for registration: {len(pin_code)} characters")
    try:
        pin_hash = hash_pin(pin_code)
    except Exception as e:
        logger.error(f"Failed to hash PIN: {e}. PIN value: {pin_code}, PIN type: {type(pin_code)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process registration. Please try again."
        )
    pin_expires = datetime.utcnow() + timedelta(minutes=PIN_EXPIRE_MINUTES)
    
    # Create user
    # Auto-promote specific emails to admin
    role = "regular"
    if user_data.email.lower() in ["kazihise.guy@gmail.com", "support@nicedaytech.com"]:
        role = "admin"
        logger.info(f"Auto-promoting {user_data.email} to admin")

    new_user = User(
        email=user_data.email.lower(),
        role=role,
        pin_code=pin_hash,
        pin_expires_at=pin_expires,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send PIN via email
    email_sent = await send_pin_email(new_user.email, pin_code, is_registration=True)
    
    if not email_sent:
        logger.warning(f"Failed to send PIN email to {new_user.email}, but user created. PIN: {pin_code}")
    
    logger.info(f"New user registered: {new_user.email}")
    
    return PINResponse(
        message="Registration successful. PIN code sent to your email." if email_sent else f"Registration successful. PIN code: {pin_code}",
        expires_in_minutes=PIN_EXPIRE_MINUTES
    )

@router.post("/request-pin", response_model=PINResponse)
async def request_pin(user_data: UserRegister, db: Session = Depends(get_db)):
    """Request a new PIN code for login"""
    user = db.query(User).filter(User.email == user_data.email.lower()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate new PIN
    pin_code = generate_pin()
    pin_hash = hash_pin(pin_code)
    pin_expires = datetime.utcnow() + timedelta(minutes=PIN_EXPIRE_MINUTES)
    
    # Update user
    user.pin_code = pin_hash
    user.pin_expires_at = pin_expires
    db.commit()
    
    # Send PIN via email
    email_sent = await send_pin_email(user.email, pin_code, is_registration=False)
    
    if not email_sent:
        logger.warning(f"Failed to send PIN email to {user.email}. PIN: {pin_code}")
    
    logger.info(f"PIN requested for user: {user.email}")
    
    return PINResponse(
        message="PIN code sent to your email." if email_sent else f"PIN code: {pin_code}",
        expires_in_minutes=PIN_EXPIRE_MINUTES
    )

@router.post("/verify-pin", response_model=TokenResponse)
async def verify_pin_code(pin_data: PINVerify, db: Session = Depends(get_db)):
    """Verify PIN code and return JWT token"""
    user = db.query(User).filter(User.email == pin_data.email.lower()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Check if PIN exists and is not expired
    if not user.pin_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PIN code found. Please request a new PIN."
        )
    
    if user.pin_expires_at and user.pin_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN code has expired. Please request a new PIN."
        )
    
    # Verify PIN
    if not verify_pin(pin_data.pin_code, user.pin_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN code"
        )
    
    # PIN verified - create access token
    # user.role is stored as a plain string ("admin" | "regular")
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    
    # Update user
    user.last_login = datetime.utcnow()
    user.pin_code = None  # Clear PIN after successful login
    user.pin_expires_at = None
    db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)

