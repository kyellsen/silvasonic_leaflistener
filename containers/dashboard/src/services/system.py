import datetime
import os
import shutil
import typing
from pathlib import Path

import psutil

from .common import REC_DIR, logger


class SystemService:
    @staticmethod
    def get_stats() -> dict[str, typing.Any]:
        try:
            # CPU Cores
            cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
            # Average for backward compatibility/summary
            cpu = round(sum(cpu_cores) / len(cpu_cores), 1) if cpu_cores else 0
        except Exception as e:
            logger.error(f"Error getting CPU stats: {e}", exc_info=True)
            cpu = 0
            cpu_cores = []

        try:
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            # RAM in GB
            ram_used_gb = round(mem.used / (1024**3), 1)
            ram_total_gb = round(mem.total / (1024**3), 1)
        except Exception as e:
            logger.error(f"Error getting Memory stats: {e}", exc_info=True)

            class MockMem:
                percent = 0
                used = 0
                total = 16 * (1024**3)

            mem = MockMem()
            mem_percent = 0
            ram_used_gb = 0
            ram_total_gb = 16

        # Disk usage for /mnt/data (mapped to /data/recording usually or root)
        # using /data/recording as proxy for NVMe
        try:
            disk = shutil.disk_usage("/data/recording")
            disk_percent = (disk.used / disk.total) * 100
            disk_used_gb = round(disk.used / (1024**3), 0)
            disk_total_gb = round(disk.total / (1024**3), 0)
        except Exception as e:
            logger.error(f"Error getting Disk stats: {e}", exc_info=True)
            disk_percent = 0
            disk_used_gb = 0
            disk_total_gb = 0

        # Boot time
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime: datetime.timedelta | str = datetime.datetime.now() - boot_time
        except Exception as e:
            logger.error(f"Error getting Boot stats: {e}", exc_info=True)
            uptime = "Unknown"

        # Last Recording
        last_rec = "Unknown"
        last_rec_ts: float = 0.0

        try:
            files = sorted(Path(REC_DIR).glob("**/*.flac"), key=os.path.getmtime, reverse=True)
            if files:
                last_rec_ts = files[0].stat().st_mtime
                last_rec = datetime.datetime.fromtimestamp(last_rec_ts).strftime("%H:%M:%S")
        except Exception as e:
            logger.error(f"Error getting Last Recording: {e}", exc_info=True)
            pass

        # CPU Temperature
        cpu_temp = "N/A"
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temp_c = int(f.read().strip()) / 1000.0
                cpu_temp = f"{temp_c:.1f}°C"
        except Exception as e:
            logger.error(f"Error getting CPU Temp: {e}", exc_info=True)
            pass

        return {
            "cpu": cpu,
            "cpu_cores": cpu_cores,
            "cpu_temp": cpu_temp,
            "ram_percent": mem_percent,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "disk_percent": round(disk_percent, 1),
            "disk_used_gb": int(disk_used_gb),
            "disk_total_gb": int(disk_total_gb),
            "uptime_str": str(uptime).split(".")[0]
            if isinstance(uptime, datetime.timedelta)
            else str(uptime),
            "last_recording": last_rec,
            "last_recording_ago": int(datetime.datetime.now().timestamp() - last_rec_ts)
            if last_rec_ts > 0
            else -1,
        }
