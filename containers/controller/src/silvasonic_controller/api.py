import json
from typing import Any, cast

import redis
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

    # Fetch System Status from Redis
    system_status = {}
    try:
        r: redis.Redis = redis.Redis(
            host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=0.5
        )
        raw = cast(bytes | None, r.get("system:status"))
        if raw:
            system_status = json.loads(raw)
    except Exception:
        # If Redis fails, we default to Unknown statuses
        pass

    # Generic Services
    for name, config in ctrl.service_manager._services.items():
        # Lookup in system_status
        # system_status keys are instance_ids. For singletons, id=name.
        # But name in ServiceManager might be "uploader", system_status has "uploader" or "uploader_sensor1".
        # We try exact match first.
        s_data = system_status.get(name, {})
        status_str = s_data.get("status", "Unknown")

        statuses.append(
            ServiceStatus(
                name=name,
                enabled=config.enabled,
                status=status_str,
            )
        )

    # Recorders
    # Controller knows active sessions (Desired State).
    # System Status has actual state (Reported State).
    # structure of system_status for recorders: "recorder_front", "recorder_back".
    for _card_id, session in ctrl.active_sessions.items():
        rec_id = f"recorder_{session.rec_id}"
        s_data = system_status.get(rec_id, {})
        status_str = s_data.get("status", "Unknown")

        statuses.append(ServiceStatus(name=rec_id, enabled=True, status=status_str))

    # Also include any other services found in system_status that are not in _services?
    # e.g. "postgres", "healthchecker".
    # For now, UI might only expect specific list, but let's add core infra if invalid?
    # The API filter seems to be "managed services". Postgres/Healthchecker are static.
    # Controller usually manages Dynamic services.
    # But for visibility, we might want them.
    # Current API contract: get_status() -> list[ServiceStatus].
    # Let's stick to managed + recorders for now to avoid UI clutter of duplicates or unmanaged items.

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
