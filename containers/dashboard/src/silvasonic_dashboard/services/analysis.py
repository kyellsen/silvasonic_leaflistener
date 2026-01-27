import typing
from datetime import UTC

from sqlalchemy import text

from .common import logger
from .database import db


class AnalyzerService:
    @staticmethod
    async def get_recent_analysis(limit: int = 50) -> list[dict[str, typing.Any]]:
        """Get list of recently processed files from BirdNET."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    """
                    SELECT 
                        filename,
                        audio_duration_sec as duration_sec,
                        file_size_bytes,
                        processed_at as created_at
                    FROM birdnet.processed_files
                    ORDER BY processed_at DESC
                    LIMIT :limit
                """
                )
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

                    # Format size
                    if d.get("file_size_bytes"):
                        d["size_fmt"] = AnalyzerService._format_size(d["file_size_bytes"])
                    else:
                        d["size_fmt"] = "-"

                    # Format duration
                    if d.get("duration_sec"):
                        d["duration_fmt"] = AnalyzerService._format_duration(d["duration_sec"])
                    else:
                        d["duration_fmt"] = "-"

                    # No more spectrograms or metrics for basic file list
                    d["spec_url"] = None
                    d["peak_frequency_hz"] = None
                    d["rms_loudness"] = None

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

        return " ".join(parts[:2])

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
        """Get aggregate stats from BirdNET processed files."""
        try:
            async with db.get_connection() as conn:
                query = text(
                    """
                    SELECT 
                        COUNT(*) as total_files,
                        COALESCE(SUM(audio_duration_sec), 0) as total_duration,
                        AVG(audio_duration_sec) as avg_duration,
                        AVG(file_size_bytes) as avg_size
                    FROM birdnet.processed_files
                """
                )
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
