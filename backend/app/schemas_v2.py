"""
V2 Pydantic schemas for White-label SaaS API.
"""
from pydantic import BaseModel, EmailStr, field_validator
from email_validator import validate_email, EmailNotValidError
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# --- Organization ---
class OrganizationBase(BaseModel):
    name: str
    workspace_url: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    primary_user_id: Optional[UUID] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    workspace_url: Optional[str] = None
    primary_user_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    primary_user_id: Optional[UUID] = None
    is_active: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Location ---
class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class LocationDeviceAdd(BaseModel):
    device_id: UUID


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Device Owner ---
class DeviceOwnerCreate(BaseModel):
    device_id: UUID
    organization_id: UUID
    is_primary: bool = False


class DeviceOwnerResponse(BaseModel):
    id: UUID
    device_id: UUID
    organization_id: UUID
    is_primary: bool
    assigned_at: datetime

    class Config:
        from_attributes = True


# --- Measurement Price ---
class MeasurementPriceBase(BaseModel):
    price: Decimal
    currency: str = "XAF"


class MeasurementPriceCreate(MeasurementPriceBase):
    pass


class MeasurementPriceUpdate(BaseModel):
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class MeasurementPriceResponse(MeasurementPriceBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Alert Preferences ---
class AlertPreferenceBase(BaseModel):
    email_enabled: bool = True
    email_address: Optional[str] = None
    whatsapp_enabled: bool = False
    whatsapp_number: Optional[str] = None
    sms_enabled: bool = False
    sms_number: Optional[str] = None
    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    webhook_url: Optional[str] = None


class AlertPreferenceUpdate(AlertPreferenceBase):
    pass


class AlertPreferenceResponse(AlertPreferenceBase):
    id: UUID
    organization_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Workspace Config ---
class WorkspaceConfigBase(BaseModel):
    brand_name: Optional[str] = None
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_domain: Optional[str] = None
    primary_language: str = "en"
    dashboard_theme: str = "light"
    metrics_display: Optional[Dict[str, Any]] = None


class WorkspaceConfigUpdate(WorkspaceConfigBase):
    pass


class WorkspaceConfigResponse(WorkspaceConfigBase):
    id: UUID
    organization_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Retail User Invite ---
class RetailUserInviteCreate(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        try:
            email_info = validate_email(v, check_deliverability=False)
            return email_info.normalized.lower()
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")


class RetailUserInviteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    token: UUID
    expires_at: datetime
    is_used: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Measurement Assignment ---
class MeasurementAssignBody(BaseModel):
    retail_user_id: UUID


# --- V2 Health Measurement Response ---
class HealthMeasurementV2Response(BaseModel):
    id: UUID
    action: Optional[str] = None
    device_id: Optional[str] = None
    patient_id: Optional[str] = None
    kiosk_location: Optional[str] = None
    measurement_data: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None
    retail_user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    location_id: Optional[UUID] = None
    status: Optional[str] = None
    price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthMeasurementV2List(BaseModel):
    items: List[HealthMeasurementV2Response]
    total: int
    page: int
    page_size: int


# --- Retail User Register (via invite) ---
class RetailUserRegisterBody(BaseModel):
    token: UUID
    pin_code: str


class RetailUserRequestPinBody(BaseModel):
    token: UUID
