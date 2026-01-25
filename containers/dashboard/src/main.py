import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

from src.auth import require_auth, verify_credentials, SESSION_SECRET, COOKIE_NAME

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Dashboard")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
AUDIO_DIR = "/data/recording"
LOG_DIR = "/var/log/silvasonic"

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
        
    return templates.TemplateResponse(template, context)

# We need a partial base that outputs only the blocks


# Mount Static (if we had specific assets, for now CDN is used)
# app.mount("/static", StaticFiles(directory="static"), name="static")

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
    if verify_credentials(username, password):
        response = RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
        response.set_cookie(key=COOKIE_NAME, value=SESSION_SECRET, httponly=True)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response

# --- Protected Routes ---

from src.services import SystemService, BirdNetService, CarrierService, RecorderService

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    
    stats = SystemService.get_stats()
    detections = BirdNetService.get_recent_detections(limit=5)
    birdnet_stats = BirdNetService.get_stats()
    carrier_stats = CarrierService.get_status()
    recorder_stats = RecorderService.get_status()
    
    return render(request, "index.html", {
        "request": request, 
        "page": "home",
        "stats": stats,
        "detections": detections,
        "birdnet_stats": birdnet_stats,
        "carrier_stats": carrier_stats,
        "recorder_stats": recorder_stats,
        "status_label": "System:",
        "status_value": "Online",
        "status_color": "text-green-600 dark:text-green-400"
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
    
    detections = BirdNetService.get_recent_detections(limit=50) # More for browser
    stats = BirdNetService.get_stats()
    
    return render(request, "birdnet.html", {
        "request": request, 
        "page": "birdnet",
        "detections": detections,
        "stats": stats,
        "status_label": "BirdNET:",
        "status_value": stats.get("status", "Active"),
        "status_color": "text-green-600 dark:text-green-400"
    })

@app.get("/birdnet/discover", response_class=HTMLResponse)
async def birdnet_discover_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    
    species_list = BirdNetService.get_all_species()
    
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
    
    data = BirdNetService.get_species_stats(species_name)
    if not data:
        raise HTTPException(status_code=404, detail="Species not found")
        
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
    
    stats_data = BirdNetService.get_time_stats()
    
    return render(request, "stats.html", {
        "request": request,
        "page": "stats",
        "daily": stats_data["daily"],
        "hourly": stats_data["hourly"],
        "top": stats_data["top"],
        "status_label": "Statistics:",
        "status_value": "Overview",
        "status_color": "text-blue-500 dark:text-blue-400"
    })

@app.get("/recorder", response_class=HTMLResponse)
async def recorder_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    
    stats = RecorderService.get_status()
    # Also get system stats for context if needed
    sys_stats = SystemService.get_stats()
    
    return render(request, "recorder.html", {
        "request": request, 
        "page": "recorder",
        "stats": stats,
        "sys_stats": sys_stats,
        "status_label": "Recorder:",
        "status_value": stats.get("status", "Unknown"),
        "status_color": "text-green-600 dark:text-green-400" if stats.get("status") == "Running" else "text-red-600 dark:text-red-400"
    })

@app.get("/uploader", response_class=HTMLResponse)
async def uploader_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    
    stats = CarrierService.get_status()
    
    return render(request, "uploader.html", {
        "request": request, 
        "page": "uploader",
        "stats": stats,
        "status_label": "Uploader:",
        "status_value": stats.get("status", "Idle"),
        "status_color": "text-cyan-600 dark:text-cyan-400"
    })

@app.get("/analyzer", response_class=HTMLResponse)
async def analyzer_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    
    # Brain/Analyzer specific stats could go here. 
    # For now, we reuse system stats as Brain is the main CPU user.
    stats = SystemService.get_stats()
    
    return render(request, "analyzer.html", {
        "request": request, 
        "page": "analyzer",
        "page": "analyzer",
        "stats": stats,
        "status_label": "Analyzer:",
        "status_value": "Monitoring",
        "status_color": "text-purple-600 dark:text-purple-400"
    })

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
            async with aiofiles.open(log_file, mode='r') as f:
                # Seek to end
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

@app.get("/api/audio/{filename}")
async def stream_audio(filename: str, auth=Depends(require_auth)):
    """Stream audio file from recording dir"""
    if isinstance(auth, RedirectResponse): raise HTTPException(401)
    
    # Security: Prevent traversing out of audio dir
    safe_path = os.path.normpath(os.path.join(AUDIO_DIR, filename))
    if not safe_path.startswith(AUDIO_DIR) or not os.path.exists(safe_path):
        raise HTTPException(404, "File not found")
        
    return FileResponse(safe_path, media_type="audio/flac")
