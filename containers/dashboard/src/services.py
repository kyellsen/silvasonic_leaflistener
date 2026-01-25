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
                        common_name as com_name, 
                        scientific_name as sci_name,
                        COUNT(*) as count,
                        MAX(timestamp) as last_seen,
                        MIN(timestamp) as first_seen,
                        AVG(confidence) as avg_conf
                    FROM birdnet.detections
                    GROUP BY common_name, scientific_name
                    ORDER BY count DESC
                """)
                result = conn.execute(query)
                species = []
                for row in result:
                    d = dict(row._mapping)
                    # Format dates
                    if d.get('last_seen'):
                        d['last_seen_str'] = d['last_seen'].strftime("%Y-%m-%d %H:%M")
                    else:
                        d['last_seen_str'] = "-"
                    
                    if d.get('first_seen'):
                        d['first_seen_str'] = d['first_seen'].strftime("%Y-%m-%d")
                    else:
                        d['first_seen_str'] = "-"
                        
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
                    d['time_str'] = d['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if d.get('timestamp') else "-"
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
