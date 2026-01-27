import datetime
import typing

from sqlalchemy import text
from src.settings import SettingsService

from .common import REC_DIR, logger
from .database import db


class BirdNetStatsService:
    @staticmethod
    async def get_stats() -> dict[str, typing.Any]:
        """Get basic stats for dashboard widgets."""
        try:
            async with db.get_connection() as conn:
                # Today
                today_start = datetime.datetime.utcnow().date()
                query_today = text(
                    "SELECT COUNT(*) FROM birdnet.detections WHERE timestamp >= :today"
                )
                today_count = (
                    await conn.execute(query_today, {"today": today_start})
                ).scalar() or 0

                # Total
                query_total = text("SELECT COUNT(*) FROM birdnet.detections")
                total_count = (await conn.execute(query_total)).scalar() or 0

                # Top Species
                query_top = text("""
                    SELECT 
                        d.common_name as com_name, 
                        MAX(s.german_name) as german_name, 
                        COUNT(*) as count 
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info s ON d.scientific_name = s.scientific_name
                    GROUP BY d.common_name 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                result_top = await conn.execute(query_top)

                use_german = SettingsService.is_german_names_enabled()
                top_species = []
                for row in result_top:
                    r = dict(row._mapping)
                    r["display_name"] = (
                        r.get("german_name")
                        if use_german and r.get("german_name")
                        else r.get("com_name")
                    )
                    top_species.append(r)

                # Species Count
                query_species = text(
                    "SELECT COUNT(DISTINCT scientific_name) FROM birdnet.detections"
                )
                species_count = (await conn.execute(query_species)).scalar() or 0

                # Biodiversity (Menhinick's Index: D = S / sqrt(N))
                biodiversity = 0.0
                if total_count > 0:
                    biodiversity = round(species_count / (total_count**0.5), 3)

                return {
                    "today": today_count,
                    "total": total_count,
                    "species_count": species_count,
                    "biodiversity": biodiversity,
                    "top_species": top_species,
                }
        except Exception as e:
            logger.error(f"Error getting BirdNet Stats: {e}", exc_info=True)
            return {"today": 0, "total": 0, "top_species": []}

    @staticmethod
    async def get_advanced_stats(
        start_date: datetime.date | None = None, end_date: datetime.date | None = None
    ) -> dict[str, typing.Any]:
        """Get comprehensive stats for the BirdStats dashboard with optional date filtering."""
        try:
            # Defaults
            if not start_date:
                start_date = datetime.date.today() - datetime.timedelta(days=30)
            if not end_date:
                end_date = datetime.date.today()

            # Ensure they are datetime objects for comparison if needed, but SQL parameters handle dates fine.
            
            async with db.get_connection() as conn:
                # 1. Activity Trend (Daily counts within range)
                query_daily = text("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE DATE(timestamp) >= :start_date 
                      AND DATE(timestamp) <= :end_date
                    GROUP BY date
                    ORDER BY date ASC
                """)
                res_daily = await conn.execute(
                    query_daily, {"start_date": start_date, "end_date": end_date}
                )
                
                # ApexCharts desires: { x: '2023-01-01', y: 10 }
                daily_series = []
                for row in res_daily:
                    if row.date:
                        daily_series.append({
                            "x": row.date.strftime("%Y-%m-%d"),
                            "y": row.count
                        })

                # 2. Hourly Distribution (within range)
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE DATE(timestamp) >= :start_date 
                      AND DATE(timestamp) <= :end_date
                    GROUP BY hour
                    ORDER BY hour ASC
                """)
                res_hourly = await conn.execute(
                    query_hourly, {"start_date": start_date, "end_date": end_date}
                )
                
                hourly_map = {r.hour: r.count for r in res_hourly if r.hour is not None}
                # ApexCharts category series: data array matching categories [0, 1, ... 23]
                hourly_data = [hourly_map.get(h, 0) for h in range(24)]

                # 3. Top Species Distribution (within range)
                query_top = text("""
                    SELECT common_name, COUNT(*) as count 
                    FROM birdnet.detections 
                    WHERE DATE(timestamp) >= :start_date 
                      AND DATE(timestamp) <= :end_date
                      AND common_name IS NOT NULL
                    GROUP BY common_name 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                res_top = await conn.execute(
                    query_top, {"start_date": start_date, "end_date": end_date}
                )
                
                top_labels = []
                top_values = []
                for row in res_top:
                    top_labels.append(row.common_name)
                    top_values.append(row.count)

                # 4. Rarest Specifications (Just a list, maybe easiest within range too)
                # To find "rarest" within this period might be just low counts. 
                # Or "globally rare" seen in this period? Let's do "Least frequent in this period".
                query_rarest = text("""
                    SELECT common_name, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE DATE(timestamp) >= :start_date 
                      AND DATE(timestamp) <= :end_date
                      AND common_name IS NOT NULL
                    GROUP BY common_name
                    ORDER BY count ASC
                    LIMIT 10
                """)
                res_rarest = await conn.execute(
                    query_rarest, {"start_date": start_date, "end_date": end_date}
                )
                rarest_list = [dict(row._mapping) for row in res_rarest]

                return {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "daily": daily_series,
                    "hourly": hourly_data,
                    "top_species": {
                        "labels": top_labels,
                        "values": top_values
                    },
                    "rarest": rarest_list
                }

        except Exception as e:
            logger.error(f"Error get_advanced_stats: {e}", exc_info=True)
            return {
                "period": {"start": str(start_date), "end": str(end_date)},
                "daily": [],
                "hourly": [],
                "top_species": {"labels": [], "values": []},
                "rarest": []
            }

    @staticmethod
    async def get_species_stats(species_name: str) -> dict[str, typing.Any] | None:
        """Get detailed stats for a specific species."""
        try:
            async with db.get_connection() as conn:
                # Basic Info
                query_info = text("""
                    SELECT 
                        common_name as com_name, 
                        scientific_name as sci_name,
                        COUNT(*) as total_count,
                        MAX(timestamp) as last_seen,
                        MIN(timestamp) as first_seen,
                        AVG(confidence) as avg_conf,
                        MAX(confidence) as max_conf
                    FROM birdnet.detections
                    WHERE common_name = :name
                    GROUP BY common_name, scientific_name
                """)
                res_info = (await conn.execute(query_info, {"name": species_name})).fetchone()
                if not res_info:
                    return None

                info = dict(res_info._mapping)
                if info.get("first_seen"):
                    if info["first_seen"].tzinfo is None:
                        info["first_seen"] = info["first_seen"].replace(tzinfo=datetime.UTC)
                    info["first_seen_iso"] = info["first_seen"].isoformat()
                if info.get("last_seen"):
                    if info["last_seen"].tzinfo is None:
                        info["last_seen"] = info["last_seen"].replace(tzinfo=datetime.UTC)
                    info["last_seen_iso"] = info["last_seen"].isoformat()

                # Recent Detections
                query_recent = text("""
                    SELECT * FROM birdnet.detections 
                    WHERE common_name = :name 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """)
                res_recent = await conn.execute(query_recent, {"name": species_name})
                recent = []
                import os  # Local import

                for row in res_recent:
                    d = dict(row._mapping)
                    if d.get("timestamp"):
                        if d["timestamp"].tzinfo is None:
                            d["timestamp"] = d["timestamp"].replace(tzinfo=datetime.UTC)
                        d["iso_timestamp"] = d["timestamp"].isoformat()
                    else:
                        d["iso_timestamp"] = ""

                    fp = d.get("filepath")
                    if fp and fp.startswith(REC_DIR):
                        d["audio_relative_path"] = fp[len(REC_DIR) :].lstrip("/")
                    else:
                        d["audio_relative_path"] = d.get("filename")

                    if d.get("clip_path"):
                        d["playback_url"] = f"/api/clips/{os.path.basename(d['clip_path'])}"
                    else:
                        d["playback_url"] = f"/api/audio/{d.get('audio_relative_path')}"

                    recent.append(d)

                # Hourly Distribution
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE common_name = :name
                    GROUP BY hour
                    ORDER BY hour
                """)
                res_hourly = await conn.execute(query_hourly, {"name": species_name})
                hourly_dist = {int(r.hour): r.count for r in res_hourly if r.hour is not None}
                hourly_data = [hourly_dist.get(h, 0) for h in range(24)]

                return {"info": info, "recent": recent, "hourly": hourly_data}
        except Exception as e:
            logger.error(f"Error get_species_stats: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_all_detections_cursor() -> typing.AsyncGenerator[dict[str, typing.Any], None]:
        """Yields all detections efficiently for export."""
        async with db.get_connection() as conn:
            query = text("""
                SELECT 
                    timestamp,
                    scientific_name,
                    common_name,
                    confidence,
                    start_time,
                    end_time,
                    filename
                FROM birdnet.detections
                ORDER BY timestamp DESC
            """)

            result = await conn.stream(query)

            async for row in result:
                yield dict(row._mapping)
