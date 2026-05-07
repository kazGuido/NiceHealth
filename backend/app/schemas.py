from pydantic import BaseModel, EmailStr, field_validator
from email_validator import validate_email, EmailNotValidError
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
from uuid import UUID

UserRole = Literal["admin", "staff", "customer", "regular", "retail"]

class DeviceBase(BaseModel):
    device_id: str
    name: Optional[str] = None
    device_model: Optional[str] = None
    mac_addr: Optional[str] = None
    unit_no: Optional[str] = None
    unit_name: Optional[str] = None

class DeviceCreate(DeviceBase):
    owner_id: Optional[UUID] = None

class DeviceResponse(DeviceBase):
    id: UUID
    owner_id: Optional[UUID] = None
    owner_ids: List[UUID] = []  # all owners (device_user_owners + legacy owner_id)
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceOwnersUpdate(BaseModel):
    """Set the list of owner user IDs for a device. Empty = public (no owners)."""
    owner_ids: List[UUID] = []


class CustomerBase(BaseModel):
    full_name: str
    email: Optional[str] = None
    dob: Optional[datetime] = None
    photo_url: Optional[str] = None

class CustomerCreate(CustomerBase):
    user_id: Optional[UUID] = None

class CustomerResponse(CustomerBase):
    id: UUID
    user_id: Optional[UUID] = None
    created_by: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class HealthMeasurementCreate(BaseModel):
    patient_id: Optional[str] = None
    kiosk_location: Optional[str] = None
    measurement_data: Dict[str, Any]  # Accept any JSON structure
    customer_id: Optional[UUID] = None

class HealthMeasurementResponse(BaseModel):
    id: UUID
    action: Optional[str] = None  # Action from reference format
    device_id: Optional[str] = None  # deviceID from reference format
    patient_id: Optional[str] = None
    kiosk_location: Optional[str] = None
    measurement_data: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None  # Complete raw incoming payload
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True

class HealthMeasurementUpdate(BaseModel):
    patient_id: Optional[str] = None
    kiosk_location: Optional[str] = None
    customer_id: Optional[UUID] = None
    measurement_data: Optional[Dict[str, Any]] = None

class HealthMeasurementList(BaseModel):
    items: list[HealthMeasurementResponse]
    total: int
    page: int
    page_size: int

class SendReportEmailBody(BaseModel):
    """Optional body: send report to this email (e.g. after customer enters email on kiosk)."""
    email: Optional[EmailStr] = None

class StatsResponse(BaseModel):
    total_measurements: int
    bmi_normal: int
    bmi_overweight: int
    bmi_obesity: int


class MyMachineStatusItem(BaseModel):
    """Per-machine summary for owner dashboard."""
    device_id: str
    name: str
    last_measurement_at: Optional[datetime] = None
    count_24h: int = 0
    count_7d: int = 0

# Authentication Schemas
class UserRegister(BaseModel):
    email: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        try:
            # Skip deliverability check (DNS lookup) which can fail in dev/certain networks
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")

class UserLogin(BaseModel):
    email: str
    pin_code: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        try:
            # Skip deliverability check (DNS lookup) which can fail in dev/certain networks
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")

class PINVerify(BaseModel):
    email: str
    pin_code: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        try:
            # Skip deliverability check (DNS lookup) which can fail in dev/certain networks
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")

class PINResponse(BaseModel):
    message: str
    expires_in_minutes: int

class UserCreate(BaseModel):
    """Admin: create a user (e.g. machine owner) by email."""
    email: str
    role: UserRole = "regular"
    send_pin: bool = True  # send PIN email so they can log in

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        try:
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    business_name: Optional[str] = None
    is_premium: Optional[bool] = None
    branding_logo_url: Optional[str] = None
    branding_primary_color: Optional[str] = None
    custom_cta_text: Optional[str] = None
    custom_cta_link: Optional[str] = None
    whatsapp_phone_e164: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    business_name: Optional[str] = None
    is_premium: Optional[bool] = None
    branding_logo_url: Optional[str] = None
    branding_primary_color: Optional[str] = None
    custom_cta_text: Optional[str] = None
    custom_cta_link: Optional[str] = None
    whatsapp_phone_e164: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            # Skip deliverability check (DNS lookup) which can fail in dev/certain networks
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")
