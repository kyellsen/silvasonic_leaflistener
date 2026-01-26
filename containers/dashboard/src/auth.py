import os
import secrets

from fastapi import HTTPException, Request, status
from starlette.responses import RedirectResponse

# Simple Env-based Auth
ADMIN_USER = os.getenv("DASHBOARD_USER", "Admin")
ADMIN_PASS = os.getenv("DASHBOARD_PASS", "1234")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
COOKIE_NAME = "silvasonic_session"

def check_auth(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token or token != SESSION_SECRET:
        return None
    return True

def require_auth(request: Request):
    if not check_auth(request):
        # If API request, return 401
        if request.url.path.startswith("/api"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # If Page request, redirect to login
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return True

def verify_credentials(username, password):
    # Constant time comparison to prevent timing attacks
    user_ok = secrets.compare_digest(username, ADMIN_USER)
    pass_ok = secrets.compare_digest(password, ADMIN_PASS)
    return user_ok and pass_ok
