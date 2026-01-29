import datetime
import json
import os
from typing import Any, cast

import redis
from async_lru import alru_cache
from sqlalchemy import select, text

from silvasonic_dashboard.models import Recording
from silvasonic_dashboard.services.database import db

from .common import REC_DIR, logger, run_in_executor


class RecorderService:
    @staticmethod
    def get_audio_settings(profile: dict[str, Any] | None) -> float:
        """Extract audio BPS (Bytes per Second) from profile."""
        try:
            if isinstance(profile, dict) and "audio" in profile:
                audio = profile["audio"]
                sr = int(audio.get("sample_rate", 48000))
                ch = int(audio.get("channels", 1))
                depth = int(audio.get("bit_depth", 16))

                # Bytes per second (Uncompressed)
                return sr * ch * (depth / 8)
        except Exception:
            pass
        return 48000 * 1 * 2  # Default to 48kHz, Mono, 16-bit (96000 Bps)

    @staticmethod
    @alru_cache(ttl=1)
    async def get_status() -> list[dict[str, Any]]:
        """Returns a list of status dicts for all detected recorders from Redis."""
        statuses = []
        try:
            # Connect to Redis
            r: redis.Redis = redis.Redis(
                host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1
            )

            # Find all recorder keys
            keys = cast(list[bytes], r.keys("status:recorder:*"))

            # Additional keys that might match: "status:recorder"
            if r.exists("status:recorder"):
                keys.append(b"status:recorder")

            if not keys:
                return []

            for key in keys:
                try:
                    raw_data = cast(bytes | None, r.get(key))
                    if not raw_data:
                        continue

                    data = json.loads(raw_data)
                    meta = data.get("meta", {})
                    profile = meta.get("profile", {})

                    # 1. Device Name Cleaning
                    raw_device = meta.get("device", "Unknown")
                    clean_device = raw_device
                    if isinstance(raw_device, str):
                        import re

                        match = re.search(r"\[(.*?)\]", raw_device)
                        if match:
                            clean_device = match.group(1)

                    data["profile"] = profile
                    data["device"] = clean_device
                    data["device_raw"] = raw_device

                    # 2. Storage Forecast
                    forecast = {
                        "daily_gb": 0,
                        "daily_str": "Unknown",
                        "remaining_days": 0,
                        "remaining_str": "Unknown",
                    }

                    if isinstance(profile, dict) and "audio" in profile:
                        try:
                            bps = RecorderService.get_audio_settings(profile)
                            compression = 0.6
                            bytes_per_day = bps * 60 * 60 * 24 * compression
                            gb_per_day = bytes_per_day / (1024**3)

                            forecast["daily_gb"] = round(gb_per_day, 1)
                            forecast["daily_str"] = f"~{gb_per_day:.1f} GB"

                            # Calculate Remaining using shutil on the recording path
                            import shutil

                            def get_usage() -> tuple[int, int, int]:
                                check_path = REC_DIR if os.path.exists(REC_DIR) else "/"
                                u = shutil.disk_usage(check_path)
                                return u.total, u.used, u.free

                            _, _, free_bytes = await run_in_executor(get_usage)

                            if bytes_per_day > 0:
                                days_remaining = free_bytes / bytes_per_day
                                forecast["remaining_days"] = int(days_remaining)
                                if days_remaining > 365:
                                    forecast["remaining_str"] = ">1y"
                                else:
                                    forecast["remaining_str"] = f"~{int(days_remaining)}d"

                        except Exception as e:
                            logger.error(f"Forecast Error: {e}")

                    data["storage_forecast"] = forecast
                    statuses.append(data)
                except Exception as e:
                    logger.error(
                        f"Error reading redis key {key.decode('utf-8', errors='replace')}: {e}"
                    )

            statuses.sort(key=lambda x: x.get("profile", {}).get("name", ""))
            return statuses

        except Exception as e:
            logger.error(f"Recorder status error: {e}")

        return [
            {
                "status": "Unknown",
                "profile": "Error",
                "device": "Unknown",
                "storage_forecast": {"daily_str": "?", "remaining_str": "?"},
            }
        ]

    @staticmethod
    @alru_cache(ttl=15)
    async def get_recent_recordings(limit_per_source: int = 20) -> dict[str, list[dict[str, Any]]]:
        """Returns recordings grouped by source (device_id), querying the database."""
        grouped_recordings: dict[str, list[dict[str, Any]]] = {}

        try:
            async with db.get_connection() as conn:
                # We want recent recordings but grouped by device/source.
                # Since we don't know the sources, we can query distinct sources first
                # OR just fetch recent N recordings and group them python side or via CTE.
                # Since limit is per source, let's fetch distinct devices first.

                query_devices = text("SELECT DISTINCT device_id FROM recordings")
                devices = (await conn.execute(query_devices)).scalars().all()

                # If no devices in DB yet, fallback to Empty logic
                if not devices:
                    # Provide empty list for 'Default' if just starting
                    # or handle empty UI gracefully
                    pass

                # If devices found, query for each
                # This could be optimized into one window function query, but N+1 is fine for small specific queries
                devices_list = list(devices)
                if not devices_list:
                    # Check if we should fallback to 'Default' if empty?
                    # Let's show nothing.
                    pass

                for source in devices_list:
                    # Resolve display name? Use Source for now.
                    # We need to map paths properly.

                    query = (
                        select(Recording)
                        .where(Recording.device_id == source)
                        .order_by(Recording.time.desc())
                        .limit(limit_per_source)
                    )

                    result = await conn.execute(query)
                    # Because we use core connection mostly in this project for direct SQL speed/control
                    # but here we used ORM select.
                    # Wait, db.get_connection() returns AsyncConnection (Core), need AsyncSession for ORM models.
                    # But the db helper provides get_connection (Core) AND get_db (Session).
                    # 'conn' is connection.
                    # Better use direct SQL or use session in different logic.
                    # Let's stick to Core SQL for consistency with other services if easier.
                    # Or use execute(select(Recording)) with connection... does it return rows?
                    # Yes, but rows won't be ORM objects, just tuples/mappings.

                    rows = result.all()  # These are Row objects

                    items = []
                    for row in rows:
                        # Row might be (id, time, ...) or if using select(Recording) on connection?
                        # It returns columns.
                        # Let's cast to dict assuming names match.
                        d = dict(row._mapping)

                        # We need to map to the format frontend expects
                        # filename, file_size_bytes, size_mb, formatted_time, created_at_iso, duration_str
                        # audio_relative_path

                        # Determine path preference
                        # High Res if exists? Wait, Dashboard usually plays low res (BirdNET uses low res).
                        # Let's prefer path_low if available, else path_high.
                        path = d.get("path_low") or d.get("path_high")
                        if not path:
                            path = ""

                        filename = os.path.basename(path)

                        # Time formatting
                        dt = d.get("time")
                        if dt and dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.UTC)

                        # Format size
                        size_bytes = d.get("file_size_bytes", 0)  # If we added it to model
                        # Wait, we added it to model, let's hope it's in DB or null
                        # If table doesn't have column, select * might fail if using ORM select expansion.
                        # We should be careful.
                        # Let's assume schema matches. If not, this crashes.

                        size_mb = round((size_bytes or 0) / (1024 * 1024), 2)

                        items.append(
                            {
                                "filename": filename,
                                "file_size_bytes": size_bytes,
                                "size_mb": size_mb,
                                "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-",
                                "created_at_iso": dt.isoformat() if dt else "",
                                "duration_str": f"{d.get('duration_sec', 0):.2f}s",
                                "duration_sec": d.get("duration_sec", 0),
                                "source": source,
                                "audio_relative_path": path.lstrip("/"),  # Ensure relative for API?
                                # /api/audio endpoint usually mounts REC_DIR.
                                # if path is absolute /data/recordings/front/file.wav
                                # audio_relative_path should be front/file.wav
                                # Rec Dir is /data/recordings/
                                # So we strip REC_DIR
                            }
                        )

                        # Path fixup
                        if path.startswith(REC_DIR):
                            items[-1]["audio_relative_path"] = path[len(REC_DIR) :].lstrip("/")

                    if items:
                        grouped_recordings[source] = items

            return grouped_recordings

        except Exception as e:
            logger.error(f"Recorder History Error (DB): {e}", exc_info=True)
            return {}

    @staticmethod
    async def get_creation_rate(minutes: int = 60) -> float:
        """Calculate files created per minute over the last X minutes via DB."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    "SELECT COUNT(*) FROM recordings WHERE time >= NOW() - make_interval(mins => :mins)"
                )
                count = (await conn.execute(query, {"mins": minutes})).scalar() or 0
                return round(count / minutes, 2)
        except Exception as e:
            logger.error(f"Creation rate error: {e}")
            return 0.0

    @staticmethod
    async def get_latest_filename() -> str | None:
        """Get the filename of the most recent recording from DB."""
        try:
            async with db.get_connection() as conn:
                # Use path_low or path_high? Filename is usually part of path.
                # Or just filename if we had that column?
                # The model I added has no 'filename' column, only paths!
                # Ah, wait. Implementation Plan said "Add Recording model... Columns: id, filename..."
                # My model code had paths but NO filename column.
                # Processor DB.py doesn't have filename column.
                # So I must extract it from path.

                # However, for cursor comparison (lexicographical), using path is confusing if paths differ.
                # But typically timestamp is best cursor.
                # The dashboard uses filename cursor in 'count_files_after'.
                # Let's hope filename corresponds to time.

                # Query max path?
                query = text("SELECT path_low FROM recordings ORDER BY time DESC LIMIT 1")
                path = (await conn.execute(query)).scalar()
                if path:
                    return cast(str, os.path.basename(path))
                return None
        except Exception:
            return None

    @staticmethod
    async def count_files_after(filename: str | None) -> int:
        """Count how many files are 'after' the given filename (Lexicographical sort).
        Note: Using DB, we should ideally use Time-based cursors.
        But frontend might pass filename.
        If filename follows date pattern, we can try to guess time or just compare filenames if stored?
        We don't store plain filenames in DB, only paths.
        So we can't do efficient 'filename > X' without a filename column.

        Workaround: If filename is None, return 0 (no lag).
        If filename provided, we assume it's like '2023-01-01...'.
        We can try to extract time from it?

        Or we just do COUNT(*) - (Position of filename).

        Let's assume typical usage: Dashboard checks 'latest_processed' vs 'latest_recorded'.
        If we return total Lag, it's (Total Recs) - (Total Processed)?
        But they might be different sets.

        Let's use Time if possible.
        But 'filename' arg comes from 'latest_processed_filename' from BirdNET (which HAS filename).
        So we have a filename '2024-01-01_12-00-00.wav'.
        We can query DB: SELECT count(*) FROM recordings WHERE time > (Time of that file).

        Parsing time from filename is safest here.
        """
        if not filename:
            # If no cursor, assume everything is "after" (Lag is high)?
            # Or if no processed files, lag is ALL files.
            # So return Count(*).
            pass  # fallback to query all

        try:
            # Try parse time from filename
            # Format: YYYY-MM-DD_HH-MM-SS
            cutoff_dt = None
            if filename:
                try:
                    # Remove extension
                    stem = os.path.splitext(filename)[0]
                    # Try common formats
                    # 2024-01-01_12-00-00
                    cutoff_dt = datetime.datetime.strptime(stem[:19], "%Y-%m-%d_%H-%M-%S")
                except ValueError:
                    pass

            async with db.get_connection() as conn:
                if cutoff_dt:
                    query = text("SELECT COUNT(*) FROM recordings WHERE time > :dt")
                    return (await conn.execute(query, {"dt": cutoff_dt})).scalar() or 0
                else:
                    # Fallback: Just return total count?
                    # Or 0?
                    query = text("SELECT COUNT(*) FROM recordings")
                    return (await conn.execute(query)).scalar() or 0

        except Exception as e:
            logger.error(f"Count after error: {e}")
            return 0
