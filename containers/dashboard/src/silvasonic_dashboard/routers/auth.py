import asyncio
from typing import cast

import structlog
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.status import HTTP_302_FOUND, HTTP_403_FORBIDDEN

from silvasonic_dashboard import auth as auth_logic
from silvasonic_dashboard.auth import (
    COOKIE_NAME,
    SESSION_SECRET,
    verify_credentials,
)
from silvasonic_dashboard.core.templates import render

logger = structlog.get_logger()
router = APIRouter()


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    return cast(
        Response,
        render(
            request,
            "login.html",
            {"request": request, "is_dev_mode": auth_logic.SILVASONIC_ENV == "development"},
        ),
    )


@router.post("/auth/dev-login")
async def dev_login(request: Request) -> Response:
    if auth_logic.SILVASONIC_ENV != "development":
        return Response(content="Forbidden", status_code=HTTP_403_FORBIDDEN)

    logger.warning("DEV MODE: Bypassing authentication via Dev Login button")
    response = RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
    response.set_cookie(
        key=COOKIE_NAME,
        value=SESSION_SECRET,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@router.post("/auth/login")
async def login_submit(
    request: Request, username: str = Form(...), password: str = Form(...)
) -> Response:
    if verify_credentials(username, password):
        logger.info("User logged in", username=username)
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
    logger.warning("Failed login attempt", username=username)
    await asyncio.sleep(1.0)
    return cast(
        Response,
        render(request, "login.html", {"request": request, "error": "Invalid credentials"}),
    )


@router.get("/auth/logout")
async def logout() -> Response:
    response = RedirectResponse(url="/auth/login", status_code=HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response
