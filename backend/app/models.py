from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base

class HealthMeasurement(Base):
    __tablename__ = "health_measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    action = Column(String, nullable=True, index=True)  # Action type from reference format
    device_id = Column(String, nullable=True, index=True)  # deviceID from reference format
    patient_id = Column(String, nullable=True, index=True)  # Keep for backward compatibility
    kiosk_location = Column(String, nullable=True)  # Keep for backward compatibility
    measurement_data = Column(JSONB, nullable=False)  # Stores the 'datas' content
    raw_data = Column(JSONB, nullable=True)  # Stores the complete raw incoming payload for analysis
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # V2: retail user assignment, organization, location, status, price, soft delete
    retail_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    status = Column(String, default="pending", nullable=True)  # pending | assigned | deleted
    price = Column(Numeric(12, 2), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="measurements")
    retail_user = relationship("User", foreign_keys=[retail_user_id])
    organization = relationship("Organization", foreign_keys=[organization_id], back_populates="measurements")
    location = relationship("Location", foreign_keys=[location_id], back_populates="measurements")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="regular", nullable=False)  # "admin" | "staff" | "customer"
    pin_hash = Column(String, nullable=True)  # Hashed PIN
    pin_code = Column(String, nullable=True)  # Temporary PIN for login (hashed)
    pin_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Branding fields for v2
    business_name = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False, nullable=False)
    branding_logo_url = Column(String, nullable=True)
    branding_primary_color = Column(String, nullable=True, default="#3B82F6") # Default Tailwind blue-500
    custom_cta_text = Column(String, nullable=True)
    custom_cta_link = Column(String, nullable=True)
    # E.164 WhatsApp number for machine-owner PDF alerts (e.g. +33612345678)
    whatsapp_phone_e164 = Column(String, nullable=True)

    owned_devices = relationship("Device", back_populates="owner")
    device_owner_assignments = relationship("DeviceUserOwner", back_populates="user", cascade="all, delete-orphan")
    customers_created = relationship("Customer", back_populates="creator", foreign_keys="Customer.created_by")

class DeviceUserOwner(Base):
    """V1: multiple users can be owners of one device."""
    __tablename__ = "device_user_owners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", back_populates="user_owners")
    user = relationship("User", back_populates="device_owner_assignments")


class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    device_model = Column(String, nullable=True)   # e.g. "X10", "X18_5"
    mac_addr = Column(String, nullable=True)        # MAC address from payload
    unit_no = Column(String, nullable=True)         # unitNo from payload
    unit_name = Column(String, nullable=True)       # unitName from payload
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # legacy first owner
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="owned_devices")
    user_owners = relationship("DeviceUserOwner", back_populates="device", cascade="all, delete-orphan")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    dob = Column(DateTime(timezone=True), nullable=True)
    photo_url = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by], back_populates="customers_created")
    measurements = relationship("HealthMeasurement", back_populates="customer")

class OwnerNotificationLog(Base):
    """Audit trail for owner notifications (e.g. WhatsApp PDF)."""
    __tablename__ = "owner_notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    measurement_id = Column(UUID(as_uuid=True), ForeignKey("health_measurements.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    phone_e164 = Column(String, nullable=False)
    channel = Column(String, default="whatsapp", nullable=False)
    status = Column(String, nullable=False)  # sent | failed | skipped | disabled
    detail = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    error_type = Column(String, nullable=False, index=True)  # e.g., "POST_ERROR", "PROCESSING_ERROR", "VALIDATION_ERROR"
    error_message = Column(String, nullable=False)
    error_details = Column(JSONB, nullable=False)  # Full error details in JSONB format
    endpoint = Column(String, nullable=True, index=True)  # API endpoint where error occurred
    method = Column(String, nullable=True)  # HTTP method
    client_ip = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    request_body = Column(JSONB, nullable=True)  # Request body if available
    stack_trace = Column(String, nullable=True)  # Full stack trace
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
