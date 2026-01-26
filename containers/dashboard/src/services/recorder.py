import json
import os
import time
import datetime
from datetime import UTC

from sqlalchemy import text

from .common import REC_DIR, STATUS_DIR, logger
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
                    profile = meta.get("profile", {})
                    
                    # 1. Device Name Cleaning
                    raw_device = meta.get("device", "Unknown")
                    clean_device = raw_device
                    if isinstance(raw_device, str):
                        # Extract content between first [] if present
                        # Example: card 0: r0 [UltraMic384K_EVO 16bit r0], device 0...
                        import re
                        match = re.search(r"\[(.*?)\]", raw_device)
                        if match:
                            clean_device = match.group(1)
                    
                    data["profile"] = profile
                    data["device"] = clean_device
                    data["device_raw"] = raw_device

                    # 2. Storage Forecast
                    # Calculate daily usage based on profile
                    forecast = {
                        "daily_gb": 0,
                        "daily_str": "Unknown",
                        "remaining_days": 0,
                        "remaining_str": "Unknown"
                    }
                    
                    if isinstance(profile, dict) and "audio" in profile:
                        try:
                            audio = profile["audio"]
                            sr = int(audio.get("sample_rate", 48000))
                            ch = int(audio.get("channels", 1))
                            depth = int(audio.get("bit_depth", 16))
                            
                            # Bytes per second (Uncompressed)
                            bps = sr * ch * (depth / 8)
                            
                            # Compression Ratio (Estimate for FLAC)
                            # 384kHz recordings might compress differently, but 0.6 is a safe standard for FLAC
                            compression = 0.6 
                            
                            # Bytes per day
                            bytes_per_day = bps * 60 * 60 * 24 * compression
                            gb_per_day = bytes_per_day / (1024**3)
                            
                            forecast["daily_gb"] = round(gb_per_day, 1)
                            forecast["daily_str"] = f"~{gb_per_day:.1f} GB"
                            
                            # Calculate Remaining using shutil on the recording path
                            import shutil
                            # Check if REC_DIR exists, else use current
                            check_path = REC_DIR if os.path.exists(REC_DIR) else "/"
                            usage = shutil.disk_usage(check_path)
                            free_bytes = usage.free
                            
                            if bytes_per_day > 0:
                                days_remaining = free_bytes / bytes_per_day
                                forecast["remaining_days"] = int(days_remaining)
                                if days_remaining > 365:
                                    forecast["remaining_str"] = ">1y"
                                else:
                                    forecast["remaining_str"] = f"~{int(days_remaining)}d"
                            
                        except Exception as e:
                            logger.error(f"Forecast Error: {e}")
                    
                    data["storage_forecast"] = forecast

                    return data
        except Exception as e:
            logger.error(f"Recorder status error: {e}")

        return {
            "status": "Unknown", 
            "profile": "Unknown", 
            "device": "Unknown", 
            "storage_forecast": {"daily_str": "?", "remaining_str": "?"}
        }

    @staticmethod
    async def get_recent_recordings(limit=20):
        try:
            async with db.get_connection() as conn:
                # Try fetching from birdnet schema (new architecture)
                # Fallback to brain if needed, but for now we switch to birdnet.processed_files
                query = text("""
                    SELECT 
                        filename,
                        audio_duration_sec as duration_sec,
                        0 as file_size_bytes,
                        processed_at as created_at
                    FROM birdnet.processed_files
                    ORDER BY processed_at DESC
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
                        # Convert to string for JSON serialization in templates
                        d['created_at'] = d['created_at'].isoformat()
                    else:
                        d['created_at_iso'] = ""
                        d['formatted_time'] = "Unknown"

                    # Calculate Size in MB
                    # If DB returns 0 (birdnet schema doesn't store size), try to fetch from disk
                    size_bytes = d.get('file_size_bytes') or 0
                    fname = d.get('filename')
                    
                    if size_bytes == 0 and fname:
                        try:
                            # Try to find file in REC_DIR
                            # Note: This is an educated guess if file is in root of REC_DIR
                            # If structure is complex, we might miss it without a recursive search.
                            # But recursive search for every row is too slow.
                            p = os.path.join(REC_DIR, fname)
                            if os.path.exists(p):
                                size_bytes = os.path.getsize(p)
                        except Exception:
                            pass
                            
                    d['size_mb'] = round(size_bytes / (1024*1024), 2)
                    d['file_size_bytes'] = size_bytes
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
            logger.error(f"Recorder History Error: {e}")
            return []

    @staticmethod
    def get_creation_rate(minutes=60):
        """Calculate files created per minute over the last X minutes."""
        try:
            now = time.time()
            cutoff = now - (minutes * 60)
            count = 0
            
            if not os.path.exists(REC_DIR):
                return 0.0

            # Scan directory (non-recursive for now, assuming flat structure or dated folders?)
            # Recorder uses dated folders typically?
            # Actually pattern is "%Y-%m-%d_%H-%M-%S.flac" inside BASE_OUTPUT_DIR/profile_slug
            # But REC_DIR should point to the active profile dir?
            # Dashboard Config: AUDIO_DIR = "/data/recording"
            # We might need to scan subdirs if profile is used.
            # Let's assume recursion for robustness or check depth 1.
            
            for root, dirs, files in os.walk(REC_DIR):
                for f in files:
                    if not f.endswith('.flac'): continue
                    
                    # Parse time from filename
                    # Pattern: YYYY-mm-dd_HH-MM-SS.flac
                    try:
                        # Extract timestamp string
                        ts_str = f.split('.')[0]
                        # Manual parsing is faster than strptime
                        # 2023-10-27_10-00-00
                        # 0123456789012345678
                        # strict positions
                        # This works only if matches pattern exactly.
                        # Fallback: os.path.getmtime?
                        # getmtime is disk IO, parsing name is CPU.
                        # Let's use getmtime if we visit the file anyway?
                        # No, getmtime might be unreliable if copied. Name is truth.
                        
                        # Use datetime.strptime
                        # dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                        # ts = dt.timestamp()
                        
                        # Optimization: we only need to know if it's > cutoff
                        # If filename format matches, use it.
                        
                        # Let's rely on mtime for MVP simplicity as we are already walking stats?
                        # os.walk yields names. We have to stat for mtime.
                        # Parsing name avoids stat call (IO).
                        
                        folder_date = root.split('/')[-1] # if folders are dates
                        
                        # Try parsing name first
                        dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                        ts = dt.replace(tzinfo=datetime.timezone.utc).timestamp() # Assuming UTC filenames
                        
                        if ts >= cutoff:
                            count += 1
                    except:
                        # Fallback to mtime
                        try:
                            mtime = os.path.getmtime(os.path.join(root, f))
                            if mtime >= cutoff:
                                count += 1
                        except:
                            pass
                            
            # Return rate per minute
            return round(count / minutes, 2)
            
        except Exception as e:
            logger.error(f"Recorder Rate Error: {e}")
            return 0.0

    @staticmethod
    def get_latest_filename():
        """Get the filename of the most recent recording on disk."""
        try:
            if not os.path.exists(REC_DIR): return None
            # Find latest file. os.scandir is fast.
            latest = None
            # We assume YYYY-MM-DD naming sort works
            # Optimization: check only recent folders if deeply nested?
            # For now, recursive walk
            all_files = []
            for root, dirs, files in os.walk(REC_DIR):
                for f in files:
                    if f.endswith('.flac'):
                        all_files.append(f)
            
            if not all_files: return None
            return max(all_files)
        except Exception:
            return None

    @staticmethod
    def count_files_after(filename: str):
        """Count how many files on disk are lexicographically 'after' the given filename."""
        if not filename: 
            # If no comparison file provided, count ALL files (queue is full)
             # But this might be huge if starting fresh.
             # If processed table is empty, lag is Everything.
             # We should probably count all.
             pass
        
        try:
            if not os.path.exists(REC_DIR): return 0
            count = 0
            for root, dirs, files in os.walk(REC_DIR):
                for f in files:
                    if f.endswith('.flac'):
                        if not filename or f > filename:
                            count += 1
            return count
        except Exception as e:
            logger.error(f"Recorder Count After Error: {e}")
            return 0
