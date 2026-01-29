import asyncio
import json
import os
import typing

import aiofiles
import redis
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from silvasonic_dashboard.auth import require_auth
from silvasonic_dashboard.core.templates import templates
from silvasonic_dashboard.services import SystemService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/api/events/system")
async def sse_system_status(
    request: Request, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    async def event_generator() -> typing.AsyncGenerator[str, None]:
        # Connect to Redis
        r: redis.Redis = redis.Redis(
            host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1
        )

        last_system_status_raw: bytes | None = None

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Poll Redis for system:status
                # We do raw comparison to detect changes cheaply
                # Using get() is fast.

                # To be non-blocking in async loop, run in executor
                loop = asyncio.get_running_loop()
                current_raw = typing.cast(
                    bytes | None, await loop.run_in_executor(None, r.get, "system:status")
                )

                if current_raw and current_raw != last_system_status_raw:
                    last_system_status_raw = current_raw

                    # Logic duplicated from dashboard route (refactor ideally, but inline for now is robust)
                    stats = await SystemService.get_stats()  # Fresh stats
                    raw_containers = {}
                    try:
                        raw_containers = json.loads(current_raw)
                    except Exception:
                        pass

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

            # 1 second poll interval
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/api/logs/{service_name}", response_model=dict[str, str])
async def get_service_logs(
    service_name: str, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    """Get logs for a specific service."""
    if isinstance(auth, RedirectResponse):
        return auth

    from silvasonic_dashboard.core.constants import LOG_DIR

    log_file = os.path.join(LOG_DIR, f"{service_name}.log")
    if not os.path.exists(log_file):
        return {"content": f"Log file for {service_name} not found."}

    try:
        # Read last 1000 lines or full content (simple read for now as per tests)
        async with aiofiles.open(log_file) as f:
            content = await f.read()
            return {"content": content}
    except Exception as e:
        return {"content": f"Error reading logs: {str(e)}"}
