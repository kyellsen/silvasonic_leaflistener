import os
import psutil
import datetime
import time
from datetime import timezone
import shutil
from pathlib import Path
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.settings import SettingsService

# Paths
DB_PATH = "/data/birdnet_db/birdnet.sqlite"
REC_DIR = "/data/recording"
LOG_DIR = "/var/log/silvasonic"

class DatabaseHandler:
    def __init__(self):
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        
        self.db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.engine = create_engine(self.db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)

    def get_connection(self):
        return self.engine.connect()

db = DatabaseHandler()

class SystemService:
    @staticmethod
    def get_stats():
        try:
            cpu = psutil.cpu_percent(interval=None)
        except:
            cpu = 0
            
        try:
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
        except:
            class MockMem:
                percent = 0
            mem = MockMem()
            mem_percent = 0
        
        # Disk usage for /mnt/data (mapped to /data/recording usually or root)
        # using /data/recording as proxy for NVMe
        try:
            disk = shutil.disk_usage("/data/recording")
            disk_percent = (disk.used / disk.total) * 100
        except:
            disk_percent = 0

        # Boot time
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
        except:
            uptime = "Unknown"
        
        # Last Recording
        last_rec = "Unknown"
        last_rec_ts = 0
        try:
            files = sorted(Path(REC_DIR).glob("**/*.flac"), key=os.path.getmtime, reverse=True)
            if files:
                last_rec_ts = files[0].stat().st_mtime
                last_rec = datetime.datetime.fromtimestamp(last_rec_ts).strftime("%H:%M:%S")
        except:
            pass
            
            pass

        # CPU Temperature
        cpu_temp = "N/A"
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_c = int(f.read().strip()) / 1000.0
                cpu_temp = f"{temp_c:.1f}°C"
        except:
            pass
            
        return {
            "cpu": cpu,
            "cpu_temp": cpu_temp,
            "ram_percent": mem_percent,
            "disk_percent": round(disk_percent, 1),
            "uptime_str": str(uptime).split('.')[0] if isinstance(uptime, datetime.timedelta) else str(uptime),
            "last_recording": last_rec,
            "last_recording_ago": int(datetime.datetime.now().timestamp() - last_rec_ts) if last_rec_ts > 0 else -1
        }

