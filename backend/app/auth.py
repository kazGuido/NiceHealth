from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
import secrets
import logging
import bcrypt

logger = logging.getLogger(__name__)

# JWT Configuration
import os
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-use-env-var")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# PIN Configuration
PIN_LENGTH = 6
PIN_EXPIRE_MINUTES = 10

# Password hashing
# Configure bcrypt with explicit rounds to avoid issues
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)
security = HTTPBearer()

def generate_pin() -> str:
    """Generate a random 6-digit PIN"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(PIN_LENGTH)])

def hash_pin(pin: str) -> str:
    """Hash a PIN using bcrypt directly (bypassing passlib compatibility issues)"""
    # Ensure PIN is a string and properly encoded
    if not isinstance(pin, str):
        pin = str(pin)
    
    # Encode PIN to bytes
    pin_bytes = pin.encode('utf-8')
    logger.debug(f"Hashing PIN of length {len(pin_bytes)} bytes")
    
    # Ensure it's not longer than 72 bytes (bcrypt limit)
    if len(pin_bytes) > 72:
        logger.error(f"PIN too long ({len(pin_bytes)} bytes), truncating. PIN value: {pin[:20]}...")
        pin_bytes = pin_bytes[:72]
    
    try:
        # Use bcrypt directly with 12 rounds
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(pin_bytes, salt)
        # Return as string (bcrypt returns bytes)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing PIN: {e}. PIN length: {len(pin_bytes)} bytes, PIN value: {pin[:20]}...")
        raise

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a PIN against its hash using bcrypt directly"""
    try:
        # Encode both to bytes
        pin_bytes = plain_pin.encode('utf-8')
        hash_bytes = hashed_pin.encode('utf-8')
        # Use bcrypt to verify
        return bcrypt.checkpw(pin_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Error verifying PIN: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current authenticated user from JWT token, or None if not authenticated"""
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
    
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current user and verify they are an admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

