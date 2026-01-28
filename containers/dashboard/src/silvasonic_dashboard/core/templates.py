from typing import Any

from fastapi import Request, Response
from fastapi.templating import Jinja2Templates

from .constants import TEMPLATES_DIR, VERSION

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def render(request: Request, template: str, context: dict[str, Any]) -> Response:
    """Render a template with global context injected."""
    # HTMX Support: Check header. If HX-Request, use a different "base" that is empty?
    if request.headers.get("HX-Request"):
        context["base"] = "partials/empty_base.html"
    else:
        context["base"] = "base.html"

    # Inject Global Context
    context["version"] = VERSION

    return templates.TemplateResponse(template, context)
