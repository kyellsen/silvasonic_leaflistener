import logging
import logging.handlers
import os

# Setup Logging
import sys

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.auth import COOKIE_NAME, SESSION_SECRET, require_auth, verify_credentials
from starlette.status import HTTP_302_FOUND

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.TimedRotatingFileHandler(
            "/var/log/silvasonic/dashboard.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("Dashboard")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AUDIO_DIR = "/data/recording"
LOG_DIR = "/var/log/silvasonic"
ARTIFACTS_DIR = "/data/processed/artifacts"

VERSION = "0.1.0"

app = FastAPI(title="Silvasonic Dashboard")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def render(request: Request, template: str, context: dict):
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

# We need a partial base that outputs only the blocks


# Mount Static
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Redirect to dashboard if authed, else login
    from src.auth import check_auth
    if check_auth(request):
        return RedirectResponse("/dashboard", status_code=HTTP_302_FOUND)
    return RedirectResponse("/auth/login", status_code=HTTP_302_FOUND)

# --- Auth Routes ---
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/auth/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    import asyncio
    if verify_credentials(username, password):
        response = RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
        response.set_cookie(
            key=COOKIE_NAME,
            value=SESSION_SECRET,
            httponly=True,
            samesite="lax",
            secure=False # Set to True if running behind HTTPS proxy
        )
        return response

    # Basic Rate Limiting / Brute Force Protection
    await asyncio.sleep(1.0)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response

# --- Protected Routes ---

from src.services import (
    # AnalyzerService, # Deprecated
    BirdNetService,
    CarrierService,
    HealthCheckerService,
    RecorderService,
    SystemService,
    WeatherService,
)
from src.settings import SettingsService


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    stats = SystemService.get_stats()
    detections = await BirdNetService.get_recent_detections(limit=5)
    birdnet_stats = await BirdNetService.get_stats()
    carrier_stats = CarrierService.get_status()
    recorder_stats = RecorderService.get_status()
    raw_containers = HealthCheckerService.get_system_metrics()

    # Throughput Metrics (Last 60 mins)
    rec_rate = RecorderService.get_creation_rate(60)
    process_rate = await BirdNetService.get_processing_rate(60)
    upload_rate = await CarrierService.get_upload_rate(60)

    throughput = {
        "recorder": rec_rate,
        "analyzer": process_rate,
        "uploader": upload_rate,
        # Status Logic
        # If analyzer < recorder (with margin), it's lagging.
        # Margin: 10% tolerance? Or simple comparison.
        # If analyzer is 0 and recorder > 0, strict lag.
        "analyzer_status": "ok" if process_rate >= (rec_rate * 0.9) else "lagging",
        "uploader_status": "ok" if upload_rate >= (rec_rate * 0.9) else "lagging"
    }
    
    # Correction: If recorder is 0, then we are not lagging even if 0.
    if rec_rate == 0:
        throughput["analyzer_status"] = "ok"
        throughput["uploader_status"] = "ok"
        
    # Define Sort Order & Display Names
    # Order: Recorder, Carrier, LiveSound, Birdnet, Weather, PostgressDB, HealthChecker
    container_config = [
        {"key": "recorder", "name": "Recorder"},
        {"key": "uploader", "name": "Uploader"},
        {"key": "livesound", "name": "Livesound"},
        {"key": "birdnet", "name": "Birdnet"},
        {"key": "weather", "name": "Weather"},
        {"key": "postgres", "name": "Postgress"},
        {"key": "healthchecker", "name": "HealthChecker"},
    ]
    
    containers = []
    
    # helper to find container by fuzzy key
    def find_container(key_fragment, source_dict):
        for k, v in source_dict.items():
            if key_fragment in k:
                return v
        return None

    for config in container_config:
        # Try exact match first, then fuzzy
        c = raw_containers.get(config["key"])
        if not c:
            c = find_container(config["key"], raw_containers)
        
        if c:
            # Clone to avoid mutating original if cached
            c_copy = c.copy()
            c_copy["display_name"] = config["name"]
            containers.append(c_copy)
        else:
            # Optional: Add placeholder if missing? Or skip.
            # User wants specific order, maybe show even if missing/unknown status?
            # For now, let's add a placeholder to ensure the grid structure is preserved if that's desired,
            # but usually we only show what's reported.
            # However, looking at the template, it iterates what's there.
            # Let's try to simulate a 'down' state if missing?
            # actually, if HealthChecker doesn't report it, it might not exist. 
            # safe to skip or add as 'Unknown'.
            pass

    # Add any others that weren't in the config?
    # Logic: simple Reorder.
    
    # Let's just pass the sorted list.
    containers_sorted = containers

    return render(request, "index.html", {
        "request": request,
        "page": "home",
        "stats": stats,
        "detections": detections,
        "birdnet_stats": birdnet_stats,
        "carrier_stats": carrier_stats,
        "recorder_stats": recorder_stats,
        "carrier_stats": carrier_stats,
        "recorder_stats": recorder_stats,
        "containers": containers_sorted,
        "throughput": throughput,
        "status_label": "System:",
        "status_value": "Online",
        "status_color": "text-green-600 dark:text-green-400",
        "auto_refresh_interval": 15
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    settings = SettingsService.get_settings()

    return render(request, "settings.html", {
        "request": request,
        "page": "settings",
        "settings": settings,
        "status_label": "System:",
        "status_value": "Settings",
        "status_color": "text-gray-500"
    })

@app.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    form = await request.form()

    # Process Form
    use_german = form.get("use_german_names") == "on"
    notifier_email = form.get("notifier_email", "").strip()
    apprise_urls_raw = form.get("apprise_urls", "").strip()

    # Location
    try:
        latitude = float(form.get("latitude", 52.52))
        longitude = float(form.get("longitude", 13.40))
    except (ValueError, TypeError):
        latitude = 0.0 # Will likely fail validation if range logic works, or be valid but wrong.
        # Actually, let's keep the raw values or try parse?
        # If float conversion fails, it's invalid input.
        # But here we are converting safely. Pydantic will validate Range.
        latitude = 52.52 # Default fallback or 0?
        longitude = 13.40 # fallback
        # Ideally we pass raw to Pydantic but Pydantic expects types if we use Settings(**dict).
        # Let's trust the float conversion here for basic typing, Pydantic for Logic.

    # Parse URLs (comma separated)
    apprise_urls = [u.strip() for u in apprise_urls_raw.split(',') if u.strip()]

    # Load existing to preserve other fields if any
    settings = SettingsService.get_settings()

    if "locale" not in settings: settings["locale"] = {}
    settings["locale"]["use_german_names"] = use_german

    if "healthchecker" not in settings: settings["healthchecker"] = {}
    settings["healthchecker"]["recipient_email"] = notifier_email
    settings["healthchecker"]["apprise_urls"] = apprise_urls

    if "location" not in settings: settings["location"] = {}
    settings["location"]["latitude"] = latitude
    settings["location"]["latitude"] = latitude
    settings["location"]["longitude"] = longitude

    # BirdNET Form Parsing
    try:
        settings.setdefault("birdnet", {})
        settings["birdnet"]["min_confidence"] = float(form.get("birdnet_min_confidence", 0.7))
        settings["birdnet"]["sensitivity"] = float(form.get("birdnet_sensitivity", 1.0))
        settings["birdnet"]["overlap"] = float(form.get("birdnet_overlap", 0.0))
    except (ValueError, TypeError):
        # Fallback to existing or defaults if bad input
        pass

    # Service Timeouts Parsing
    settings.setdefault("healthchecker", {}).setdefault("service_timeouts", {})
    # Default list of services to check for
    services = ["recorder", "birdnet", "sound_analyser", "weather", "carrier"]
    for svc in services:
        key = f"timeout_{svc}"
        val = form.get(key)
        if val:
            try:
                settings["healthchecker"]["service_timeouts"][svc] = int(val)
            except ValueError:
                pass # Keep previous or default

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
            loc = error['loc']
            if loc:
                field_name = loc[-1]
                # Map to form field names if different
                # We use hierarchical names in Pydantic but flattened in Form?
                # Actually our form logic above maps Flattened Form -> Hierarchical Dict
                # So we need to map Hierarchical Error -> Flattened Form Field to show in UI

                # Mapping:
                # ('healthchecker', 'recipient_email') -> 'notifier_email'
                # ('location', 'latitude') -> 'latitude'

                if field_name == 'recipient_email': field_name = 'notifier_email'
                # others match (latitude, longitude, use_german_names)

                field_errors[field_name] = error['msg']

    except Exception as e:
        err = f"Failed to save settings: {e}"

    return render(request, "settings.html", {
        "request": request,
        "page": "settings",
        "settings": settings, # Pass back the attempted settings so user doesn't lose input (partial)
        "success": msg,
        "error": err,
        "field_errors": field_errors,
        "status_label": "System:",
        "status_value": "Settings",
        "status_color": "text-gray-500"
    })

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    return render(request, "logs.html", {
        "request": request,
        "page": "logs",
        "status_label": "System:",
        "status_value": "Logging",
        "status_color": "text-gray-500 dark:text-gray-400"
    })

@app.get("/birdnet", response_class=HTMLResponse)
async def birdnet_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    detections = await BirdNetService.get_recent_detections(limit=50) # More for browser
    stats = await BirdNetService.get_stats()

    return render(request, "birdnet.html", {
        "request": request,
        "page": "birdnet",
        "detections": detections,
        "stats": stats,
        "status_label": "BirdNET:",
        "status_value": stats.get("status", "Active"),
        "status_color": "text-green-600 dark:text-green-400",
        "auto_refresh_interval": 15
    })

@app.get("/birdnet/discover", response_class=HTMLResponse)
async def birdnet_discover_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    species_list = await BirdNetService.get_all_species()

    # Enrich with Watchlist Status
    sci_names = [s['sci_name'] for s in species_list]
    watchlist_status = await BirdNetService.get_watchlist_status(sci_names)

    for s in species_list:
        s['is_watched'] = watchlist_status.get(s['sci_name'], False)

    return render(request, "birdnet_discover.html", {
        "request": request,
        "page": "birdnet_discover",
        "species_list": species_list,
        "status_label": "BirdNET:",
        "status_value": "Discover",
        "status_color": "text-amber-500 dark:text-amber-400"
    })

@app.get("/birdnet/discover/{species_name}", response_class=HTMLResponse)
async def birdnet_species_page(request: Request, species_name: str, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    data = await BirdNetService.get_species_stats(species_name)
    if not data:
        raise HTTPException(status_code=404, detail="Species not found")

    # Enrich with Wikimedia Data (Async)
    data["info"] = await BirdNetService.enrich_species_data(data["info"])

    return render(request, "birdnet_species.html", {
        "request": request,
        "page": "birdnet_discover",
        "species": data["info"],
        "recent": data["recent"],
        "hourly": data["hourly"],
        "status_label": "BirdNET:",
        "status_value": species_name,
        "status_color": "text-amber-500 dark:text-amber-400"
    })

@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    stats_data = await BirdNetService.get_advanced_stats()

    return render(request, "stats.html", {
        "request": request,
        "page": "stats",
        "daily": stats_data["daily"],
        "hourly": stats_data["hourly"],
        "distributions": stats_data["distributions"],
        "histogram": stats_data["histogram"],
        "rarest": stats_data["rarest"],
        "status_label": "Statistics:",
        "status_value": "Detailed",
        "status_color": "text-blue-500 dark:text-blue-400"
    })

@app.get("/recorder", response_class=HTMLResponse)
async def recorder_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    stats = RecorderService.get_status()
    # Also get system stats for context if needed
    sys_stats = SystemService.get_stats()
    recordings = await RecorderService.get_recent_recordings()

    return render(request, "recorder.html", {
        "request": request,
        "page": "recorder",
        "stats": stats,
        "sys_stats": sys_stats,
        "recordings": recordings,
        "status_label": "Recorder:",
        "status_value": stats.get("status", "Unknown"),
        "status_color": "text-green-600 dark:text-green-400" if stats.get("status") == "Running" else "text-red-600 dark:text-red-400",
        "auto_refresh_interval": 15
    })

@app.get("/uploader", response_class=HTMLResponse)
async def uploader_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    stats = CarrierService.get_status()
    upload_stats = await CarrierService.get_upload_stats()
    recent_uploads = await CarrierService.get_recent_uploads(limit=100)
    failed_uploads = await CarrierService.get_failed_uploads(limit=50)

    return render(request, "uploader.html", {
        "request": request,
        "page": "uploader",
        "stats": stats,
        "upload_stats": upload_stats,
        "recent_uploads": recent_uploads,
        "failed_uploads": failed_uploads,
        "status_label": "Uploader:",
        "status_value": stats.get("status", "Idle"),
        "status_color": "text-cyan-600 dark:text-cyan-400",
        "auto_refresh_interval": 15
    })

@app.get("/livesound", response_class=HTMLResponse)
async def livesound_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    # No stats needed for pure live stream page initially
    # If we want livesound container stats, we could fetch them, but for now just render UI
    
    return render(request, "livesound.html", {
        "request": request,
        "page": "livesound",
        "status_label": "Livesound:",
        "status_value": "Streaming",
        "status_color": "text-purple-600 dark:text-purple-400",
        # Auto refresh not needed for live canvas/audio
        # "auto_refresh_interval": 15
    })

@app.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    current = await WeatherService.get_current_weather()
    history = await WeatherService.get_history(hours=24)
    status_data = WeatherService.get_status()
    correlations = await WeatherService.get_correlations(days=30)

    return render(request, "weather.html", {
        "request": request,
        "page": "weather",
        "current": current,
        "history": history,
        "correlations": correlations,
        "status_label": "Weather:",
        "status_value": status_data.get("status", "Unknown"),
        "status_color": "text-blue-500 dark:text-blue-400" if status_data.get("status") == "Running" else "text-red-500",
        "auto_refresh_interval": 15
    })

# --- Inspector API Partials ---
from pydantic import BaseModel


class WatchlistToggleRequest(BaseModel):
    scientific_name: str
    common_name: str
    enabled: bool

@app.post("/api/watchlist/toggle")
async def api_toggle_watchlist(req: WatchlistToggleRequest, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): raise HTTPException(401)

    success = await BirdNetService.toggle_watchlist(req.scientific_name, req.common_name, req.enabled)
    if success:
        return {"status": "ok", "enabled": req.enabled}
    else:
        raise HTTPException(500, "Failed to toggle watchlist")

@app.get("/api/details/birdnet/{filename:path}", response_class=HTMLResponse)
async def get_birdnet_details(request: Request, filename: str, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth

    data = await BirdNetService.get_detection(filename)
    if not data:
        return "<div class='p-4 text-red-500'>Detection not found</div>"

    # Enrich if missing (async) - optional, or rely on what get_detection fetched (via join)
    # The join in get_detection might miss if not cached.
    # Let's trigger quick enrichment if basic info is missing but we have sci_name
    if not data.get('image_url') and data.get('sci_name'):
         # We trigger a background fetch or just Await it (better for user exp here)
         await BirdNetService.enrich_species_data(data)
         # Refresh data
         data = await BirdNetService.get_detection(filename) or data

    return render(request, "partials/inspector_birdnet.html", {"request": request, "d": data})

# --- API / HTMX Partials ---

@app.get("/api/logs/{service}")
async def stream_logs(service: str, auth=Depends(require_auth)):
    """SSE Stream for logs"""
    if isinstance(auth, RedirectResponse): raise HTTPException(401)

    log_file = os.path.join(LOG_DIR, f"{service}.log")
    # Do NOT try to create file (RO Volume violation)

    async def log_generator():
        import asyncio
        import aiofiles

        # Wait for file to exist
        while not os.path.exists(log_file):
            yield f"data: Waiting for {service} logs...\n\n"
            await asyncio.sleep(2)

        try:
            async with aiofiles.open(log_file) as f:
                # --- Initial Tail (Last 8KB) ---
                file_size = os.path.getsize(log_file)
                tail_size = 8192 # 8KB
                
                if file_size > 0:
                    seek_pos = max(0, file_size - tail_size)
                    await f.seek(seek_pos)
                    
                    # If we seeked to middle, skip partial line
                    if seek_pos > 0:
                        await f.readline() 
                    
                    # Read remaining existing content
                    while True:
                        line = await f.readline()
                        if not line: break
                        yield f"data: {line}\n\n"
                        
                # --- Continuous Tail ---
                # Ensure we are at the end (though reading to end above should have done it)
                await f.seek(0, 2)
                
                while True:
                    line = await f.readline()
                    if line:
                        yield f"data: {line}\n\n"
                    else:
                        await asyncio.sleep(0.5)
        except Exception as e:
            yield f"data: Error reading logs: {e}\n\n"

    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/api/audio/{filename:path}")
async def stream_audio(filename: str, auth=Depends(require_auth)):
    """Stream audio file from recording dir"""
    if isinstance(auth, RedirectResponse): raise HTTPException(401)

    # Security: Prevent traversing out of audio dir
    # filename here is actually a path potentially (e.g. "2023-10-27/bird.flac")

    # Sanitize:
    clean_path = os.path.normpath(filename).lstrip('/')

    # Construct full path
    full_path = os.path.join(AUDIO_DIR, clean_path)
    safe_path = os.path.abspath(full_path)

    # Verify it is still inside AUDIO_DIR
    if not safe_path.startswith(os.path.abspath(AUDIO_DIR)):
        raise HTTPException(403, "Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(404, "File not found")

    return FileResponse(safe_path, media_type="audio/flac")

@app.get("/api/spectrogram/{filename:path}")
async def stream_spectrogram(filename: str, auth=Depends(require_auth)):
    """Stream spectrogram from artifacts dir, generating it if needed (Lazy Loading)"""
    if isinstance(auth, RedirectResponse): raise HTTPException(401)

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
