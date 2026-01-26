import datetime
from sqlalchemy import text
from .database import db
from .common import logger, REC_DIR
from src.settings import SettingsService

class BirdNetStatsService:
    @staticmethod
    async def get_stats():
        """Get basic stats for dashboard widgets."""
        try:
            async with db.get_connection() as conn:
                # Today
                today_start = datetime.datetime.utcnow().date()
                query_today = text("SELECT COUNT(*) FROM birdnet.detections WHERE timestamp >= :today")
                today_count = (await conn.execute(query_today, {"today": today_start})).scalar()

                # Total
                query_total = text("SELECT COUNT(*) FROM birdnet.detections")
                total_count = (await conn.execute(query_total)).scalar()

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
                    r['display_name'] = r.get('german_name') if use_german and r.get('german_name') else r.get('com_name')
                    top_species.append(r)

                # Species Count
                query_species = text("SELECT COUNT(DISTINCT scientific_name) FROM birdnet.detections")
                species_count = (await conn.execute(query_species)).scalar() or 0

                # Biodiversity (Menhinick's Index: D = S / sqrt(N))
                biodiversity = 0.0
                if total_count > 0:
                    biodiversity = round(species_count / (total_count ** 0.5), 3)

                return {
                    "today": today_count,
                    "total": total_count,
                    "species_count": species_count,
                    "biodiversity": biodiversity,
                    "top_species": top_species
                }
        except Exception as e:
            logger.error(f"Error getting BirdNet Stats: {e}", exc_info=True)
            return {"today": 0, "total": 0, "top_species": []}

    @staticmethod
    async def get_advanced_stats():
        """Get comprehensive stats for the BirdStats dashboard."""
        try:
            async with db.get_connection() as conn:
                # 1. Daily Trend (Last 30 Days)
                query_daily = text("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE timestamp >= NOW() - INTERVAL '30 DAYS'
                      AND timestamp IS NOT NULL
                    GROUP BY date
                    ORDER BY date ASC
                """)
                res_daily = await conn.execute(query_daily)
                daily = {"labels": [], "values": []}
                for row in res_daily:
                    if row.date:
                        daily["labels"].append(row.date.strftime("%Y-%m-%d"))
                        daily["values"].append(row.count)

                # 2. Hourly Distribution (All Time)
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE timestamp IS NOT NULL
                    GROUP BY hour
                """)
                res_hourly = await conn.execute(query_hourly)
                dist_map = {}
                for r in res_hourly:
                    if r.hour is not None:
                        dist_map[int(r.hour)] = r.count
                
                hourly = {"values": [dist_map.get(h, 0) for h in range(24)]}

                # 3. Top Species Distributions (Pie Charts)
                async def get_top_species(interval_clause, limit=20):
                    where_sql = "WHERE timestamp IS NOT NULL"
                    if interval_clause:
                        where_sql += f" AND timestamp >= NOW() - INTERVAL '{interval_clause}'"

                    query = text(f"""
                        SELECT common_name, COUNT(*) as count 
                        FROM birdnet.detections 
                        {where_sql}
                        GROUP BY common_name 
                        ORDER BY count DESC 
                        LIMIT :limit
                    """)
                    result = await conn.execute(query, {"limit": limit})
                    rows = result.fetchall()
                    return {
                        "labels": [r.common_name for r in rows if r.common_name],
                        "values": [r.count for r in rows if r.common_name]
                    }

                query_today_exact = text("""
                    SELECT common_name, COUNT(*) as count 
                    FROM birdnet.detections 
                    WHERE DATE(timestamp) = CURRENT_DATE
                      AND timestamp IS NOT NULL
                    GROUP BY common_name 
                    ORDER BY count DESC 
                    LIMIT 20
                """)
                result_today = await conn.execute(query_today_exact)
                rows_today = result_today.fetchall()
                dist_today = {
                    "labels": [r.common_name for r in rows_today if r.common_name], 
                    "values": [r.count for r in rows_today if r.common_name]
                }

                dist_week = await get_top_species("7 DAYS")
                dist_month = await get_top_species("30 DAYS")
                dist_year = await get_top_species("1 YEAR")
                dist_all = await get_top_species(None)

                # 4. Histogram (All Species Ranked)
                query_all = text("""
                    SELECT common_name, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE common_name IS NOT NULL
                    GROUP BY common_name
                    ORDER BY count DESC
                """)
                res_all = await conn.execute(query_all)
                hist_labels = []
                hist_values = []
                
                all_rows = []
                for row in res_all:
                    d = dict(row._mapping)
                    if d.get('common_name'):
                        all_rows.append(d)
                        hist_labels.append(d['common_name'])
                        hist_values.append(d['count'])

                # 5. Rarest Species (List)
                rarest_list = []
                if len(all_rows) > 0:
                    rarest_slice = all_rows[-20:]
                    rarest_list = sorted(rarest_slice, key=lambda x: x['count'])

                return {
                    "daily": daily,
                    "hourly": hourly,
                    "distributions": {
                        "today": dist_today,
                        "week": dist_week,
                        "month": dist_month,
                        "year": dist_year,
                        "all_time": dist_all
                    },
                    "histogram": {
                        "labels": hist_labels,
                        "values": hist_values
                    },
                    "rarest": rarest_list
                }
        except Exception as e:
            logger.error(f"Error get_advanced_stats: {e}", exc_info=True)
            empty_chart = {"labels": [], "values": []}
            return {
                "daily": empty_chart,
                "hourly": {"values": []},
                "distributions": {
                    "today": empty_chart, "week": empty_chart,
                    "month": empty_chart, "year": empty_chart,
                    "all_time": empty_chart
                },
                "histogram": empty_chart,
                "rarest": []
            }

    @staticmethod
    async def get_species_stats(species_name: str):
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
                if info.get('first_seen'):
                    if info['first_seen'].tzinfo is None: info['first_seen'] = info['first_seen'].replace(tzinfo=datetime.UTC)
                    info['first_seen_iso'] = info['first_seen'].isoformat()
                if info.get('last_seen'):
                    if info['last_seen'].tzinfo is None: info['last_seen'] = info['last_seen'].replace(tzinfo=datetime.UTC)
                    info['last_seen_iso'] = info['last_seen'].isoformat()

                # Recent Detections
                query_recent = text("""
                    SELECT * FROM birdnet.detections 
                    WHERE common_name = :name 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """)
                res_recent = await conn.execute(query_recent, {"name": species_name})
                recent = []
                for row in res_recent:
                    d = dict(row._mapping)
                    if d.get('timestamp'):
                         if d['timestamp'].tzinfo is None: d['timestamp'] = d['timestamp'].replace(tzinfo=datetime.UTC)
                         d['iso_timestamp'] = d['timestamp'].isoformat()
                    else:
                         d['iso_timestamp'] = ""

                    fp = d.get('filepath')
                    if fp and fp.startswith(REC_DIR):
                        d['audio_relative_path'] = fp[len(REC_DIR):].lstrip('/')
                    else:
                        d['audio_relative_path'] = d.get('filename')

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

                return {
                    "info": info,
                    "recent": recent,
                    "hourly": hourly_data
                }
        except Exception as e:
            logger.error(f"Error get_species_stats: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_all_detections_cursor():
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
