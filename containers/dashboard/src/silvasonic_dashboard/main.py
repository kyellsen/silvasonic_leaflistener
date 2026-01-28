import asyncio
import datetime
import json
import logging
import logging.handlers
import os

# Setup Logging
import sys
import threading
import time
import typing
from contextlib import asynccontextmanager

import psutil
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from silvasonic_dashboard.auth import COOKIE_NAME, SESSION_SECRET, require_auth, verify_credentials
from silvasonic_dashboard.services import (
    # AnalyzerService, # Deprecated
    BirdNetService,
    BirdNetStatsService,
    HealthCheckerService,
    RecorderService,
    SystemService,
    UploaderService,
    WeatherService,
)
from silvasonic_dashboard.settings import SettingsService
from starlette.status import HTTP_302_FOUND

# Initialize Paths with Fallbacks
LOG_DIR = os.getenv("LOG_DIR", "/var/log/silvasonic")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    # Check if writable
    if not os.access(LOG_DIR, os.W_OK):
        raise PermissionError(f"{LOG_DIR} is not writable")
except (PermissionError, OSError):
    LOG_DIR = os.path.join(os.getcwd(), ".logs")
    os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            os.path.join(LOG_DIR, "dashboard.log"),
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("Dashboard")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AUDIO_DIR = os.getenv("AUDIO_DIR", "/data/recording")

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "/data/processed/artifacts")
try:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    if not os.access(ARTIFACTS_DIR, os.W_OK):
        raise PermissionError(f"{ARTIFACTS_DIR} is not writable")
except (PermissionError, OSError):
    ARTIFACTS_DIR = os.path.join(os.getcwd(), ".artifacts")
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

CLIPS_DIR = "/data/db/results/clips"

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    # Startup: Start status writer in thread
    t = threading.Thread(target=write_status, daemon=True)
    t.start()

    # Start Stats Cache Manager
    try:
        from silvasonic_dashboard.services.stats_cache import StatsManager

        StatsManager.get_instance().start_background_task()
    except ImportError:
        logger.error("Failed to start StatsManager")

    yield
    # Shutdown logic can go here if needed


app = FastAPI(title="Silvasonic Dashboard", lifespan=lifespan)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def render(request: Request, template: str, context: dict[str, typing.Any]) -> typing.Any:
    # If HTMX request, we could try to render only the block,
    # BUT Jinja2 doesn't support block rendering easily without extensions.
    # ALTERNATIVE: Use the same template but let the base.html logic handle it?
    # NO, base.html has the sidebar. We need to swap ONLY the content.
    # Hack: Pass 'htmx' flag to template, and in base.html derive inheritance?
    # Better: If HTMX, render a partial template.
    # Simplest for now: Use the fact that we target #main-content.
    # We still send the full page but the client swaps correct part? NO bandwidth waste.

    # Correct HTMX Pattern with Jinja2:
    # Check header. If HX-Request, use a different "base" that is empty?
    if request.headers.get("HX-Request"):
        context["base"] = "partials/empty_base.html"
    else:
        context["base"] = "base.html"

    # Inject Global Context
    context["version"] = VERSION

    return templates.TemplateResponse(template, context)


# --- Self-Monitoring ---
def write_status() -> None:
    """Writes the Dashboard's own heartbeat."""
    status_file = "/mnt/data/services/silvasonic/status/dashboard.json"
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    while True:
        try:
            data = {
                "service": "dashboard",
                "timestamp": time.time(),
                "status": "Running",
                "cpu_percent": psutil.cpu_percent(),
                "memory_usage_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,
                "pid": os.getpid(),
            }

            tmp_file = f"{status_file}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f)
            os.rename(tmp_file, status_file)
        except Exception as e:
            logger.error(f"Failed to write dashboard status: {e}")

        time.sleep(5)  # Check every 5s


# Mount Static
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: typing.Callable[[Request], typing.Awaitable[typing.Any]]
) -> typing.Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> typing.Any:
    # Redirect to dashboard if authed, else login
    from silvasonic_dashboard.auth import check_auth

    if check_auth(request):
        return RedirectResponse("/dashboard", status_code=HTTP_302_FOUND)
    return RedirectResponse("/auth/login", status_code=HTTP_302_FOUND)


