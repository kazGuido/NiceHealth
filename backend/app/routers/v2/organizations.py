"""
V2 Customer (machine owner): Locations, pricing, alerts, workspace, retail invites.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging

from ...database import get_db
from ...models import User, Device
from ...models_v2 import (
    Organization,
    OrganizationUser,
    Location,
    LocationDevice,
    DeviceOwner,
    MeasurementPrice,
    AlertPreference,
    WorkspaceConfig,
    RetailUserInvite,
)
from ...schemas_v2 import (
    LocationCreate,
    LocationUpdate,
    LocationDeviceAdd,
    LocationResponse,
    MeasurementPriceCreate,
    MeasurementPriceUpdate,
    MeasurementPriceResponse,
    AlertPreferenceUpdate,
    AlertPreferenceResponse,
    WorkspaceConfigUpdate,
    WorkspaceConfigResponse,
    RetailUserInviteCreate,
    RetailUserInviteResponse,
)
from ...auth_v2 import get_current_customer_user, get_organization_ids_for_user
from ...auth import generate_pin, hash_pin
from ...email_service import send_pin_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["v2-organizations"])


def _get_primary_organization(db: Session, user: User) -> Optional[Organization]:
    """Get user's primary organization (first one they own or are member of)."""
    if user.role == "admin":
        return db.query(Organization).filter(Organization.is_active == True).first()
    org = db.query(Organization).filter(
        Organization.primary_user_id == user.id,
        Organization.is_active == True
    ).first()
    if org:
        return org
    ou = db.query(OrganizationUser).filter(OrganizationUser.user_id == user.id).first()
    if ou:
        return db.query(Organization).filter(Organization.id == ou.organization_id).first()
    return None


def _require_org_access(db: Session, user: User, organization_id: UUID) -> Organization:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if user.role != "admin" and organization_id not in get_organization_ids_for_user(db, user):
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    return org


def _get_org_or_raise(db: Session, user: User, organization_id: Optional[UUID]) -> Organization:
    """Get org by id or primary org. Raises if none."""
    if organization_id:
        return _require_org_access(db, user, organization_id)
    org = _get_primary_organization(db, user)
    if not org:
        raise HTTPException(status_code=400, detail="No organization found. Specify organization_id or ensure you are linked to an organization.")
    return org


