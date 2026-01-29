import datetime
import typing

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from starlette.status import HTTP_302_FOUND

from silvasonic_dashboard.auth import check_auth, require_auth
from silvasonic_dashboard.core.templates import render
from silvasonic_dashboard.services import (
    BirdNetService,
    BirdNetStatsService,
    HealthCheckerService,
    RecorderService,
    SystemService,
    UploaderService,
    WeatherService,
)
from silvasonic_dashboard.settings import SettingsService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> typing.Any:
    # Redirect to dashboard if authed, else login
    if check_auth(request):
        return RedirectResponse("/dashboard", status_code=HTTP_302_FOUND)
    return RedirectResponse("/auth/login", status_code=HTTP_302_FOUND)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = await SystemService.get_stats()
    detections = await BirdNetService.get_recent_detections(limit=5)
    birdnet_stats = await BirdNetStatsService.get_stats()
    uploader_stats = UploaderService.get_status()
    recorder_stats = await RecorderService.get_status()
    raw_containers = HealthCheckerService.get_system_metrics()

    # 1. Get Cursors
    latest_processed = await BirdNetService.get_latest_processed_filename()
    latest_uploaded = await UploaderService.get_latest_uploaded_filename()

    # 2. Calculate Lag (Files waiting)
    analyzer_lag = await RecorderService.count_files_after(latest_processed)
    uploader_lag = await RecorderService.count_files_after(latest_uploaded)

    # Status Logic (Thresholds)
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
        is_active = r.get("status") == "Running"
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
        "recorder_active": (await RecorderService.get_creation_rate(10)) > 0,
        "recorders": recorders_throughput,
        "analyzer_lag": analyzer_lag,
        "uploader_lag": uploader_lag,
        "analyzer_status": get_status(analyzer_lag),
        "uploader_status": get_status(uploader_lag),
    }

    # Define Sort Order & Display Names
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

    def find_container(
        key_fragment: str, source_dict: dict[str, typing.Any]
    ) -> dict[str, typing.Any] | None:
        for k, v in source_dict.items():
            if key_fragment in k:
                return typing.cast(dict[str, typing.Any], v)
        return None

    for config in container_config:
        if config["key"] == "recorder":
            recorders_found = [
                (k, v) for k, v in raw_containers.items() if k.startswith("recorder")
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
            c = find_container(config["key"], raw_containers)

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
            "containers": containers,
            "throughput": throughput,
            "status_label": "System:",
            "status_value": "Online",
            "status_color": "text-green-600 dark:text-green-400",
            "auto_refresh_interval": 5,
        },
    )


@router.get("/recorder", response_class=HTMLResponse)
async def recorder_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = await RecorderService.get_status()
    # Dummy system stats if SystemService doesn't provide them yet, but template calls sys_stats
    sys_stats = await SystemService.get_stats()
    recordings = await RecorderService.get_recent_recordings()

    return render(
        request,
        "recorder.html",
        {
            "request": request,
            "page": "recorder",
            "stats": stats,  # List of recorder status
            "sys_stats": sys_stats,
            "recordings": recordings,
            "status_label": "Recorders:",
            "status_value": "Active" if stats else "No Recorders",
            "status_color": "text-pink-600 dark:text-pink-400",
            "auto_refresh_interval": 30,  # Slower refresh for recorders
        },
    )


@router.get("/uploader", response_class=HTMLResponse)
async def uploader_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    stats = UploaderService.get_status()
    recent_uploads = await UploaderService.get_recent_uploads()
    failed_uploads = await UploaderService.get_failed_uploads()
    upload_stats = await UploaderService.get_upload_stats()

    return render(
        request,
        "uploader.html",
        {
            "request": request,
            "page": "uploader",
            "stats": stats,
            "recent_uploads": recent_uploads,
            "failed_uploads": failed_uploads,
            "upload_stats": upload_stats,
            "status_label": "Uploader:",
            "status_value": stats.get("status", "Unknown"),
            "status_color": "text-cyan-600 dark:text-cyan-400",
            "auto_refresh_interval": 5,
        },
    )


@router.get("/livesound", response_class=HTMLResponse)
async def livesound_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    recorder_stats = await RecorderService.get_status()

    return render(
        request,
        "livesound.html",
        {
            "request": request,
            "page": "livesound",
            "recorder_stats": recorder_stats,
            "status_label": "Livesound:",
            "status_value": "Ready",
            "status_color": "text-purple-600 dark:text-purple-400",
        },
    )