# --- Auth Routes ---
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request) -> typing.Any:
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/auth/login")
async def login_submit(
    request: Request, username: str = Form(...), password: str = Form(...)
) -> typing.Any:
    import asyncio

    if verify_credentials(username, password):
        response = RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
        response.set_cookie(
            key=COOKIE_NAME,
            value=SESSION_SECRET,
            httponly=True,
            samesite="lax",
            secure=False,  # Set to True if running behind HTTPS proxy
        )
        return response

    # Basic Rate Limiting / Brute Force Protection
    await asyncio.sleep(1.0)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid credentials"}
    )


@app.get("/auth/logout")
async def logout() -> typing.Any:
    response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response


# --- Protected Routes ---


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = await SystemService.get_stats()
    detections = await BirdNetService.get_recent_detections(limit=5)
    birdnet_stats = await BirdNetStatsService.get_stats()
    uploader_stats = UploaderService.get_status()
    recorder_stats = await RecorderService.get_status()
    raw_containers = HealthCheckerService.get_system_metrics()

    # Throughput / Lag Metrics
    # rec_rate = RecorderService.get_creation_rate(60) # Still useful info? User wants "concrete numbers" for lag.
    # But maybe "Recorder" status needs a metric? Maybe "Active" or files last hour.
    # Let's keep one rate for Recorder as "Heartbeat", but show Lag for others.

    # 1. Get Cursors
    latest_processed = await BirdNetService.get_latest_processed_filename()
    latest_uploaded = await UploaderService.get_latest_uploaded_filename()

    # 2. Calculate Lag (Files waiting)
    analyzer_lag = await RecorderService.count_files_after(latest_processed)
    uploader_lag = await RecorderService.count_files_after(latest_uploaded)

    # Status Logic (Thresholds)
    # 0-2 files: OK
    # 3-10: Pending
    # >10: Lagging
    def get_status(lag: int) -> str:
        if lag <= 2:
            return "ok"
        if lag <= 10:
            return "pending"
        return "lagging"

    # Fetch Recorder Statuses for Throughput
    recorder_statuses = recorder_stats
    recorders_throughput = []

    for r in recorder_statuses:
        # Determine strict activity (running vs idle) via file creation?
        # For now, trust the status "Running" if we had container stats,
        # but here we have the file-based status.
        # Actually RecorderService.get_status() returns data from json files written by containers.
        # Let's use that.
        # r = {"status": "Running", "meta": {...}, "profile": {...} }

        # We also want to support "Active" check via file rate per recorder?
        # That would require scanning folders per recorder.
        # RecorderService.get_creation_rate() is global.
        # Let's stick to the status reported by the container for now.

        is_active = r.get("status") == "Running"

        # Nicer display name
        display_name = r.get("device", "Unknown Recorder")
        if r.get("profile") and "name" in r.get("profile"):
            display_name = r["profile"]["name"]

        recorders_throughput.append(
            {
                "name": display_name,
                "is_active": is_active,
                "status": r.get("status", "Unknown"),
                "device": r.get("device", "Unknown"),
            }
        )

    throughput = {
        "recorder_active": (await RecorderService.get_creation_rate(10)) > 0,  # Global activity
        "recorders": recorders_throughput,  # List of individual recorders
        "analyzer_lag": analyzer_lag,
        "uploader_lag": uploader_lag,
        "analyzer_status": get_status(analyzer_lag),
        "uploader_status": get_status(uploader_lag),
    }

    # Define Sort Order & Display Names
    # Order: Liveaudio, Recorder, Uploader, BirdNet, Dashboard, PostgressDB, HealthChecker
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

    # helper to find container by fuzzy key
    def find_container(
        key_fragment: str, source_dict: dict[str, typing.Any]
    ) -> dict[str, typing.Any] | None:
        for k, v in source_dict.items():
            if key_fragment in k:
                return typing.cast(dict[str, typing.Any], v)
        return None

    for config in container_config:
        # Special handling for Recorder to support multiple
        if config["key"] == "recorder":
            # Find all keys starting with "recorder" in raw_containers
            recorders_found = [
                (k, v) for k, v in raw_containers.items() if k.startswith("recorder")
            ]

            if not recorders_found:
                # Add placeholder if none
                containers.append(
                    {
                        "id": "recorder",
                        "display_name": "Recorder",
                        "status": "Down",
                        "message": "Not Reported",
                    }
                )
            else:
                # Add all found recorders
                for _, v in recorders_found:
                    c_copy = v.copy()
                    # If name is generic "Recorder", append ID?
                    # HealthChecker already names them "Recorder (Front)" etc if profile matches
                    # If not, we rely on v["name"]
                    c_copy["display_name"] = v.get("name", "Recorder")
                    containers.append(c_copy)
            continue

        # Normal logic for others
        c = raw_containers.get(config["key"])
        if not c:
            c = find_container(config["key"], raw_containers)

        # If still not found, create a placeholder so the order is preserved
        if not c:
            c = {
                "id": config["key"],
                "display_name": config["name"],
                "status": "Down",  # Default to Down if missing
                "message": "Not Reported",
            }

        # Clone to avoid mutating original if cached
        c_copy = c.copy()
        c_copy["display_name"] = config["name"]
        containers.append(c_copy)

    # Add any others that weren't in the config?
    # Logic: simple Reorder.

    # Let's just pass the sorted list.
    containers_sorted = containers

    return render(
        request,
        "index.html",
        {
            "request": request,
            "page": "home",
            "stats": stats,
            "detections": detections,
            "birdnet_stats": birdnet_stats,
            "uploader_stats": uploader_stats,
            "recorder_stats": recorder_stats,
            "containers": containers_sorted,
            "throughput": throughput,
            "status_label": "System:",
            "status_value": "Online",
            "status_color": "text-green-600 dark:text-green-400",
            "auto_refresh_interval": 5,
        },
    )


