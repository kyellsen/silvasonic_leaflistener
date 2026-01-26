import json
import os
from datetime import UTC

from sqlalchemy import text

from .common import REC_DIR, STATUS_DIR
from .database import db


class RecorderService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(STATUS_DIR, "recorder.json")
            if os.path.exists(status_file):
                with open(status_file) as f:
                    data = json.load(f)

                    # Flatten meta for compatibility or just return rich data
                    meta = data.get("meta", {})
                    data["profile"] = meta.get("profile", "Unknown")
                    data["device"] = meta.get("device", "Unknown")

                    return data
        except Exception as e:
            print(f"Recorder status error: {e}")

        return {"status": "Unknown", "profile": "Unknown", "device": "Unknown"}

    @staticmethod
    async def get_recent_recordings(limit=20):
        try:
             async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        filename,
                        duration_sec,
                        file_size_bytes,
                        created_at
                    FROM brain.audio_files
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('created_at'):
                        if d['created_at'].tzinfo is None:
                             d['created_at'] = d['created_at'].replace(tzinfo=UTC)
                        d['created_at_iso'] = d['created_at'].isoformat()
                        d['formatted_time'] = d['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        d['created_at_iso'] = ""
                        d['formatted_time'] = "Unknown"

                    # Calculate Size in MB
                    d['size_mb'] = round((d.get('file_size_bytes') or 0) / (1024*1024), 2)
                    d['duration_str'] = f"{d.get('duration_sec', 0):.1f}s"

                    # Audio Path Logic (Recorder usually stores just filename in filename column, or full path?)
                    # brain.audio_files table usually is populated by Carrier/Recorder.
                    # If filename is just "file.flac", it's relative to REC_DIR?
                    # Let's assume filename IS the relative path or base name.
                    # But we should try to be smart.

                    # Ideally we have a filepath column in audio_files too?
                    # The query selects: filename.
                    fname = d.get('filename')
                    # If it's a full path
                    if fname and fname.startswith(REC_DIR):
                        d['audio_relative_path'] = fname[len(REC_DIR):].lstrip('/')
                    else:
                        d['audio_relative_path'] = fname

                    items.append(d)
                return items
        except Exception as e:
            print(f"Recorder History Error: {e}")
            return []
