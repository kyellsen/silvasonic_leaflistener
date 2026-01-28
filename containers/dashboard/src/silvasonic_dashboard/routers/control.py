from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from silvasonic_dashboard.models import SystemConfig, SystemService
from silvasonic_dashboard.services.database import db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/control", tags=["Control"])


# Pydantic Schemas
class ServiceStateResponse(BaseModel):
    service_name: str
    enabled: bool
    status: str = "unknown"  # status quo in DB logic


class ServiceToggleRequest(BaseModel):
    enabled: bool


class ConfigResponse(BaseModel):
    key: str
    value: str | None
    description: str | None


class ConfigUpdateRequest(BaseModel):
    value: str


# Endpoints
@router.get("/services", response_model=list[ServiceStateResponse])
async def list_services(session: AsyncSession = Depends(db.get_db)) -> Any:
    """List all services and their target state."""
    result = await session.execute(select(SystemService))
    services = result.scalars().all()

    # We map 'enabled' to target state. Real running status would require querying Controller API
    # For this task, we return DB state.
    response = []
    for svc in services:
        response.append(
            ServiceStateResponse(
                service_name=svc.service_name,
                enabled=svc.enabled,
                status="enabled" if svc.enabled else "disabled",
            )
        )
    return response


@router.post("/services/{service_name}", response_model=ServiceStateResponse)
async def toggle_service(
    service_name: str, toggle: ServiceToggleRequest, session: AsyncSession = Depends(db.get_db)
) -> Any:
    """Enable or disable a service."""
    # Check existence
    result = await session.execute(
        select(SystemService).where(SystemService.service_name == service_name)
    )
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Update
    service.enabled = toggle.enabled
    await session.commit()
    await session.refresh(service)

    # TODO: Trigger Controller Notification here

    return ServiceStateResponse(
        service_name=service.service_name,
        enabled=service.enabled,
        status="enabled" if service.enabled else "disabled",
    )


@router.get("/config", response_model=list[ConfigResponse])
async def list_config(session: AsyncSession = Depends(db.get_db)) -> Any:
    """List all system configurations."""
    result = await session.execute(select(SystemConfig))
    configs = result.scalars().all()
    return [ConfigResponse(key=c.key, value=c.value, description=c.description) for c in configs]


@router.patch("/config/{key}", response_model=ConfigResponse)
async def update_config(
    key: str, update_data: ConfigUpdateRequest, session: AsyncSession = Depends(db.get_db)
) -> Any:
    """Update a configuration value."""
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config key not found")

    config.value = update_data.value
    await session.commit()
    await session.refresh(config)

    return ConfigResponse(key=config.key, value=config.value, description=config.description)
