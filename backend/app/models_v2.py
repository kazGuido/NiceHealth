"""
V2 models - White-label SaaS (organizations, locations, device ownership, etc.)
Additive to existing models. Same database.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base


class Organization(Base):
    """Machine owner / tenant (business entity)."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    workspace_url = Column(String, nullable=True)
    primary_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    primary_user = relationship("User", foreign_keys=[primary_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    organization_users = relationship("OrganizationUser", back_populates="organization", cascade="all, delete-orphan")
    measurements = relationship("HealthMeasurement", back_populates="organization")
    device_owners = relationship("DeviceOwner", back_populates="organization", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    measurement_prices = relationship("MeasurementPrice", back_populates="organization", cascade="all, delete-orphan")
    alert_preferences = relationship("AlertPreference", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    workspace_config = relationship("WorkspaceConfig", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    retail_user_invites = relationship("RetailUserInvite", back_populates="organization", cascade="all, delete-orphan")


class OrganizationUser(Base):
    """Links users to organizations (machine owner + delegated users)."""
    __tablename__ = "organization_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="organization_users")
    user = relationship("User", backref="organization_memberships")


class DeviceOwner(Base):
    """Many-to-many: device can have multiple organization owners."""
    __tablename__ = "device_owners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    device = relationship("Device", backref="device_owners")
    organization = relationship("Organization", back_populates="device_owners")


class Location(Base):
    """Location (machine owner specific). One location can have multiple devices."""
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="locations")
    devices = relationship("LocationDevice", back_populates="location", cascade="all, delete-orphan")
    measurements = relationship("HealthMeasurement", back_populates="location")


class LocationDevice(Base):
    """Many-to-many: location can have multiple devices."""
    __tablename__ = "location_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    location = relationship("Location", back_populates="devices")
    device = relationship("Device", backref="location_assignments")


class MeasurementPrice(Base):
    """Per-unit measurement price (machine owner specific, for offline billing)."""
    __tablename__ = "measurement_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="XAF", nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="measurement_prices")


class AlertPreference(Base):
    """Alert preferences (email, WhatsApp, etc.) per organization."""
    __tablename__ = "alert_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    email_address = Column(String, nullable=True)
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)
    whatsapp_number = Column(String, nullable=True)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    sms_number = Column(String, nullable=True)
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    telegram_chat_id = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="alert_preferences")


class WorkspaceConfig(Base):
    """Branding / workspace config per organization."""
    __tablename__ = "workspace_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String, nullable=True)
    brand_color = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    custom_domain = Column(String, nullable=True)
    primary_language = Column(String(10), default="en", nullable=True)
    dashboard_theme = Column(String(20), default="light", nullable=True)
    metrics_display = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="workspace_config")


class RetailUserInvite(Base):
    """Invite for retail user (end user) to register."""
    __tablename__ = "retail_user_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String, nullable=False)
    token = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="retail_user_invites")
