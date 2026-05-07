"""
V2 Admin: Organization (machine owner) management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import logging

from ...database import get_db
from ...models import User
from ...models_v2 import Organization, OrganizationUser
from ...schemas_v2 import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from ...auth_v2 import get_current_admin_user_v2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/organizations", tags=["v2-admin"])


@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Create a new organization (machine owner)."""
    org = Organization(
        name=body.name,
        workspace_url=body.workspace_url,
        primary_user_id=body.primary_user_id,
        created_by=admin.id,
        is_active=True
    )
    db.add(org)
    db.flush()

    if body.primary_user_id:
        ou = OrganizationUser(
            organization_id=org.id,
            user_id=body.primary_user_id,
            is_primary=True
        )
        db.add(ou)

    db.commit()
    db.refresh(org)
    logger.info(f"Admin {admin.email} created organization {org.name}")
    return org


@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: List all organizations."""
    return db.query(Organization).order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Get organization details."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    body: OrganizationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Update organization."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(org, k, v)

    db.commit()
    db.refresh(org)
    logger.info(f"Admin {admin.email} updated organization {organization_id}")
    return org


@router.delete("/{organization_id}", status_code=204)
async def deactivate_organization(
    organization_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user_v2)
):
    """Admin: Deactivate organization (soft delete)."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.is_active = False
    db.commit()
    logger.info(f"Admin {admin.email} deactivated organization {organization_id}")
    return None