# --- Locations ---
@router.post("/me/locations", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Create a location for the current organization."""
    org = _get_org_or_raise(db, current_user, organization_id)
    loc = Location(
        organization_id=org.id,
        name=body.name,
        address=body.address,
        phone=body.phone,
        is_active=True
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    logger.info(f"User {current_user.email} created location {loc.name}")
    return loc


@router.get("/me/locations", response_model=List[LocationResponse])
async def list_locations(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """List locations for the current organization(s)."""
    org_ids = get_organization_ids_for_user(db, current_user)
    query = db.query(Location).filter(Location.organization_id.in_(org_ids), Location.is_active == True)
    if organization_id:
        _require_org_access(db, current_user, organization_id)
        query = query.filter(Location.organization_id == organization_id)
    return query.all()


@router.get("/me/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Get location details."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    _require_org_access(db, current_user, loc.organization_id)
    return loc


@router.patch("/me/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    body: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Update location."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    _require_org_access(db, current_user, loc.organization_id)
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(loc, k, v)
    db.commit()
    db.refresh(loc)
    return loc


@router.post("/me/locations/{location_id}/devices")
async def add_device_to_location(
    location_id: UUID,
    body: LocationDeviceAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Add a device to a location."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    _require_org_access(db, current_user, loc.organization_id)
    device = db.query(Device).filter(Device.id == body.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    existing = db.query(LocationDevice).filter(
        LocationDevice.location_id == location_id,
        LocationDevice.device_id == body.device_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already in location")
    ld = LocationDevice(location_id=location_id, device_id=body.device_id)
    db.add(ld)
    db.commit()
    return {"message": "Device added to location"}


@router.delete("/me/locations/{location_id}/devices/{device_id}", status_code=204)
async def remove_device_from_location(
    location_id: UUID,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Remove a device from a location."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    _require_org_access(db, current_user, loc.organization_id)
    ld = db.query(LocationDevice).filter(
        LocationDevice.location_id == location_id,
        LocationDevice.device_id == device_id
    ).first()
    if ld:
        db.delete(ld)
        db.commit()
    return None


@router.delete("/me/locations/{location_id}", status_code=204)
async def deactivate_location(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Deactivate location."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    _require_org_access(db, current_user, loc.organization_id)
    loc.is_active = False
    db.commit()
    return None


# --- Measurement Price ---
@router.post("/me/pricing", response_model=MeasurementPriceResponse, status_code=201)
async def create_pricing(
    body: MeasurementPriceCreate,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Set measurement price for organization (informational, offline billing)."""
    org = _get_org_or_raise(db, current_user, organization_id)
    price = MeasurementPrice(
        organization_id=org.id,
        price=body.price,
        currency=body.currency,
        is_active=True
    )
    db.add(price)
    db.commit()
    db.refresh(price)
    return price


@router.get("/me/pricing", response_model=List[MeasurementPriceResponse])
async def list_pricing(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Get pricing for organization(s)."""
    org_ids = get_organization_ids_for_user(db, current_user)
    query = db.query(MeasurementPrice).filter(MeasurementPrice.organization_id.in_(org_ids), MeasurementPrice.is_active == True)
    if organization_id:
        _require_org_access(db, current_user, organization_id)
        query = query.filter(MeasurementPrice.organization_id == organization_id)
    return query.all()


@router.patch("/me/pricing/{price_id}", response_model=MeasurementPriceResponse)
async def update_pricing(
    price_id: UUID,
    body: MeasurementPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Update pricing."""
    price = db.query(MeasurementPrice).filter(MeasurementPrice.id == price_id).first()
    if not price:
        raise HTTPException(status_code=404, detail="Pricing not found")
    _require_org_access(db, current_user, price.organization_id)
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(price, k, v)
    db.commit()
    db.refresh(price)
    return price


# --- Alert Preferences ---
@router.get("/me/alerts", response_model=Optional[AlertPreferenceResponse])
async def get_alerts(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Get alert preferences."""
    org = _get_org_or_raise(db, current_user, organization_id)
    pref = db.query(AlertPreference).filter(AlertPreference.organization_id == org.id).first()
    return pref


@router.patch("/me/alerts", response_model=AlertPreferenceResponse)
async def update_alerts(
    body: AlertPreferenceUpdate,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Create or update alert preferences."""
    org = _get_org_or_raise(db, current_user, organization_id)
    pref = db.query(AlertPreference).filter(AlertPreference.organization_id == org.id).first()
    if not pref:
        pref = AlertPreference(organization_id=org.id)
        db.add(pref)
        db.flush()
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(pref, k, v)
    db.commit()
    db.refresh(pref)
    return pref


# --- Workspace Config ---
@router.get("/me/workspace", response_model=Optional[WorkspaceConfigResponse])
async def get_workspace(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Get workspace branding config."""
    org = _get_org_or_raise(db, current_user, organization_id)
    config = db.query(WorkspaceConfig).filter(WorkspaceConfig.organization_id == org.id).first()
    return config


@router.patch("/me/workspace", response_model=WorkspaceConfigResponse)
async def update_workspace(
    body: WorkspaceConfigUpdate,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Create or update workspace branding."""
    org = _get_org_or_raise(db, current_user, organization_id)
    config = db.query(WorkspaceConfig).filter(WorkspaceConfig.organization_id == org.id).first()
    if not config:
        config = WorkspaceConfig(organization_id=org.id)
        db.add(config)
        db.flush()
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(config, k, v)
    db.commit()
    db.refresh(config)
    return config


# --- Retail User Invites ---
@router.post("/me/retail-users/invite", response_model=RetailUserInviteResponse, status_code=201)
async def invite_retail_user(
    body: RetailUserInviteCreate,
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """Invite a retail user via email. Sends PIN to register."""
    org = _get_org_or_raise(db, current_user, organization_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invite = RetailUserInvite(
        organization_id=org.id,
        email=body.email.lower(),
        expires_at=expires_at
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    # TODO: Send invite email with link containing token
    logger.info(f"User {current_user.email} invited retail user {body.email}")
    return invite


@router.get("/me/retail-users/invites", response_model=List[RetailUserInviteResponse])
async def list_invites(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """List retail user invites for organization."""
    org_ids = get_organization_ids_for_user(db, current_user)
    return db.query(RetailUserInvite).filter(RetailUserInvite.organization_id.in_(org_ids)).order_by(RetailUserInvite.created_at.desc()).all()
