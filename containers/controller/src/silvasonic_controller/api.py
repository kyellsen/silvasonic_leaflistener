from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

# We will inject the controller instance dynamically
# to avoid circular imports or complex globals if possible.
# But for simplicity in this architecture, we might set a global on startup.

app = FastAPI(title="Silvasonic Controller API")


class ServiceStatus(BaseModel):
    name: str
    enabled: bool
    status: str  # Running, Stopped, etc.


class ToggleRequest(BaseModel):
    enabled: bool


# Global reference to controller, set by main.py
controller_instance: Any | None = None


def get_controller() -> Any:
    if controller_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Controller not initialized"
        )
    return controller_instance


@app.get("/status", response_model=list[ServiceStatus])
async def get_status() -> list[ServiceStatus]:
    """Get status of all managed services."""
    ctrl = get_controller()

    # This logic assumes ServiceManager is available on Controller
    # We haven't added it to Controller class yet, but we will in main.py updates.
    if not hasattr(ctrl, "service_manager"):
        raise HTTPException(status_code=500, detail="Service Manager not available")

    statuses = []
    # Generic Services
    for name, config in ctrl.service_manager._services.items():
        # TODO: Check actual running status from orchestrator or cache
        statuses.append(
            ServiceStatus(
                name=name,
                enabled=config.enabled,
                status="Unknown",  # We need to link real status later
            )
        )

    # Recorders
    for _card_id, session in ctrl.active_sessions.items():
        statuses.append(
            ServiceStatus(name=f"recorder_{session.rec_id}", enabled=True, status="Running")
        )

    return statuses


@app.post("/services/{name}/toggle")
async def toggle_service(name: str, req: ToggleRequest) -> dict[str, Any]:
    """Enable or Disable a service."""
    ctrl = get_controller()

    # Logic to toggle service in DB/Registry and trigger reconcile
    # For now, we update the in-memory registry of ServiceManager
    if hasattr(ctrl, "service_manager"):
        mgr = ctrl.service_manager
        if name in mgr._services:
            mgr._services[name].enabled = req.enabled

            if req.enabled:
                await mgr.start_service(name)
            else:
                await mgr.stop_service(name)

            return {"status": "updated", "enabled": req.enabled}

    raise HTTPException(status_code=404, detail="Service not found")
