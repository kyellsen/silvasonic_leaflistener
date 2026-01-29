import os
import threading
import typing
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from silvasonic_dashboard.core.constants import BASE_DIR
from silvasonic_dashboard.core.health import write_status
from silvasonic_dashboard.core.logging import setup_logging
from silvasonic_dashboard.core.middleware import add_security_headers
from silvasonic_dashboard.models import SystemConfig, SystemService
from silvasonic_dashboard.routers import api, auth, control, profiles, views
from silvasonic_dashboard.services.database import db

# Setup Logging
setup_logging()
logger = structlog.get_logger("Dashboard")


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    # Startup: Start status writer in thread
    t = threading.Thread(target=write_status, daemon=True)
    t.start()

    # Seed Defaults
    try:
        async with db.async_session_maker() as session:
            # 1. System Config
            result = await session.execute(select(SystemConfig))
            if not result.scalars().first():
                logger.info("Seeding System Config defaults...")
                session.add_all(
                    [
                        SystemConfig(
                            key="upload_strategy",
                            value="wifi_only",
                            description="Upload only when WiFi is connected",
                        ),
                        SystemConfig(
                            key="retention_days",
                            value="30",
                            description="Days to keep local recordings",
                        ),
                    ]
                )
                await session.commit()

            # 2. System Services (If empty - though likely seeded by SQL)
            result = await session.execute(select(SystemService))
            if not result.scalars().first():
                logger.info("Seeding System Services defaults...")
                session.add_all(
                    [
                        SystemService(
                            service_name="birdnet",
                            image="silvasonic-birdnet:latest",
                            enabled=False,
                            category="addon",
                        ),
                        SystemService(
                            service_name="weather",
                            image="silvasonic-weather:latest",
                            enabled=True,
                            category="addon",
                        ),
                        SystemService(
                            service_name="uploader",
                            image="silvasonic-uploader:latest",
                            enabled=True,
                            category="core",
                        ),
                    ]
                )
                await session.commit()

    except Exception as e:
        logger.error(f"Seeding failed: {e}")

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
app.include_router(control.router)
app.include_router(profiles.router)
app.include_router(views.router)