class BirdNetService:
    @staticmethod
    def get_recent_detections(limit=10):
        try:
            with db.get_connection() as conn:
                # Query matches BirdNET schema: birdnet.detections table
                # We need to manually split timestamp into date/time map for value compatibility with template
                query = text("""
                    SELECT 
                        d.filepath, 
                        d.start_time, 
                        d.end_time, 
                        d.confidence, 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name, 
                        d.timestamp,
                        d.filename,
                        s.german_name
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info s ON d.scientific_name = s.scientific_name
                    ORDER BY d.timestamp DESC 
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                
                detections = []
                use_german = SettingsService.is_german_names_enabled()
                
                for row in result:
                    d = dict(row._mapping) # SQLAlchemy Row to dict
                    ts = d.get('timestamp')
                    if ts:
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        d['iso_timestamp'] = ts.isoformat()
                        # Legacy support or direct use? We'll use ISO in frontend.
                        d['time'] = ts.isoformat() # Temporary overload for template compatibility check
                    else:
                        d['iso_timestamp'] = ""
                        d['time'] = "-"
                        
                    # Display Name Logic
                    d['display_name'] = d.get('german_name') if use_german and d.get('german_name') else d.get('com_name')
                    
                    detections.append(d)
                    
                return detections
        except Exception as e:
            print(f"DB Error (get_recent_detections): {e}")
            return []

    @staticmethod
    def get_detection(filename: str):
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        d.filepath, 
                        d.start_time, 
                        d.end_time, 
                        d.confidence, 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name, 
                        d.timestamp,
                        d.filename,
                        s.image_url,
                        s.description,
                        s.german_name,
                        s.wikipedia_url
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info s ON d.scientific_name = s.scientific_name
                    WHERE d.filename = :filename
                """)
                row = conn.execute(query, {"filename": filename}).fetchone()
                
                if not row:
                    return None
                    
                d = dict(row._mapping)
                if d.get('timestamp'):
                    if d['timestamp'].tzinfo is None:
                        d['timestamp'] = d['timestamp'].replace(tzinfo=timezone.utc)
                    d['iso_timestamp'] = d['timestamp'].isoformat()
                    d['formatted_time'] = d['timestamp'].strftime("%d.%m.%Y %H:%M:%S")
                else:
                    d['iso_timestamp'] = ""
                    d['formatted_time'] = "-"
                    
                d['confidence_percent'] = round(d['confidence'] * 100)
                
                # Display Name Logic
                use_german = SettingsService.is_german_names_enabled()
                d['display_name'] = d.get('german_name') if use_german and d.get('german_name') else d.get('com_name')
                
                return d
        except Exception as e:
            print(f"DB Error (get_detection): {e}")
            return None

    @staticmethod
    def get_stats():
        try:
            with db.get_connection() as conn:
                # Today
                today_start = datetime.datetime.utcnow().date()
                query_today = text("SELECT COUNT(*) FROM birdnet.detections WHERE timestamp >= :today")
                today_count = conn.execute(query_today, {"today": today_start}).scalar()
                
                # Total
                query_total = text("SELECT COUNT(*) FROM birdnet.detections")
                total_count = conn.execute(query_total).scalar()
                
                # Top Species
                query_top = text("""
                    SELECT common_name as com_name, COUNT(*) as count 
                    FROM birdnet.detections 
                    GROUP BY common_name 
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                result_top = conn.execute(query_top)
                top_species = [dict(row._mapping) for row in result_top]
                
                return {
                    "today": today_count,
                    "total": total_count,
                    "top_species": top_species
                }
        except:
            return {"today": 0, "total": 0, "top_species": []}

    @staticmethod
    async def get_all_species():
        """Returns all species with their counts and last seen date. Enriches with images if missing."""
        import asyncio
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name,
                        COUNT(*) as count,
                        MAX(d.timestamp) as last_seen,
                        MIN(d.timestamp) as first_seen,
                        AVG(d.confidence) as avg_conf,
                        si.image_url,
                        si.german_name
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info si ON d.scientific_name = si.scientific_name
                    GROUP BY d.common_name, d.scientific_name, si.image_url, si.german_name
                    ORDER BY count DESC
                """)
                result = conn.execute(query)
                species = []
                
                # List of species that need enrichment
                to_enrich = []
                
                for row in result:
                    d = dict(row._mapping)
                    # Format dates
                    if d.get('last_seen'):
                        if d['last_seen'].tzinfo is None:
                             d['last_seen'] = d['last_seen'].replace(tzinfo=timezone.utc)
                        d['last_seen_iso'] = d['last_seen'].isoformat()
                    else:
                        d['last_seen_iso'] = ""
                    
                    if d.get('first_seen'):
                        if d['first_seen'].tzinfo is None:
                             d['first_seen'] = d['first_seen'].replace(tzinfo=timezone.utc)
                        d['first_seen_iso'] = d['first_seen'].isoformat()
                    else:
                        d['first_seen_iso'] = ""
                        
                    if d.get('avg_conf'):
                        d['avg_conf'] = float(d['avg_conf'])
                    else:
                        d['avg_conf'] = 0.0
                    
                    species.append(d)
                    
                    # Check if enrichment is needed (no image)
                    if not d.get('image_url'):
                        to_enrich.append(d)
                
                # Enrich in background (parallel)
                if to_enrich:
                    # We limit concurrency to avoid hitting API limits if many are missing
                    # But for now, simple gather is a start.
                    await asyncio.gather(*[BirdNetService.enrich_species_data(sp) for sp in to_enrich])
                    
                # Display Name Logic (Post-process after enrichment)
                use_german = SettingsService.is_german_names_enabled()
                for sp in species:
                    sp['display_name'] = sp.get('german_name') if use_german and sp.get('german_name') else sp.get('com_name')
                    
                return species
        except Exception as e:
            print(f"Error get_all_species: {e}")
            return []

    @staticmethod
    def get_species_stats(species_name: str):
        """Get detailed stats for a specific species."""
        try:
            with db.get_connection() as conn:
                # Basic Info & Aggregate stats
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
                res_info = conn.execute(query_info, {"name": species_name}).fetchone()
                if not res_info:
                    return None
                    
                info = dict(res_info._mapping)
                # Convert info datetimes to ISO
                if info.get('first_seen'):
                    if info['first_seen'].tzinfo is None: info['first_seen'] = info['first_seen'].replace(tzinfo=timezone.utc)
                    info['first_seen_iso'] = info['first_seen'].isoformat()
                if info.get('last_seen'):
                    if info['last_seen'].tzinfo is None: info['last_seen'] = info['last_seen'].replace(tzinfo=timezone.utc)
                    info['last_seen_iso'] = info['last_seen'].isoformat()

                # Recent Detections
                query_recent = text("""
                    SELECT * FROM birdnet.detections 
                    WHERE common_name = :name 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """)
                res_recent = conn.execute(query_recent, {"name": species_name})
                recent = []
                for row in res_recent:
                    d = dict(row._mapping)
                    if d.get('timestamp'):
                         if d['timestamp'].tzinfo is None: d['timestamp'] = d['timestamp'].replace(tzinfo=timezone.utc)
                         d['iso_timestamp'] = d['timestamp'].isoformat()
                    else:
                         d['iso_timestamp'] = ""
                    recent.append(d)
                
                # Fetch German name if needed (it wasn't in the group query clearly)
                # Actually, stats for species are filtered by common_name. 
                # If we want to display German name as header, we need to fetch it.
                # It might be in 'species_info' table.
                
                # Use enriched info if available
                # info is already fetched. But check if it has german_name.
                # The first query aggregated detections, didn't join species_info. 
                
                # Let's trust enrich_species_data called later in controller will fix 'info'
                # or ensure 'info' has it by joining above?
                # The first query didn't join. Let's rely on enrichment in controller or add logic here.
                # Controller calls enrich_species_data(data["info"]).
                
                # So we just return raw info here. Controller handles display.
                
                # Hourly Distribution
                
                # Hourly Distribution
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE common_name = :name
                    GROUP BY hour
                    ORDER BY hour
                """)
                res_hourly = conn.execute(query_hourly, {"name": species_name})
                hourly_dist = {int(r.hour): r.count for r in res_hourly}
                # Fill missing hours
                hourly_data = [hourly_dist.get(h, 0) for h in range(24)]
                
                return {
                    "info": info,
                    "recent": recent,
                    "hourly": hourly_data
                }
        except Exception as e:
            print(f"Error get_species_stats: {e}")
            return None

    @staticmethod
    async def enrich_species_data(info: dict):
        """Enrich species info with Wikimedia data, using cache."""
        if not info or not info.get('sci_name'):
            return info
            
        sci_name = info['sci_name']
        
        try:
             with db.get_connection() as conn:
                # 1. Check Cache
                query_cache = text("SELECT * FROM birdnet.species_info WHERE scientific_name = :sci_name")
                cache = conn.execute(query_cache, {"sci_name": sci_name}).fetchone()
                
                wiki_data = None
                if cache:
                    wiki_data = dict(cache._mapping)
                    # Check age (optional, e.g. update every 30 days)
                    
                # 2. Fetch if missing
                if not wiki_data:
                    from src.wikimedia import WikimediaService
                    print(f"Fetching Wikimedia data for {sci_name}...")
                    wiki_data = await WikimediaService.fetch_species_data(sci_name)
                    
                    if wiki_data:
                        # 3. Cache Result
                        # We use UPSERT (INSERT ... ON CONFLICT)
                        query_upsert = text("""
                            INSERT INTO birdnet.species_info (
                                scientific_name, common_name, german_name, family, 
                                image_url, description, wikipedia_url, last_updated
                            ) VALUES (
                                :scientific_name, :common_name, :german_name, :family,
                                :image_url, :description, :wikipedia_url, NOW()
                            )
                            ON CONFLICT (scientific_name) DO UPDATE SET
                                german_name = EXCLUDED.german_name,
                                image_url = EXCLUDED.image_url,
                                description = EXCLUDED.description,
                                wikipedia_url = EXCLUDED.wikipedia_url,
                                last_updated = NOW()
                        """)
                        # Fill gaps
                        wiki_data['common_name'] = info.get('com_name')
                        wiki_data['family'] = "" # ToDo
                        
                        conn.execute(query_upsert, wiki_data)
                        conn.commit()
                        
                # 4. Merge
                if wiki_data:
                    info['german_name'] = wiki_data.get('german_name')
                    info['image_url'] = wiki_data.get('image_url')
                    info['description'] = wiki_data.get('description')
                    info['wikipedia_url'] = wiki_data.get('wikipedia_url')
                    
        except Exception as e:
            print(f"Enrichment error for {sci_name}: {e}")

        return info

    @staticmethod
    def toggle_watchlist(sci_name: str, com_name: str, enabled: bool) -> bool:
        """Toggle watchlist status for a species."""
        try:
            with db.get_connection() as conn:
                # Upsert logic (Postgres specific) or check/update
                # Check if exists
                check = text("SELECT id FROM birdnet.watchlist WHERE scientific_name = :sci")
                res = conn.execute(check, {"sci": sci_name}).fetchone()
                
                if res:
                    # Update
                    upd = text("UPDATE birdnet.watchlist SET enabled = :en, common_name = :com WHERE scientific_name = :sci")
                    conn.execute(upd, {"en": 1 if enabled else 0, "com": com_name, "sci": sci_name})
                else:
                    # Insert
                    ins = text("INSERT INTO birdnet.watchlist (scientific_name, common_name, enabled) VALUES (:sci, :com, :en)")
                    conn.execute(ins, {"sci": sci_name, "com": com_name, "en": 1 if enabled else 0})
                    
                conn.commit()
                return True
        except Exception as e:
            print(f"Watchlist toggle error: {e}")
            return False

    @staticmethod
    def get_watchlist_status(sci_names: list) -> dict:
        """Get watchlist status for a list of scientific names. Returns dict {sci_name: bool}"""
        try:
            if not sci_names: return {}
            with db.get_connection() as conn:
                query = text("SELECT scientific_name FROM birdnet.watchlist WHERE enabled = 1 AND scientific_name IN :names")
                # SQL Alchemy IN clause handling with text? 
                # Better: SELECT scientific_name FROM birdnet.watchlist WHERE enabled = 1
                # And filter in python if list is small, or bind parameters dynamically.
                # For safety/simplicity let's fetch all enabled (watchlist is usually small).
                
                query_all = text("SELECT scientific_name FROM birdnet.watchlist WHERE enabled = 1")
                res = conn.execute(query_all)
                watched = {row.scientific_name for row in res}
                
                return {name: (name in watched) for name in sci_names}
        except Exception as e:
            print(f"Watchlist status error: {e}")
            return {}

    @staticmethod
    def get_advanced_stats():
        """Get comprehensive stats for the BirdStats dashboard."""
        try:
            with db.get_connection() as conn:
                # 1. Daily Trend (Last 30 Days) - Keep existing
                query_daily = text("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE timestamp >= NOW() - INTERVAL '30 DAYS'
                    GROUP BY date
                    ORDER BY date ASC
                """)
                res_daily = conn.execute(query_daily)
                daily = {"labels": [], "values": []}
                for row in res_daily:
                    daily["labels"].append(row.date.strftime("%Y-%m-%d"))
                    daily["values"].append(row.count)

                # 2. Hourly Distribution (All Time) - Keep existing
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    GROUP BY hour
                """)
                res_hourly = conn.execute(query_hourly)
                dist_map = {int(r.hour): r.count for r in res_hourly}
                hourly = {"values": [dist_map.get(h, 0) for h in range(24)]}
                
                # 3. Top Species Distributions (Pie Charts)
                # Helper for top species
                def get_top_species(interval_clause, limit=20):
                    where_sql = ""
                    params = {}
                    if interval_clause:
                        where_sql = f"WHERE timestamp >= NOW() - INTERVAL '{interval_clause}'"
                    
                    query = text(f"""
                        SELECT common_name, COUNT(*) as count 
                        FROM birdnet.detections 
                        {where_sql}
                        GROUP BY common_name 
                        ORDER BY count DESC 
                        LIMIT :limit
                    """)
                    rows = conn.execute(query, {"limit": limit})
                    return {
                        "labels": [r.common_name for r in rows], 
                        "values": [r.count for r in rows]
                    }

                dist_today = get_top_species("1 DAY") # Actually strictly today? User said "Today". 1 DAY interval is last 24h. 
                                                     # Usually "Today" means since 00:00. 
                                                     # Let's use DATE(timestamp) = CURRENT_DATE for Today.
                
                # Correcting for "Today" (Calendar Day)
                query_today_exact = text("""
                    SELECT common_name, COUNT(*) as count 
                    FROM birdnet.detections 
                    WHERE DATE(timestamp) = CURRENT_DATE
                    GROUP BY common_name 
                    ORDER BY count DESC 
                    LIMIT 20
                """)
                rows_today = conn.execute(query_today_exact)
                dist_today = {"labels": [r.common_name for r in rows_today], "values": [r.count for r in rows_today]}

                dist_week = get_top_species("7 DAYS")
                dist_month = get_top_species("30 DAYS")
                dist_year = get_top_species("1 YEAR")

                # 4. Histogram (All Species Ranked)
                # We fetch all species and their counts
                query_all = text("""
                    SELECT common_name, COUNT(*) as count
                    FROM birdnet.detections
                    GROUP BY common_name
                    ORDER BY count DESC
                """)
                res_all = conn.execute(query_all)
                hist_labels = []
                hist_values = []
                rarest_list = []
                
                all_rows = [dict(row._mapping) for row in res_all]
                
                # Populate Histogram (Top 100 to avoid overload?) User said 'Histogram over all species'. 
                # If there are 500 species, chart.js handles it ok-ish. 
                for d in all_rows:
                    hist_labels.append(d['common_name'])
                    hist_values.append(d['count'])
                
                # 5. Rarest Species (List)
                # Since we have the list sorted DESC, the rarest are at the end.
                # But user might want them sorted ASC for the list view.
                # Let's just slice the last 20 from all_rows and reverse.
                if len(all_rows) > 0:
                    rarest_slice = all_rows[-20:] # Get last 20
                    # Sort them ASC by count (they are already somewhat sorted, but let's be sure if ties exist)
                    rarest_list = sorted(rarest_slice, key=lambda x: x['count'])
                else:
                    rarest_list = []

                return {
                    "daily": daily,
                    "hourly": hourly,
                    "distributions": {
                        "today": dist_today,
                        "week": dist_week,
                        "month": dist_month,
                        "year": dist_year
                    },
                    "histogram": {
                        "labels": hist_labels,
                        "values": hist_values
                    },
                    "rarest": rarest_list
                }
        except Exception as e:
            print(f"Error get_advanced_stats: {e}")
            empty_chart = {"labels": [], "values": []}
            return {
                "daily": empty_chart, 
                "hourly": {"values": []}, 
                "distributions": {
                    "today": empty_chart, "week": empty_chart, 
                    "month": empty_chart, "year": empty_chart
                },
                "histogram": empty_chart,
                "rarest": []
            }

STATUS_DIR = "/mnt/data/services/silvasonic/status"

class CarrierService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(STATUS_DIR, "carrier.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
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

class RecorderService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(STATUS_DIR, "recorder.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
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
    def get_recent_recordings(limit=20):
        try:
             with db.get_connection() as conn:
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
                result = conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('created_at'):
                        if d['created_at'].tzinfo is None:
                             d['created_at'] = d['created_at'].replace(tzinfo=timezone.utc)
                        d['created_at_iso'] = d['created_at'].isoformat()
                        d['formatted_time'] = d['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        d['created_at_iso'] = ""
                        d['formatted_time'] = "Unknown"
                        
                    # Calculate Size in MB
                    d['size_mb'] = round((d.get('file_size_bytes') or 0) / (1024*1024), 2)
                    d['duration_str'] = f"{d.get('duration_sec', 0):.1f}s"
                    
                    items.append(d)
                return items
        except Exception as e:
            print(f"Recorder History Error: {e}")
            return []

class HealthCheckerService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(STATUS_DIR, "healthchecker.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                     # Check freshness
                     data = json.load(f)
                     
                     # Check if stale (> 2 mins)
                     if time.time() - data.get("timestamp", 0) > 120:
                         data["status"] = "Stalled"
                     
                     return data
        except Exception as e:
            print(f"HealthChecker status error: {e}")
            
        return {"status": "Unknown"}

    @staticmethod
    def get_system_metrics():
        """Reads the consolidated system status generated by HealthChecker."""
        try:
            status_file = os.path.join(STATUS_DIR, "system_status.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                     return json.load(f)
        except Exception as e:
            print(f"System metrics error: {e}")
            
        return {}

class AnalyzerService:
    @staticmethod
    def get_recent_analysis(limit=20):
        try:
            with db.get_connection() as conn:
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
                result = conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('created_at'):
                        if d['created_at'].tzinfo is None:
                            d['created_at'] = d['created_at'].replace(tzinfo=timezone.utc)
                        d['created_at_iso'] = d['created_at'].isoformat()
                    else:
                        d['created_at_iso'] = ""
                        
                    # Fix spec path
                    if d.get('spec_path'):
                         fname = os.path.basename(d['spec_path'])
                         d['spec_url'] = f"/api/spectrogram/{fname}"
                    else:
                         d['spec_url'] = None
                         
                    # Format size
                    if d.get('file_size_bytes'):
                        d['size_mb'] = round(d['file_size_bytes'] / (1024*1024), 2)
                    else:
                        d['size_mb'] = 0
                    
                    # Round metrics
                    if d.get('rms_loudness'): d['rms_loudness'] = round(d['rms_loudness'], 1)
                    if d.get('peak_frequency_hz'): d['peak_frequency_hz'] = int(d['peak_frequency_hz'])
                        
                    items.append(d)
                return items
        except Exception as e:
            print(f"Analyzer Error: {e}")
            return []

    @staticmethod
    def get_stats():
         try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        COUNT(*) as total_files,
                        COALESCE(SUM(duration_sec), 0) as total_duration,
                        AVG(duration_sec) as avg_duration,
                        AVG(file_size_bytes) as avg_size
                    FROM brain.audio_files
                """)
                res = conn.execute(query).fetchone()
                if res:
                    d = dict(res._mapping)
                    d['total_duration_hours'] = round(d['total_duration'] / 3600, 2)
                    d['avg_size_mb'] = round((d['avg_size'] or 0) / (1024*1024), 2)
                    d['avg_duration'] = round(d.get('avg_duration') or 0, 1)
                    return d
                return {}
         except Exception as e:
             print(f"Analyzer Stats Error: {e}")
             return {}
