import asyncio
import os
import typing

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from silvasonic_dashboard.auth import require_auth
from silvasonic_dashboard.core.templates import templates
from silvasonic_dashboard.services import HealthCheckerService, SystemService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/api/events/system")
async def sse_system_status(
    request: Request, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    async def event_generator() -> typing.AsyncGenerator[str, None]:
        # Watch system_status.json for changes
        status_file = "/mnt/data/services/silvasonic/status/system_status.json"
        dashboard_stats_file = "/mnt/data/services/silvasonic/status/dashboard.json"  # Watch this too as it has disk stats

        last_mtime: float = 0.0
        last_dash_mtime: float = 0.0

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                changed = False

                # Check System Status File
                if os.path.exists(status_file):
                    mtime = os.path.getmtime(status_file)
                    if mtime > last_mtime:
                        last_mtime = mtime
                        changed = True

                # Check Dashboard Stats File (Disk usage)
                if os.path.exists(dashboard_stats_file):
                    mtime = os.path.getmtime(dashboard_stats_file)
                    if mtime > last_dash_mtime:
                        last_dash_mtime = mtime
                        changed = True  # Update if disk stats change

                if changed:
                    # Logic duplicated from dashboard route (refactor ideally, but inline for now is robust)
                    stats = await SystemService.get_stats()  # Fresh stats
                    raw_containers = HealthCheckerService.get_system_metrics()

                    # Construct Containers List (Same logic as dashboard view)
                    container_config = [
                        {"key": "livesound", "name": "Liveaudio"},
                        {"key": "controller", "name": "Controller"},
                        {"key": "recorder", "name": "Recorder"},
                        {"key": "uploader", "name": "Uploader"},
                        {"key": "birdnet", "name": "BirdNet"},
                        {"key": "dashboard", "name": "Dashboard"},
                        {"key": "postgres", "name": "PostgressDB"},
                        {"key": "healthchecker", "name": "HealthChecker"},
                    ]
                    containers = []

                    for config in container_config:
                        # Special handling for Recorder to support multiple
                        if config["key"] == "recorder":
                            # Find all keys starting with "recorder" in raw_containers
                            recorders_found = [
                                (k, v)
                                for k, v in raw_containers.items()
                                if k.startswith("recorder")
                            ]

                            if not recorders_found:
                                containers.append(
                                    {
                                        "id": "recorder",
                                        "display_name": "Recorder",
                                        "status": "Down",
                                        "message": "Not Reported",
                                    }
                                )
                            else:
                                for _, v in recorders_found:
                                    c_copy = v.copy()
                                    c_copy["display_name"] = v.get("name", "Recorder")
                                    containers.append(c_copy)
                            continue

                        c = raw_containers.get(config["key"])
                        if not c:
                            # Fuzzy search fallback
                            for k, v in raw_containers.items():
                                if config["key"] in k:
                                    c = v
                                    break

                        if not c:
                            c = {
                                "id": config["key"],
                                "display_name": config["name"],
                                "status": "Down",
                                "message": "Not Reported",
                            }

                        c_copy = c.copy()
                        c_copy["display_name"] = config["name"]
                        containers.append(c_copy)

                    # Render Partial
                    # We render the PARTIAL 'partials/system_overview.html'
                    # We must pass 'containers' and 'stats' as context
                    content = templates.get_template("partials/system_overview.html").render(
                        containers=containers, stats=stats
                    )

                    yield "event: system-overview\n"
                    # Handle multiline data
                    for line in content.splitlines():
                        yield f"data: {line}\n"
                    yield "\n"  # End of event

            except Exception as e:
                logger.error("SSE Error", error=str(e))

            await asyncio.sleep(1)  # Check frequency (Internal loop) faster than poll

    return StreamingResponse(event_generator(), media_type="text/event-stream")