@router.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    auth: typing.Any = Depends(require_auth),
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    # Default period: Last 7 days
    # Need to handle date parsing if params provided
    # BirdNetStatsService likely accepts start/end strings or dates.

    stats_data = await BirdNetStatsService.get_advanced_stats(
        start_date=datetime.date.fromisoformat(start) if start else None,
        end_date=datetime.date.fromisoformat(end) if end else None,
    )

    return render(
        request,
        "stats.html",
        {
            "request": request,
            "page": "stats",
            # stats.html expects `stats` object with daily, hourly, top_species, rarest
            "stats": stats_data,
            "status_label": "Analytics:",
            "status_value": "Viewing",
            "status_color": "text-indigo-600 dark:text-indigo-400",
        },
    )


@router.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    current = await WeatherService.get_current_weather()
    history = await WeatherService.get_history(hours=24)
    correlations = await WeatherService.get_correlations(days=30)
    status_info = WeatherService.get_status()

    return render(
        request,
        "weather.html",
        {
            "request": request,
            "page": "weather",
            "current": current,
            "history": history,
            "correlations": correlations,
            "status_value": status_info.get("status", "Unknown"),
            "status_color": "text-sky-600 dark:text-sky-400",  # Fixed color for now
            "auto_refresh_interval": 60,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
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


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    form = await request.form()

    # Process Form
    use_german = form.get("use_german_names") == "on"
    notifier_email = str(form.get("notifier_email", "")).strip()
    apprise_urls_raw = str(form.get("apprise_urls", "")).strip()

    try:
        latitude = float(str(form.get("latitude", 52.52)))
        longitude = float(str(form.get("longitude", 13.40)))
    except (ValueError, TypeError):
        latitude = 52.52
        longitude = 13.40

    apprise_urls = [u.strip() for u in apprise_urls_raw.split(",") if u.strip()]

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
    settings["location"]["longitude"] = longitude

    try:
        settings.setdefault("birdnet", {})
        settings["birdnet"]["min_confidence"] = float(str(form.get("birdnet_min_confidence", 0.7)))
        settings["birdnet"]["sensitivity"] = float(str(form.get("birdnet_sensitivity", 1.0)))
        settings["birdnet"]["overlap"] = float(str(form.get("birdnet_overlap", 0.0)))
    except (ValueError, TypeError):
        pass

    settings.setdefault("healthchecker", {}).setdefault("service_timeouts", {})
    services = ["recorder", "birdnet", "sound_analyser", "weather", "uploader"]
    for svc in services:
        key = f"timeout_{svc}"
        val = form.get(key)
        if val:
            try:
                settings["healthchecker"]["service_timeouts"][svc] = int(str(val))
            except ValueError:
                pass

    msg = None
    err = None
    field_errors = {}

    try:
        SettingsService.save_settings(settings)
        msg = "Settings saved successfully."
    except ValidationError as e:
        err = "Validation Error. Please check your inputs."
        for error in e.errors():
            loc = error["loc"]
            if loc:
                field_name = str(loc[-1])
                if field_name == "recipient_email":
                    field_name = "notifier_email"
                field_errors[field_name] = error["msg"]

    except Exception as e:
        err = f"Failed to save settings: {e}"
        logger.error("Failed to save settings", error=str(e))

    return render(
        request,
        "settings.html",
        {
            "request": request,
            "page": "settings",
            "settings": settings,
            "success": msg,
            "error": err,
            "field_errors": field_errors,
            "status_label": "System:",
            "status_value": "Settings",
            "status_color": "text-gray-500",
        },
    )


@router.get("/logs", response_class=HTMLResponse)
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


@router.get("/birdnet", response_class=HTMLResponse)
async def birdnet_page(request: Request, auth: typing.Any = Depends(require_auth)) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    detections = await BirdNetService.get_recent_detections(limit=50)
    stats = await BirdNetStatsService.get_stats()
    recent_files = await BirdNetService.get_recent_processed_files(limit=50)
    proc_stats = await BirdNetService.get_processing_stats()

    return render(
        request,
        "birdnet.html",
        {
            "request": request,
            "page": "birdnet",
            "detections": detections,
            "recent_files": recent_files,
            "stats": stats,
            "proc_stats": proc_stats,
            "status_label": "BirdNET:",
            "status_value": stats.get("status", "Active"),
            "status_color": "text-green-600 dark:text-green-400",
            "auto_refresh_interval": 5,
        },
    )


@router.get("/birdnet/discover", response_class=HTMLResponse)
async def birdnet_discover_page(
    request: Request, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    species_list = await BirdNetService.get_all_species()
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


@router.get("/birdnet/discover/{species_name}", response_class=HTMLResponse)
async def birdnet_species_page(
    request: Request, species_name: str, auth: typing.Any = Depends(require_auth)
) -> typing.Any:
    if isinstance(auth, RedirectResponse):
        return auth

    data = await BirdNetStatsService.get_species_stats(species_name)
    if not data:
        raise HTTPException(status_code=404, detail="Species not found")

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
            "auto_refresh_interval": 0,
        },
    )


@router.get("/about", response_class=HTMLResponse)
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
