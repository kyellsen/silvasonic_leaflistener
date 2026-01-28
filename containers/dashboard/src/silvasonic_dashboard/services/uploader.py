import datetime
import json
import os
import time
import typing

import redis
from sqlalchemy import text

from .database import db


class UploaderService:
    @staticmethod
    def get_status() -> dict[str, typing.Any]:
        try:
            r = redis.Redis(host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1)
            # Uploader writes status:uploader:<sensor_id>
            # We scan for any uploader status
            keys = r.keys("status:uploader:*")
            if not keys:
                # Try legacy key if exists
                if r.exists("status:uploader"):
                    keys = [b"status:uploader"]

            if keys:
                # Just take the first one for now (Singleton assumption for dashboard view)
                raw = r.get(keys[0])
                if raw:
                    data = json.loads(raw)

                    # Convert last_upload ts to readable
                    last_upload = data.get("meta", {}).get("last_upload", 0)
                    if last_upload == 0:
                        # Fallback to top level if older format or transition
                        last_upload = data.get("last_upload", 0)

                    if last_upload > 0:
                        dt = datetime.datetime.fromtimestamp(last_upload)
                        data["last_upload_str"] = dt.strftime("%H:%M:%S")

                        # Add relative time
                        ago = time.time() - last_upload
                        if ago < 60:
                            data["last_upload_ago"] = "Just now"
                        elif ago < 3600:
                            data["last_upload_ago"] = f"{int(ago / 60)}m ago"
                        else:
                            data["last_upload_ago"] = f"{int(ago / 3600)}h ago"
                    else:
                        data["last_upload_str"] = "Never"
                        data["last_upload_ago"] = ""

                    data["queue_size"] = data.get("meta", {}).get("queue_size", -1)
                    data["disk_usage"] = round(data.get("meta", {}).get("disk_usage_percent", 0), 1)
                    return typing.cast(dict[str, typing.Any], data)

        except Exception as e:
            print(f"Uploader status error: {e}")

        return {
            "status": "Unknown",
            "last_upload_str": "Unknown",
            "last_upload_ago": "",
            "queue_size": -1,
            "disk_usage": 0,
        }

    @staticmethod
    async def get_recent_uploads(limit: int = 100) -> list[dict[str, typing.Any]]:
        """Fetch recent successful uploads."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    """
                    SELECT filename, remote_path, size_bytes, upload_time 
                    FROM uploader.uploads 
                    WHERE status = 'success' 
                    ORDER BY upload_time DESC 
                    LIMIT :limit
                """
                )
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get("upload_time"):
                        if d["upload_time"].tzinfo is None:
                            d["upload_time"] = d["upload_time"].replace(tzinfo=datetime.UTC)
                        d["upload_time_str"] = d["upload_time"].strftime("%Y-%m-%d %H:%M:%S")
                        # Convert to string for JSON serialization
                        d["upload_time"] = d["upload_time"].isoformat()

                    d["size_mb"] = round((d.get("size_bytes") or 0) / (1024 * 1024), 2)

                    # Derive Source from filename (e.g. "front/2023..." -> "front")
                    fname = d.get("filename", "")
                    if "/" in fname:
                        d["source"] = fname.split("/")[0]
                        d["filename_only"] = os.path.basename(fname)
                    else:
                        d["source"] = "Default"
                        d["filename_only"] = fname

                    items.append(d)
                return items
        except Exception as e:
            print(f"Uploader recent uploads error: {e}")
            return []

    @staticmethod
    async def get_failed_uploads(limit: int = 50) -> list[dict[str, typing.Any]]:
        """Fetch recent failed uploads."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    """
                    SELECT filename, error_message, upload_time 
                    FROM uploader.uploads 
                    WHERE status = 'failed' 
                    ORDER BY upload_time DESC 
                    LIMIT :limit
                """
                )
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get("upload_time"):
                        if d["upload_time"].tzinfo is None:
                            d["upload_time"] = d["upload_time"].replace(tzinfo=datetime.UTC)
                        d["upload_time_str"] = d["upload_time"].strftime("%Y-%m-%d %H:%M:%S")
                        # Convert to string for JSON serialization
                        d["upload_time"] = d["upload_time"].isoformat()
                    items.append(d)
                return items
        except Exception as e:
            print(f"Uploader failed uploads error: {e}")
            return []

    @staticmethod
    async def get_upload_stats() -> dict[str, int]:
        """Fetch upload counts for different time ranges."""
        try:
            async with db.get_connection() as conn:
                # We can do this in one query with FILTER or multiple.
                # Postgres FILTER is elegant.
                query = text(
                    """
                    SELECT 
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '1 HOUR') as last_1h,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '24 HOURS') as last_24h,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '7 DAYS') as last_7d,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '30 DAYS') as last_30d
                    FROM uploader.uploads
                    WHERE status = 'success'
                """
                )
                row = (await conn.execute(query)).fetchone()
                if row:
                    return dict(row._mapping)
        except Exception as e:
            print(f"Uploader stats error: {e}")

        return {"last_1h": 0, "last_24h": 0, "last_7d": 0, "last_30d": 0}

    @staticmethod
    async def get_upload_rate(minutes: int = 60) -> float:
        """Calculate files uploaded per minute over the last X minutes."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    "SELECT COUNT(*) FROM uploader.uploads WHERE status='success' AND upload_time >= NOW() - make_interval(mins => :mins)"
                )
                count = (await conn.execute(query, {"mins": minutes})).scalar() or 0
                return round(count / minutes, 2)
        except Exception as e:
            print(f"Uploader Rate Error: {e}")
            return 0.0

    @staticmethod
    async def get_latest_uploaded_filename() -> str | None:
        """Get the filename of the most recently uploaded file."""
        try:
            async with db.get_connection() as conn:
                query = text("SELECT MAX(filename) FROM uploader.uploads WHERE status='success'")
                return (await conn.execute(query)).scalar()  # type: ignore[no-any-return]
        except Exception:
            return None
