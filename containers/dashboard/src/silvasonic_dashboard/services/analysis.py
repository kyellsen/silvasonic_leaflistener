import os
import typing
from datetime import UTC

from sqlalchemy import text

from .common import logger
from .database import db


class AnalyzerService:
    @staticmethod
    async def get_recent_analysis(limit: int = 20) -> list[dict[str, typing.Any]]:
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        af.filename,
                        af.duration_sec,
                        af.file_size_bytes,
                        af.created_at,
                        am.rms_loudness,
                        am.peak_frequency_hz,
                        art.filepath as spec_path
                    FROM brain.audio_files af
                    LEFT JOIN brain.analysis_metrics am ON af.id = am.audio_file_id
                    LEFT JOIN brain.artifacts art ON af.id = art.audio_file_id AND art.artifact_type = 'spectrogram'
                    ORDER BY af.created_at DESC
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get("created_at"):
                        if d["created_at"].tzinfo is None:
                            d["created_at"] = d["created_at"].replace(tzinfo=UTC)
                        d["created_at_iso"] = d["created_at"].isoformat()
                    else:
                        d["created_at_iso"] = ""

                    # Fix spec path
                    if d.get("spec_path"):
                        fname = os.path.basename(d["spec_path"])
                        d["spec_url"] = f"/api/spectrogram/{fname}"
                    else:
                        d["spec_url"] = None

                    # Format size
                    if d.get("file_size_bytes"):
                        d["size_fmt"] = AnalyzerService._format_size(d["file_size_bytes"])
                    else:
                        d["size_fmt"] = "0 B"

                    # Format duration
                    if d.get("duration_sec"):
                        d["duration_fmt"] = AnalyzerService._format_duration(d["duration_sec"])
                    else:
                        d["duration_fmt"] = "-"

                    # Round metrics
                    if d.get("rms_loudness"):
                        d["rms_loudness"] = round(d["rms_loudness"], 1)
                    if d.get("peak_frequency_hz"):
                        d["peak_frequency_hz"] = int(d["peak_frequency_hz"])

                    items.append(d)
                return items
        except Exception as e:
            logger.error(f"Analyzer Error: {e}", exc_info=True)
            return []

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into readable string (e.g. 2h 30m 15s)"""
        if not seconds:
            return "0s"

        # Check for bad data (e.g. timestamps or nanoseconds)
        # If > 50 years (approx 1.5 billion seconds), assuming it's a timestamp or garbage -> 0
        if seconds > 1577880000:
            return "Invalid"

        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        parts = []
        if d > 0:
            parts.append(f"{d}d")
        if h > 0:
            parts.append(f"{h}h")
        if m > 0:
            parts.append(f"{m}m")
        if s > 0 or not parts:
            parts.append(f"{s}s")

        return " ".join(parts[:2])  # Return max 2 significant parts

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if not size_bytes:
            return "0 B"

        s: float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if s < 1024:
                return f"{s:.1f} {unit}"
            s /= 1024
        return f"{s:.1f} TB"

    @staticmethod
    async def get_stats() -> dict[str, typing.Any]:
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        COUNT(*) as total_files,
                        COALESCE(SUM(duration_sec), 0) as total_duration,
                        AVG(duration_sec) as avg_duration,
                        AVG(file_size_bytes) as avg_size
                    FROM brain.audio_files
                """)
                res = (await conn.execute(query)).fetchone()
                if res:
                    d = dict(res._mapping)

                    raw_total = d.get("total_duration", 0)
                    raw_avg = d.get("avg_duration", 0)

                    d["total_duration_fmt"] = AnalyzerService._format_duration(raw_total)
                    d["avg_duration_fmt"] = AnalyzerService._format_duration(raw_avg)
                    d["avg_size_fmt"] = AnalyzerService._format_size(d.get("avg_size") or 0)

                    return d
                return {}
        except Exception as e:
            logger.error(f"Analyzer Stats Error: {e}", exc_info=True)
            return {}
