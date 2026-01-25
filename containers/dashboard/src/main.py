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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    return templates.TemplateResponse("index.html", {"request": request, "page": "home"})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    return templates.TemplateResponse("logs.html", {"request": request, "page": "logs"})

@app.get("/birdnet", response_class=HTMLResponse)
async def birdnet_page(request: Request, auth=Depends(require_auth)):
    if isinstance(auth, RedirectResponse): return auth
    return templates.TemplateResponse("birdnet.html", {"request": request, "page": "birdnet"})

# --- API / HTMX Partials ---

@app.get("/api/logs/{service}")
async def stream_logs(service: str, auth=Depends(require_auth)):
    """SSE Stream for logs"""
    if isinstance(auth, RedirectResponse): raise HTTPException(401)
    
    log_file = os.path.join(LOG_DIR, f"{service}.log")
    if not os.path.exists(log_file):
        # Create empty if not exists to avoid error
        with open(log_file, 'a'): pass
        
    async def log_generator():
        import asyncio
        import aiofiles
        async with aiofiles.open(log_file, mode='r') as f:
            # Seek to end
            await f.seek(0, 2)
            while True:
                line = await f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    await asyncio.sleep(0.5)
                    
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
