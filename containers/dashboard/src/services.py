import os
import sqlite3
import psutil
import datetime
import shutil
from pathlib import Path

# Paths
DB_PATH = "/data/birdnet_db/birdnet.sqlite"
REC_DIR = "/data/recording"

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
            
        return {
            "cpu": cpu,
            "ram_percent": mem.percent,
            "disk_percent": round(disk_percent, 1),
            "uptime_str": str(uptime).split('.')[0],
            "last_recording": last_rec,
            "last_recording_ago": int(datetime.datetime.now().timestamp() - last_rec_ts) if last_rec_ts > 0 else -1
        }

class BirdNetService:
    @staticmethod
    def get_connection():
        # Read-only connection
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def get_recent_detections(limit=10):
        try:
            if not os.path.exists(DB_PATH): return []
            with BirdNetService.get_connection() as conn:
                cursor = conn.cursor()
                # Assuming table 'detections' based on BirdNET-Analyzer standard or Silvasonic schema
                # Silvasonic schema likely: date, time, sci_name, com_name, confidence, filename
                # Adjust query based on schema knowledge. 
                # If schema unknown, might need to inspect. Assuming standard columns.
                cursor.execute("""
                    SELECT * FROM detections 
                    ORDER BY date DESC, time DESC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"DB Error: {e}")
            return []

    @staticmethod
    def get_stats():
        try:
            if not os.path.exists(DB_PATH): return {}
            with BirdNetService.get_connection() as conn:
                cursor = conn.cursor()
                
                # Today
                today = datetime.date.today().isoformat()
                cursor.execute("SELECT COUNT(*) as count FROM detections WHERE date = ?", (today,))
                today_count = cursor.fetchone()['count']
                
                # Total
                cursor.execute("SELECT COUNT(*) as count FROM detections")
                total_count = cursor.fetchone()['count']
                
                # Top Species
                cursor.execute("""
                    SELECT com_name, COUNT(*) as count 
                    FROM detections 
                    GROUP BY com_name 
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                top_species = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "today": today_count,
                    "total": total_count,
                    "top_species": top_species
                }
        except:
            return {"today": 0, "total": 0, "top_species": []}
