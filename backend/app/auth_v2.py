"""
V2 auth helpers - role-based access for admin, customer (machine owner), retail user.
"""
from typing import Optional, List
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import User, Device
from .models_v2 import Organization, DeviceOwner, OrganizationUser


def get_current_admin_user_v2(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_current_customer_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Require customer (machine owner) role."""
    if current_user.role not in ("admin", "customer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer (machine owner) access required"
        )
    return current_user


async def get_current_retail_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require retail user role."""
    if current_user.role not in ("admin", "retail"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retail user access required"
        )
    return current_user


def get_organizations_for_user(db: Session, user: User) -> List[Organization]:
    """Get organizations the user can access (as primary or member)."""
    if user.role == "admin":
        return db.query(Organization).filter(Organization.is_active == True).all()

    org_ids = set()
    # Primary user of org
    for org in db.query(Organization).filter(
        Organization.primary_user_id == user.id,
        Organization.is_active == True
    ).all():
        org_ids.add(org.id)
    # Member of org
    for ou in db.query(OrganizationUser).filter(OrganizationUser.user_id == user.id).all():
        org = db.query(Organization).filter(Organization.id == ou.organization_id, Organization.is_active == True).first()
        if org:
            org_ids.add(org.id)

    return db.query(Organization).filter(Organization.id.in_(org_ids)).all() if org_ids else []


def get_organization_ids_for_user(db: Session, user: User) -> List[UUID]:
    """Get organization IDs the user can access."""
    orgs = get_organizations_for_user(db, user)
    return [o.id for o in orgs]


def user_can_access_device(db: Session, user: User, device_id_str: str) -> bool:
    """
    Check if user can access a device (by device_id string from payload).
    - Admin: always
    - Customer: if device is owned by one of their organizations
    - Device with no owners: any customer can access
    """
    if user.role == "admin":
        return True

    device = db.query(Device).filter(Device.device_id == device_id_str).first()
    if not device:
        return False

    owners = db.query(DeviceOwner).filter(DeviceOwner.device_id == device.id).all()
    if not owners:
        return True  # Public device - any customer can access

    org_ids = get_organization_ids_for_user(db, user)
    for do in owners:
        if do.organization_id in org_ids:
            return True
    return False


def user_can_access_organization(db: Session, user: User, organization_id: UUID) -> bool:
    """Check if user can access an organization."""
    if user.role == "admin":
        return True
    org_ids = get_organization_ids_for_user(db, user)
    return organization_id in org_ids
