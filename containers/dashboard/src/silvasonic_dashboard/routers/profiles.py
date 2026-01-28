import os
import shutil
import typing
from pathlib import Path

import yaml
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])

PROFILES_DIR = Path("/app/mic_profiles")


@router.get("/")
async def list_profiles() -> list[dict[str, typing.Any]]:
    """List all available microphone profiles."""
    profiles = []
    if not PROFILES_DIR.exists():
        return []

    for f in PROFILES_DIR.glob("*.yml"):
        try:
            with open(f) as yml:
                data = yaml.safe_load(yml)
                # Add filename for reference
                data["filename"] = f.name
                profiles.append(data)
        except Exception:
            continue

    return profiles


@router.post("/")
async def upload_profile(file: UploadFile = File(...)) -> dict[str, str]:
    """Upload a new microphone profile (.yml)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    if not file.filename.endswith(".yml") and not file.filename.endswith(".yaml"):
        raise HTTPException(status_code=400, detail="Only .yml files allowed")

    target_path = PROFILES_DIR / file.filename

    try:
        # Save file
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Verify it's valid YAML
        with open(target_path) as verify:
            yaml.safe_load(verify)

        return {"status": "uploaded", "filename": file.filename}

    except yaml.YAMLError as e:
        # Delete invalid file
        if target_path.exists():
            os.remove(target_path)
        raise HTTPException(status_code=400, detail="Invalid YAML content") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{filename}")
async def delete_profile(filename: str) -> dict[str, str]:
    """Delete a profile by filename."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    target_path = PROFILES_DIR / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        os.remove(target_path)
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/template")
async def get_template() -> JSONResponse:
    """Get a template profile structure."""
    template = {
        "name": "Example Microphone",
        "manufacturer": "Brand",
        "model": "Model X",
        "device_patterns": ["USB Microphone Name", "Another Pattern"],
        "audio": {"sample_rate": 48000, "channels": 1, "bit_depth": 16, "format": "S16_LE"},
        "recording": {
            "chunk_duration_seconds": 60,
            "output_format": "flac",
            "compression_level": 5,
        },
    }
    return JSONResponse(template)
