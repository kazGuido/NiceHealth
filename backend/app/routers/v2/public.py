"""
V2: Public endpoints (no auth) - location discovery for end users.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ...database import get_db
from ...models_v2 import Location, Organization, WorkspaceConfig
from ...schemas_v2 import LocationResponse

router = APIRouter(prefix="/public", tags=["v2-public"])


@router.get("/locations", response_model=List[LocationResponse])
async def list_public_locations(
    organization_id: Optional[UUID] = Query(None, description="Filter by organization (machine owner)"),
    db: Session = Depends(get_db)
):
    """
    List locations where measurements can be done.
    End users can see all locations or filter by specific machine owner.
    """
    query = db.query(Location).filter(Location.is_active == True)
    if organization_id:
        query = query.filter(Location.organization_id == organization_id)
    return query.all()


@router.get("/organizations")
async def list_public_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List organizations (machine owners) with workspace branding.
    End users can browse to find where to get measurements.
    """
    orgs = db.query(Organization).filter(Organization.is_active == True).offset(skip).limit(limit).all()
    result = []
    for org in orgs:
        config = db.query(WorkspaceConfig).filter(WorkspaceConfig.organization_id == org.id).first()
        result.append({
            "id": org.id,
            "name": org.name,
            "workspace_url": org.workspace_url,
            "brand_name": config.brand_name if config else org.name,
            "brand_color": config.brand_color if config else "#3B82F6",
            "logo_url": config.logo_url if config else None,
        })
    return result
