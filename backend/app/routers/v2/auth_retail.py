"""
V2: Retail user authentication (register via invite, login).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from ...database import get_db
from ...models import User
from ...models_v2 import RetailUserInvite
from ...schemas import TokenResponse, UserResponse, PINVerify
from ...schemas_v2 import RetailUserRegisterBody, RetailUserRequestPinBody
from ...auth import (
    generate_pin,
    hash_pin,
    verify_pin,
    create_access_token,
    get_current_user,
    PIN_EXPIRE_MINUTES
)
from ...email_service import send_pin_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/retail", tags=["v2-auth-retail"])


@router.post("/register", response_model=TokenResponse)
async def register_via_invite(
    body: RetailUserRegisterBody,
    db: Session = Depends(get_db)
):
    """
    Complete registration using invite token + PIN.
    Call /auth/retail/request-pin first to receive PIN via email.
    """
    invite = db.query(RetailUserInvite).filter(
        RetailUserInvite.token == body.token,
        RetailUserInvite.is_used == False
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite token")
    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")

    user = db.query(User).filter(User.email == invite.email.lower()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Please request a PIN first via /auth/retail/request-pin")
    if user.role != "retail":
        raise HTTPException(status_code=400, detail="Email already registered with different role")
    if not user.pin_code or not user.pin_expires_at:
        raise HTTPException(status_code=400, detail="PIN expired. Please request a new PIN")
    if user.pin_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="PIN expired. Please request a new PIN")
    if not verify_pin(body.pin_code, user.pin_code):
        raise HTTPException(status_code=401, detail="Invalid PIN")

    invite.is_used = True
    invite.used_at = datetime.now(timezone.utc)
    user.pin_code = None
    user.pin_expires_at = None
    db.commit()
    db.refresh(user)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    logger.info(f"Retail user registered via invite: {user.email}")
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/request-pin")
async def request_pin_for_invite(
    body: RetailUserRequestPinBody,
    db: Session = Depends(get_db)
):
    """Request PIN for invite registration. Sends PIN to invite email."""
    invite = db.query(RetailUserInvite).filter(
        RetailUserInvite.token == body.token,
        RetailUserInvite.is_used == False
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")
    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")

    pin_code = generate_pin()
    # Store hashed PIN - we need a way for user to use it. For existing user, update. For new, we'd create user with pin_code.
    # Simpler: send PIN in email. User calls /register with token + pin. For new user we create. For existing we verify.
    email_sent = await send_pin_email(invite.email, pin_code, is_registration=True)
    # Store PIN temporarily - we need to associate it with the invite. For now, we could store in a temp table or
    # create a pending user with pin_code. The simplest: create user with role retail, pin_code, pin_expires. User then
    # calls /register with token+pin - we find invite, find or create user, verify pin.
    existing = db.query(User).filter(User.email == invite.email.lower()).first()
    if existing:
        if existing.role != "retail":
            raise HTTPException(status_code=400, detail="Email already registered with different role")
        existing.pin_code = hash_pin(pin_code)
        existing.pin_expires_at = datetime.now(timezone.utc) + timedelta(minutes=PIN_EXPIRE_MINUTES)
    else:
        new_user = User(
            email=invite.email.lower(),
            role="retail",
            pin_code=hash_pin(pin_code),
            pin_expires_at=datetime.now(timezone.utc) + timedelta(minutes=PIN_EXPIRE_MINUTES),
            is_active=True
        )
        db.add(new_user)
    db.commit()
    return {"message": "PIN sent to your email" if email_sent else f"PIN: {pin_code}", "expires_in_minutes": PIN_EXPIRE_MINUTES}