class WeatherService:
    @staticmethod
    def get_current_weather():
        """Get the latest weather measurement."""
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT * FROM weather.measurements 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                row = conn.execute(query).fetchone()
                if row:
                    d = dict(row._mapping)
                    if d.get('timestamp') and d['timestamp'].tzinfo is None:
                        d['timestamp'] = d['timestamp'].replace(tzinfo=timezone.utc)
                    return d
        except Exception as e:
            print(f"Weather DB Error: {e}")
        return None

    @staticmethod
    def get_history(hours=24):
        """Get weather history for charts."""
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT * FROM weather.measurements 
                    WHERE timestamp >= NOW() - INTERVAL ':hours HOURS'
                    ORDER BY timestamp ASC
                """)
                # Bind param properly or safe f-string for int
                query = text(f"SELECT * FROM weather.measurements WHERE timestamp >= NOW() - INTERVAL '{int(hours)} HOURS' ORDER BY timestamp ASC")
                
                result = conn.execute(query)
                data = {
                    "labels": [],
                    "temp": [],
                    "humidity": [],
                    "rain": [],
                    "wind": []
                }
                
                for row in result:
                    d = dict(row._mapping)
                    ts = d['timestamp']
                    if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                    
                    data["labels"].append(ts.strftime("%H:%M"))
                    data["temp"].append(d.get("temperature_c"))
                    data["humidity"].append(d.get("humidity_percent"))
                    data["rain"].append(d.get("precipitation_mm"))
                    data["wind"].append(d.get("wind_speed_ms"))
                    
                return data
        except Exception as e:
            print(f"Weather History Error: {e}")
            return {"labels": [], "temp": [], "humidity": [], "rain": [], "wind": []}

    @staticmethod
    def get_status():
        """Get service status from JSON file."""
        try:
            status_file = os.path.join(STATUS_DIR, "weather.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
                    # Check staleness (20 mins schedule, so maybe 25 min stale check)
                    if time.time() - data.get("timestamp", 0) > 1500:
                        data["status"] = "Stalen"
                    return data
        except:
             pass
        return {"status": "Unknown"}
