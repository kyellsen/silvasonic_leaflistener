from collections.abc import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, SecretStr
from silvasonic_uploader.config import UploaderSettings
from silvasonic_uploader.rclone_wrapper import RcloneWrapper

router = APIRouter()

# Global reference to the reload function (injected by main.py)
_reloader: Callable[[], Awaitable[None]] | None = None


def set_reloader(func: Callable[[], Awaitable[None]]) -> None:
    global _reloader
    _reloader = func


class ConnectionTestRequest(BaseModel):
    url: str
    user: str
    password: str


class ConfigUpdate(BaseModel):
    """Partial update model."""

    nextcloud_url: str | None = None
    nextcloud_user: str | None = None
    nextcloud_password: str | None = None
    sync_interval: int | None = None
    cleanup_threshold: int | None = None
    cleanup_target: int | None = None
    min_age: str | None = None
    bwlimit: str | None = None


@router.get("/config", response_model=UploaderSettings)
async def get_config() -> UploaderSettings:
    """Get current configuration."""
    return UploaderSettings.load()


@router.patch("/config")
async def update_config(
    update: ConfigUpdate, background_tasks: BackgroundTasks
) -> UploaderSettings:
    """Update configuration and trigger reload."""
    try:
        current = UploaderSettings.load()

        # Apply updates
        data = update.model_dump(exclude_unset=True)
        if "nextcloud_password" in data and data["nextcloud_password"]:
            data["nextcloud_password"] = SecretStr(data["nextcloud_password"])

        updated_settings = current.model_copy(update=data)
        updated_settings.save()

        # Trigger reload if configured
        if _reloader:
            background_tasks.add_task(_reloader)

        return updated_settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/test-connection")
async def test_connection(creds: ConnectionTestRequest) -> dict[str, str]:
    """Test Nextcloud connection with provided credentials."""
    wrapper = RcloneWrapper()
    remote_name = "test_remote"

    try:
        # Configure temporary remote
        await wrapper.configure_webdav(
            remote_name=remote_name,
            url=creds.url,
            user=creds.user,
            password=creds.password,
        )

        # Try to list files (top level)
        result = await wrapper.list_files(f"{remote_name}:")
        if result is None:
            raise Exception("Failed to list files")

        return {"status": "success", "message": "Connection successful"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}") from e