@app.get("/api/events/system")
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

                    # Remove newlines for SSE safety (one line per data) - actually spec allows multi-line data if prefixed
                    # But htmx expects the payload.
                    # SSE Format:
                    # event: message
                    # data: <html>...</html>
                    # \n

                    # Escape newlines in data is properly handled if we prefix every line with data:
                    # But simplest is to compact it or just let stream_response handle it?
                    # No, we must format manually as per SSE spec or use sse-starlette.
                    # Manual implementation:

                    yield "event: system-overview\n"
                    # Handle multiline data
                    for line in content.splitlines():
                        yield f"data: {line}\n"
                    yield "\n"  # End of event

            except Exception as e:
                logger.error(f"SSE Error: {e}")

            await asyncio.sleep(1)  # Check frequency (Internal loop) faster than poll

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    settings = SettingsService.get_settings()

    return render(
        request,
        "settings.html",
        {
            "request": request,
            "page": "settings",
            "settings": settings,
            "status_label": "System:",
            "status_value": "Settings",
            "status_color": "text-gray-500",
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    return render(
        request,
        "about.html",
        {
            "request": request,
            "page": "about",
            "status_label": "System:",
            "status_value": "About",
            "status_color": "text-gray-500",
        },
    )


@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    form = await request.form()

    # Process Form
    use_german = form.get("use_german_names") == "on"
    notifier_email = str(form.get("notifier_email", "")).strip()
    apprise_urls_raw = str(form.get("apprise_urls", "")).strip()

    # Location
    try:
        latitude = float(str(form.get("latitude", 52.52)))
        longitude = float(str(form.get("longitude", 13.40)))
    except (ValueError, TypeError):
        latitude = 0.0  # Will likely fail validation if range logic works, or be valid but wrong.
        # Actually, let's keep the raw values or try parse?
        # If float conversion fails, it's invalid input.
        # But here we are converting safely. Pydantic will validate Range.
        latitude = 52.52  # Default fallback or 0?
        longitude = 13.40  # fallback
        # Ideally we pass raw to Pydantic but Pydantic expects types if we use Settings(**dict).
        # Let's trust the float conversion here for basic typing, Pydantic for Logic.

    # Parse URLs (comma separated)
    apprise_urls = [u.strip() for u in apprise_urls_raw.split(",") if u.strip()]

    # Load existing to preserve other fields if any
    settings = SettingsService.get_settings()

    if "locale" not in settings:
        settings["locale"] = {}
    settings["locale"]["use_german_names"] = use_german

    if "healthchecker" not in settings:
        settings["healthchecker"] = {}
    settings["healthchecker"]["recipient_email"] = notifier_email
    settings["healthchecker"]["apprise_urls"] = apprise_urls

    if "location" not in settings:
        settings["location"] = {}
    settings["location"]["latitude"] = latitude
    settings["location"]["latitude"] = latitude
    settings["location"]["longitude"] = longitude

    # BirdNET Form Parsing
    try:
        settings.setdefault("birdnet", {})
        settings["birdnet"]["min_confidence"] = float(str(form.get("birdnet_min_confidence", 0.7)))
        settings["birdnet"]["sensitivity"] = float(str(form.get("birdnet_sensitivity", 1.0)))
        settings["birdnet"]["overlap"] = float(str(form.get("birdnet_overlap", 0.0)))
    except (ValueError, TypeError):
        # Fallback to existing or defaults if bad input
        pass

    # Service Timeouts Parsing
    settings.setdefault("healthchecker", {}).setdefault("service_timeouts", {})
    # Default list of services to check for
    services = ["recorder", "birdnet", "sound_analyser", "weather", "uploader"]
    for svc in services:
        key = f"timeout_{svc}"
        val = form.get(key)
        if val:
            try:
                settings["healthchecker"]["service_timeouts"][svc] = int(str(val))
            except ValueError:
                pass  # Keep previous or default

    # Save
    msg = None
    err = None
    field_errors = {}

    try:
        from pydantic import ValidationError

        SettingsService.save_settings(settings)
        msg = "Settings saved successfully."
    except ValidationError as e:
        err = "Validation Error. Please check your inputs."
        # Parse Pydantic errors
        # e.errors() returns list of dicts: [{'loc': ('healthchecker', 'recipient_email'), 'msg': '...', 'type': '...'}]
        for error in e.errors():
            # Get the leaf field name
            loc = error["loc"]
            if loc:
                field_name = loc[-1]
                # Map to form field names if different
                # We use hierarchical names in Pydantic but flattened in Form?
                # Actually our form logic above maps Flattened Form -> Hierarchical Dict
                # So we need to map Hierarchical Error -> Flattened Form Field to show in UI

                # Mapping:
                # ('healthchecker', 'recipient_email') -> 'notifier_email'
                # ('location', 'latitude') -> 'latitude'

                if field_name == "recipient_email":
                    field_name = "notifier_email"
                # others match (latitude, longitude, use_german_names)

                field_errors[field_name] = error["msg"]

    except Exception as e:
        err = f"Failed to save settings: {e}"

    return render(
        request,
        "settings.html",
        {
            "request": request,
            "page": "settings",
            "settings": settings,  # Pass back the attempted settings so user doesn't lose input (partial)
            "success": msg,
            "error": err,
            "field_errors": field_errors,
            "status_label": "System:",
            "status_value": "Settings",
            "status_color": "text-gray-500",
        },
    )


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth
    return render(
        request,
        "logs.html",
        {
            "request": request,
            "page": "logs",
            "status_label": "System:",
            "status_value": "Logging",
            "status_color": "text-gray-500 dark:text-gray-400",
        },
    )


@app.get("/birdnet", response_class=HTMLResponse)
async def birdnet_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    detections = await BirdNetService.get_recent_detections(limit=50)  # More for browser
    stats = await BirdNetStatsService.get_stats()

    # New Data for "Analysis" view (Files)
    recent_files = await BirdNetService.get_recent_processed_files(limit=50)
    proc_stats = await BirdNetService.get_processing_stats()

    return render(
        request,
        "birdnet.html",
        {
            "request": request,
            "page": "birdnet",
            "detections": detections,
            "recent_files": recent_files,  # New
            "stats": stats,
            "proc_stats": proc_stats,  # New
            "status_label": "BirdNET:",
            "status_value": stats.get("status", "Active"),
            "status_color": "text-green-600 dark:text-green-400",
            "auto_refresh_interval": 5,
        },
    )


@app.get("/birdnet/discover", response_class=HTMLResponse)
async def birdnet_discover_page(
    request: Request, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    species_list = await BirdNetService.get_all_species()

    # Enrich with Watchlist Status
    sci_names = [s["sci_name"] for s in species_list]
    watchlist_status = await BirdNetService.get_watchlist_status(sci_names)

    for s in species_list:
        s["is_watched"] = watchlist_status.get(s["sci_name"], False)

    return render(
        request,
        "birdnet_discover.html",
        {
            "request": request,
            "page": "birdnet_discover",
            "species_list": species_list,
            "status_label": "BirdNET:",
            "status_value": "Discover",
            "status_color": "text-amber-500 dark:text-amber-400",
        },
    )


@app.get("/birdnet/discover/{species_name}", response_class=HTMLResponse)
async def birdnet_species_page(
    request: Request, species_name: str, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    data = await BirdNetStatsService.get_species_stats(species_name)
    if not data:
        raise HTTPException(status_code=404, detail="Species not found")

    # Enrich with Wikimedia Data (Async)
    data["info"] = await BirdNetService.enrich_species_data(data["info"])

    return render(
        request,
        "birdnet_species.html",
        {
            "request": request,
            "page": "birdnet_discover",
            "species": data["info"],
            "recent": data["recent"],
            "hourly": data["hourly"],
            "status_label": "BirdNET:",
            "status_value": species_name,
            "status_color": "text-amber-500 dark:text-amber-400",
        },
    )


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    auth: typing.Any = Depends(require_auth),
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    # Parse dates
    start_date = None
    end_date = None
    if start:
        try:
            start_date = datetime.date.fromisoformat(start)
        except ValueError:
            pass
    if end:
        try:
            end_date = datetime.date.fromisoformat(end)
        except ValueError:
            pass

    stats_data = await BirdNetStatsService.get_advanced_stats(start_date, end_date)

    return render(
        request,
        "stats.html",
        {
            "request": request,
            "page": "stats",
            "stats": stats_data,
            "status_label": "Statistics:",
            "status_value": "Detailed",
            "status_color": "text-blue-500 dark:text-blue-400",
        },
    )


@app.get("/recorder", response_class=HTMLResponse)
async def recorder_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = await RecorderService.get_status()
    # Also get system stats for context if needed
    sys_stats = await SystemService.get_stats()
    recordings = await RecorderService.get_recent_recordings()

    return render(
        request,
        "recorder.html",
        {
            "request": request,
            "page": "recorder",
            "stats": stats,  # Now a list
            "sys_stats": sys_stats,
            "recordings": recordings,
            "status_label": "Recorders:",
            "status_value": f"{len(stats)} Active",
            "status_color": "text-green-600 dark:text-green-400" if stats else "text-gray-500",
            "auto_refresh_interval": 5,
        },
    )


@app.get("/uploader", response_class=HTMLResponse)
async def uploader_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = UploaderService.get_status()
    upload_stats = await UploaderService.get_upload_stats()
    recent_uploads = await UploaderService.get_recent_uploads(limit=100)
    failed_uploads = await UploaderService.get_failed_uploads(limit=50)

    # Check for HTMX request
    template = (
        "partials/uploader_content.html" if request.headers.get("HX-Request") else "uploader.html"
    )

    return render(
        request,
        template,
        {
            "request": request,
            "page": "uploader",
            "stats": stats,
            "upload_stats": upload_stats,
            "recent_uploads": recent_uploads,
            "failed_uploads": failed_uploads,
            "status_label": "Uploader:",
            "status_value": stats.get("status", "Idle"),
            "status_color": "text-cyan-600 dark:text-cyan-400",
            "auto_refresh_interval": 5,
        },
    )


@app.get("/livesound", response_class=HTMLResponse)
async def livesound_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    # Fetch recorder stats to populate source dropdown
    recorder_stats = await RecorderService.get_status()

    return render(
        request,
        "livesound.html",
        {
            "request": request,
            "page": "livesound",
            "recorder_stats": recorder_stats,
            "status_label": "Livesound:",
            "status_value": "Streaming",
            "status_color": "text-purple-600 dark:text-purple-400",
            # Auto refresh not needed for live canvas/audio
            # "auto_refresh_interval": 15
        },
    )


@app.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    current = await WeatherService.get_current_weather()
    history = await WeatherService.get_history(hours=24)
    status_data = WeatherService.get_status()
    correlations = await WeatherService.get_correlations(days=30)

    return render(
        request,
        "weather.html",
        {
            "request": request,
            "page": "weather",
            "current": current,
            "history": history,
            "correlations": correlations,
            "status_label": "Weather:",
            "status_value": status_data.get("status", "Unknown"),
            "status_color": "text-blue-500 dark:text-blue-400"
            if status_data.get("status") == "Running"
            else "text-red-500",
            "auto_refresh_interval": 5,
        },
    )


# --- Inspector API Partials ---
# --- Inspector API Partials ---


class WatchlistToggleRequest(BaseModel):
    scientific_name: str
    common_name: str
    enabled: bool


@app.post("/api/watchlist/toggle")
async def api_toggle_watchlist(
    req: WatchlistToggleRequest, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    success = await BirdNetService.toggle_watchlist(
        req.scientific_name, req.common_name, req.enabled
    )
    if success:
        return {"status": "ok", "enabled": req.enabled}
    else:
        raise HTTPException(500, "Failed to toggle watchlist")


@app.get("/api/details/birdnet/{filename:path}", response_class=HTMLResponse)
async def get_birdnet_details(
    request: Request, filename: str, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    data = await BirdNetService.get_detection(filename)
    if not data:
        return "<div class='p-4 text-red-500'>Detection not found</div>"

    # Enrich if missing (async) - optional, or rely on what get_detection fetched (via join)
    # The join in get_detection might miss if not cached.
    # Let's trigger quick enrichment if basic info is missing but we have sci_name
    if not data.get("image_url") and data.get("sci_name"):
        # We trigger a background fetch or just Await it (better for user exp here)
        await BirdNetService.enrich_species_data(data)
        # Refresh data
        data = await BirdNetService.get_detection(filename) or data

    return render(request, "partials/inspector_birdnet.html", {"request": request, "d": data})


@app.get("/api/export/birdnet/csv")
async def export_birdnet_csv(auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    async def iter_csv() -> typing.AsyncGenerator[str, None]:
        # Header
        yield "Date,Time,Scientific Name,Common Name,Confidence,Start (s),End (s),Filename\n"

        # Rows
        iterator = BirdNetStatsService.get_all_detections_cursor()
        async for row in iterator:
            # Format fields
            ts = row.get("timestamp")

            date_str = ts.strftime("%Y-%m-%d") if ts else ""
            time_str = ts.strftime("%H:%M:%S") if ts else ""

            sci = (row.get("scientific_name") or "").replace(",", " ")  # Simple CSV escape
            com = (row.get("common_name") or "").replace(",", " ")
            conf = f"{row.get('confidence', 0.0):.2f}"
            start = f"{row.get('start_time', 0.0):.1f}"
            end = f"{row.get('end_time', 0.0):.1f}"
            fname = row.get("filename") or ""

            line = f"{date_str},{time_str},{sci},{com},{conf},{start},{end},{fname}\n"
            yield line

    filename = f"birdnet_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- API / HTMX Partials ---


@app.get("/api/logs/{service}")
async def get_logs(
    service: str, lines: int = 200, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    """Get last N lines of logs"""
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    log_file = os.path.join(LOG_DIR, f"{service}.log")

    if not os.path.exists(log_file):
        return {"content": f"Log file for {service} not found so far (waiting for creation)..."}

    try:
        # Simple tail implementation
        # For very large files, this might be inefficient, but log rotation keeps them sane (10MB-ish?)
        # Actually TimedRotatingFileHandler doesn't guarantee size, but we can assume reasonable checks.
        # Efficient tailing using seek is better.

        import aiofiles

        async with aiofiles.open(log_file):
            # Quick & Dirty: Read all lines? No, might be huge.
            # Seek to end and back up?
            # Subprocess tail is actually safest for large files on Linux.

            # Using tail command is robust
            proc = await asyncio.create_subprocess_exec(
                "tail",
                "-n",
                str(lines),
                log_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {"content": f"Error reading logs: {stderr.decode()}"}

            return {"content": stdout.decode(errors="replace")}

    except Exception as e:
        return {"content": f"Error accessing logs: {str(e)}"}


@app.get("/api/audio/{filename:path}")
async def stream_audio(filename: str, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    """Stream audio file from recording dir"""
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    # Security: Prevent traversing out of audio dir
    # filename here is actually a path potentially (e.g. "2023-10-27/bird.flac")

    # Sanitize:
    clean_path = os.path.normpath(filename).lstrip("/")

    # Construct full path
    full_path = os.path.join(AUDIO_DIR, clean_path)
    safe_path = os.path.abspath(full_path)

    # Verify it is still inside AUDIO_DIR
    if not safe_path.startswith(os.path.abspath(AUDIO_DIR)):
        raise HTTPException(403, "Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(404, "File not found")

    return FileResponse(safe_path, media_type="audio/flac")


@app.get("/api/clips/{filename:path}")
async def stream_clip(filename: str, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    """Stream clip from clips dir"""
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    # Sanitize
    clean_path = os.path.normpath(filename).lstrip("/")
    full_path = os.path.join(CLIPS_DIR, clean_path)
    safe_path = os.path.abspath(full_path)

    # Security check
    if not safe_path.startswith(os.path.abspath(CLIPS_DIR)):
        raise HTTPException(403, "Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(404, "Clip not found")

    return FileResponse(safe_path, media_type="audio/wav")


@app.get("/api/spectrogram/{filename:path}")
async def stream_spectrogram(filename: str, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    """Stream spectrogram from artifacts dir, generating it if needed (Lazy Loading)"""
    if isinstance(auth, RedirectResponse):
        raise HTTPException(401)

    # Path to the visual artifact (PNG)
    safe_path = os.path.normpath(os.path.join(ARTIFACTS_DIR, filename))

    # Security: Prevent traversing out of artifacts dir
    if not safe_path.startswith(ARTIFACTS_DIR):
        raise HTTPException(403, "Invalid path")

    # Lazy Loading Strategy:
    # 1. Check if the PNG exists.
    if not os.path.exists(safe_path):
        # 2. If not, check if we have the Source Audio
        # The filename for spectrogram usually is: {audio_filename}_spec.png
        # So we need to reconstruct the original audio filename.
        # Logic from sound_analyser/src/analyzers/spectrum.py:
        # artifact_name = f"{filename}_spec.png"
        # So if we have "recording.flac_spec.png", the audio is "recording.flac"

        if not filename.endswith("_spec.png"):
            raise HTTPException(404, "Invalid spectrogram filename format")

        audio_filename = filename.replace("_spec.png", "")
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        if not os.path.exists(audio_path):
            raise HTTPException(404, "Source audio for spectrogram not found")

        # 3. Generate it on the fly
        # This is invalidating the "read-only" constraint if ARTIFACTS_DIR is read-only?
        # Usually /data/processed is R/W.
        # Run in threadpool so we don't block the async loop
        import asyncio

        from src.spectrogram import generate_spectrogram

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, generate_spectrogram, audio_path, safe_path)

        if not success:
            raise HTTPException(500, "Failed to generate spectrogram")

    if not os.path.exists(safe_path):
        raise HTTPException(404, "Spectrogram not found")

    return FileResponse(safe_path, media_type="image/png")
