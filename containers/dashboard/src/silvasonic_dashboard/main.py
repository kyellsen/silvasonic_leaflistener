import os
import threading
import typing
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from silvasonic_dashboard.core.constants import BASE_DIR
from silvasonic_dashboard.core.health import write_status
from silvasonic_dashboard.core.logging import setup_logging
from silvasonic_dashboard.core.middleware import add_security_headers
from silvasonic_dashboard.routers import api, auth, views

# Setup Logging
setup_logging()
logger = structlog.get_logger("Dashboard")


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

    logger.info("Dashboard Service Started", version="0.1.0")
    yield
    # Shutdown logic can go here if needed
    logger.info("Dashboard Service Stopping")


app = FastAPI(title="Silvasonic Dashboard", lifespan=lifespan)

# Middleware
app.middleware("http")(add_security_headers)

# Mount Static
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(views.router)
