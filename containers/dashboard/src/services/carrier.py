import datetime
import json
import os
import time

from sqlalchemy import text

from .common import STATUS_DIR
from .database import db


class CarrierService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(STATUS_DIR, "carrier.json")
            if os.path.exists(status_file):
                with open(status_file) as f:
                    data = json.load(f)

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
                            data["last_upload_ago"] = f"{int(ago/60)}m ago"
                        else:
                            data["last_upload_ago"] = f"{int(ago/3600)}h ago"
                    else:
                        data["last_upload_str"] = "Never"
                        data["last_upload_ago"] = ""

                    data["queue_size"] = data.get("meta", {}).get("queue_size", -1)
                    data["disk_usage"] = round(data.get("meta", {}).get("disk_usage_percent", 0), 1)
                    return data
        except Exception as e:
            print(f"Carrier status error: {e}")

        return {
            "status": "Unknown",
            "last_upload_str": "Unknown",
            "last_upload_ago": "",
            "queue_size": -1,
            "disk_usage": 0
        }

    @staticmethod
    async def get_recent_uploads(limit=100):
        """Fetch recent successful uploads."""
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT filename, remote_path, size_bytes, upload_time 
                    FROM carrier.uploads 
                    WHERE status = 'success' 
                    ORDER BY upload_time DESC 
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('upload_time'):
                         if d['upload_time'].tzinfo is None: d['upload_time'] = d['upload_time'].replace(tzinfo=datetime.UTC)
                         d['upload_time_str'] = d['upload_time'].strftime("%Y-%m-%d %H:%M:%S")

                    d['size_mb'] = round((d.get('size_bytes') or 0) / (1024*1024), 2)
                    items.append(d)
                return items
        except Exception as e:
            print(f"Carrier recent uploads error: {e}")
            return []

    @staticmethod
    async def get_failed_uploads(limit=50):
        """Fetch recent failed uploads."""
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT filename, error_message, upload_time 
                    FROM carrier.uploads 
                    WHERE status = 'failed' 
                    ORDER BY upload_time DESC 
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('upload_time'):
                         if d['upload_time'].tzinfo is None: d['upload_time'] = d['upload_time'].replace(tzinfo=datetime.UTC)
                         d['upload_time_str'] = d['upload_time'].strftime("%Y-%m-%d %H:%M:%S")
                    items.append(d)
                return items
        except Exception as e:
            print(f"Carrier failed uploads error: {e}")
            return []

    @staticmethod
    async def get_upload_stats():
        """Fetch upload counts for different time ranges."""
        try:
            async with db.get_connection() as conn:
                # We can do this in one query with FILTER or multiple.
                # Postgres FILTER is elegant.
                query = text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '1 HOUR') as last_1h,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '24 HOURS') as last_24h,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '7 DAYS') as last_7d,
                        COUNT(*) FILTER (WHERE upload_time >= NOW() - INTERVAL '30 DAYS') as last_30d
                    FROM carrier.uploads
                    WHERE status = 'success'
                """)
                row = (await conn.execute(query)).fetchone()
                if row:
                    return dict(row._mapping)
        except Exception as e:
            print(f"Carrier stats error: {e}")

        return {"last_1h": 0, "last_24h": 0, "last_7d": 0, "last_30d": 0}
