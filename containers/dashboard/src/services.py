import os
import psutil
import datetime
from datetime import timezone
import shutil
from pathlib import Path
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        
        # Disk usage for /mnt/data (mapped to /data/recording usually or root)
        # using /data/recording as proxy for NVMe
        try:
            disk = shutil.disk_usage("/data/recording")
            disk_percent = (disk.used / disk.total) * 100
        except:
            disk_percent = 0

        # Boot time
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        
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
            "ram_percent": mem.percent,
            "disk_percent": round(disk_percent, 1),
            "uptime_str": str(uptime).split('.')[0],
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
                        filepath, 
                        start_time, 
                        end_time, 
                        confidence, 
                        common_name as com_name, 
                        scientific_name as sci_name, 
                        timestamp,
                        filename
                    FROM birdnet.detections 
                    ORDER BY timestamp DESC 
                    LIMIT :limit
                """)
                result = conn.execute(query, {"limit": limit})
                
                detections = []
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
                    detections.append(d)
                    
                return detections
        except Exception as e:
            print(f"DB Error (get_recent_detections): {e}")
            return []

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
    def get_all_species():
        """Returns all species with their counts and last seen date."""
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
                        
                    d['avg_conf'] = round(d.get('avg_conf', 0), 2)
                    species.append(d)
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
    def get_time_stats():
        """Get global temporal stats for charts."""
        try:
            with db.get_connection() as conn:
                # Detections per day (last 30 days)
                query_daily = text("""
                    SELECT DATE(timestamp) as date, COUNT(*) as count
                    FROM birdnet.detections
                    WHERE timestamp >= NOW() - INTERVAL '30 DAYS'
                    GROUP BY date
                    ORDER BY date ASC
                """)
                res_daily = conn.execute(query_daily)
                
                daily_labels = []
                daily_values = []
                for row in res_daily:
                    daily_labels.append(row.date.strftime("%Y-%m-%d"))
                    daily_values.append(row.count)

                # Detections by Hour of Day (All time)
                query_hourly = text("""
                    SELECT EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count
                    FROM birdnet.detections
                    GROUP BY hour
                    ORDER BY hour ASC
                """)
                res_hourly = conn.execute(query_hourly)
                dist_map = {int(r.hour): r.count for r in res_hourly}
                hourly_values = [dist_map.get(h, 0) for h in range(24)]
                
                # Top Species Composition
                query_top = text("""
                    SELECT common_name, COUNT(*) as count 
                    FROM birdnet.detections 
                    GROUP BY common_name 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                res_top = conn.execute(query_top)
                top_labels = []
                top_values = []
                for row in res_top:
                    top_labels.append(row.common_name)
                    top_values.append(row.count)
                
                return {
                    "daily": {"labels": daily_labels, "values": daily_values},
                    "hourly": {"values": hourly_values},
                    "top": {"labels": top_labels, "values": top_values}
                }
        except Exception as e:
            print(f"Error get_time_stats: {e}")
            return {"daily": {"labels": [], "values": []}, "hourly": {"values": []}, "top": {"labels": [], "values": []}}

class CarrierService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(LOG_DIR, "carrier_status.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convert last_upload ts to readable
                    if data.get("last_upload", 0) > 0:
                        data["last_upload_str"] = datetime.datetime.fromtimestamp(data["last_upload"]).strftime("%H:%M:%S")
                    else:
                        data["last_upload_str"] = "Never"
                        
                    return data
        except Exception as e:
            print(f"Carrier status error: {e}")
            
        return {"status": "Unknown", "last_upload_str": "Unknown", "queue_size": -1}

class RecorderService:
    @staticmethod
    def get_status():
        try:
            status_file = os.path.join(LOG_DIR, "recorder_status.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Recorder status error: {e}")
            
        return {"status": "Unknown", "profile": "Unknown", "device": "Unknown"}
