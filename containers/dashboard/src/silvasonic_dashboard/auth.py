# Environment-Aware Auth Logic
import logging
import os
import secrets
import sys

from fastapi import HTTPException, Request, Response, status
from starlette.responses import RedirectResponse

logger = logging.getLogger("Dashboard.Auth")

SILVASONIC_ENV = os.getenv("SILVASONIC_ENV", "development").lower()
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "Admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

SECRET_FILE_PATH = "/config/secrets/auth_token.txt"


def get_admin_password() -> str:
    """Resolve Admin Password based on Environment Logic."""
    if SILVASONIC_ENV == "development":
        if not DASHBOARD_PASSWORD:
            logger.warning(
                "DEV MODE: Using default password '1234'. Set DASHBOARD_PASSWORD to override."
            )
            return "1234"
        return DASHBOARD_PASSWORD

    # PRODUCTION MODE
    if DASHBOARD_PASSWORD:
        if DASHBOARD_PASSWORD == "1234":
            logger.critical(
                "PRODUCTION SECURITY ERROR: Password '1234' is not allowed in production!"
            )
            sys.exit(1)  # Hard Fail
        return DASHBOARD_PASSWORD

    # No password var set -> Check Persistence
    if os.path.exists(SECRET_FILE_PATH):
        try:
            with open(SECRET_FILE_PATH) as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read secret file: {e}")
            sys.exit(1)

    # Generate New Secret
    token = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(SECRET_FILE_PATH), exist_ok=True)
        with open(SECRET_FILE_PATH, "w") as f:
            f.write(token)
        logger.critical(f"FIRST RUN SECURITY: Generated Admin Password: {token}")
        logger.critical("SAVE THIS PASSWORD! It is stored in /config/secrets/auth_token.txt")
        return token
    except Exception as e:
        logger.critical(f"FATAL: Could not write secret to {SECRET_FILE_PATH}: {e}")
        sys.exit(1)


ADMIN_USER = DASHBOARD_USER
ADMIN_PASS = get_admin_password()
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
COOKIE_NAME = "silvasonic_session"


def check_auth(request: Request) -> bool | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or token != SESSION_SECRET:
        return None
    return True


def require_auth(request: Request) -> bool | RedirectResponse | Response:
    if not check_auth(request):
        # If API request, return 401
        if request.url.path.startswith("/api"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        # Check for HTMX Request
        if request.headers.get("HX-Request"):
            from fastapi.responses import Response

            # Force client-side redirect
            return Response(headers={"HX-Redirect": "/auth/login"})

        # If Page request, redirect to login
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return True


def verify_credentials(username: str, password: str) -> bool:
    # Constant time comparison to prevent timing attacks
    user_ok = secrets.compare_digest(username, ADMIN_USER)
    pass_ok = secrets.compare_digest(password, ADMIN_PASS)
    return user_ok and pass_ok
