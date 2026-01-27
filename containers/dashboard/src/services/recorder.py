import datetime
import json
import os
import time
from datetime import UTC
from typing import Any

from .common import REC_DIR, STATUS_DIR, logger


class RecorderService:
    @staticmethod
    def get_audio_settings(profile: dict[str, Any] | None) -> float:
        """Extract audio BPS (Bytes per Second) from profile."""
        try:
            if isinstance(profile, dict) and "audio" in profile:
                audio = profile["audio"]
                sr = int(audio.get("sample_rate", 48000))
                ch = int(audio.get("channels", 1))
                depth = int(audio.get("bit_depth", 16))

                # Bytes per second (Uncompressed)
                return sr * ch * (depth / 8)
        except Exception:
            pass
        return 48000 * 1 * 2  # Default to 48kHz, Mono, 16-bit (96000 Bps)

    @staticmethod
    def get_status() -> list[dict[str, Any]]:
        """Returns a list of status dicts for all detected recorders."""
        statuses = []
        try:
            import glob
            # Find all recorder status files
            files = glob.glob(os.path.join(STATUS_DIR, "recorder_*.json"))
            # Also check legacy/default "recorder.json" if exists and not covered? 
            # If we migrated, we shouldn't have it, but for safety check explicit file too if not in glob
            if os.path.exists(os.path.join(STATUS_DIR, "recorder.json")):
                 files.append(os.path.join(STATUS_DIR, "recorder.json"))

            # Dedup files
            files = list(set(files))

            if not files:
                 return [{
                    "status": "Unknown",
                    "profile": "No Recorders Found",
                    "device": "Unknown",
                    "storage_forecast": {"daily_str": "?", "remaining_str": "?"},
                }]

            for status_file in files:
                try:
                    with open(status_file) as f:
                        data: dict[str, Any] = json.load(f)

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
                        forecast = {
                            "daily_gb": 0,
                            "daily_str": "Unknown",
                            "remaining_days": 0,
                            "remaining_str": "Unknown",
                        }

                        if isinstance(profile, dict) and "audio" in profile:
                            try:
                                bps = RecorderService.get_audio_settings(profile)
                                compression = 0.6
                                bytes_per_day = bps * 60 * 60 * 24 * compression
                                gb_per_day = bytes_per_day / (1024**3)

                                forecast["daily_gb"] = round(gb_per_day, 1)
                                forecast["daily_str"] = f"~{gb_per_day:.1f} GB"

                                # Calculate Remaining using shutil on the recording path
                                import shutil
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
                        statuses.append(data)
                except Exception as e:
                    logger.error(f"Error reading {status_file}: {e}")
            
            # Sort by profile name or slug for stability
            statuses.sort(key=lambda x: x.get("profile", {}).get("name", ""))
            return statuses

        except Exception as e:
            logger.error(f"Recorder status error: {e}")

        return [{
            "status": "Unknown",
            "profile": "Error",
            "device": "Unknown",
            "storage_forecast": {"daily_str": "?", "remaining_str": "?"},
        }]

    @staticmethod
    async def get_recent_recordings(limit: int = 20) -> list[dict[str, Any]]:
        try:
            # Get current BPS setting for Duration Fallback
            # Get first active profile for defaults?
            # Or assume standard?
            # We can try to get from get_status()[0] if exists
            statuses = RecorderService.get_status()
            current_bps = 48000 * 2 # Default
            if statuses and "profile" in statuses[0]:
                 current_bps = RecorderService.get_audio_settings(statuses[0]["profile"])

            if not os.path.exists(REC_DIR):
                return []

            files_found: list[dict[str, Any]] = []
            # Recursive scan to find all audio files (support subdirs like YYYY-MM-DD or profile)
            for root, _dirs, files in os.walk(REC_DIR):
                for f in files:
                    if f.endswith((".flac", ".wav", ".mp3")):
                        full_path = os.path.join(root, f)
                        try:
                            stats = os.stat(full_path)
                            files_found.append(
                                {
                                    "path": full_path,
                                    "name": f,
                                    "size": stats.st_size,
                                    "mtime": stats.st_mtime,
                                }
                            )
                        except Exception:
                            pass

            # Sort by mtime DESC (newest first)
            files_found.sort(key=lambda x: x["mtime"], reverse=True)
            files_found = files_found[:limit]

            items = []
            for item in files_found:
                dt = datetime.datetime.fromtimestamp(item["mtime"])
                size_bytes = item["size"]
                size_mb = round(size_bytes / (1024 * 1024), 2)

                # Sanitize Duration Estimate
                # Duration = CompressedSize / (BPS * 0.6)
                duration = 0.0
                if size_bytes > 0:
                    duration = size_bytes / (current_bps * 0.6)

                d = {
                    "filename": item["name"],
                    "file_size_bytes": size_bytes,
                    "size_mb": size_mb,
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "created_at_iso": dt.isoformat(),
                    "duration_str": f"{duration:.2f}s",
                    "duration_sec": duration,
                    # Relative path for potential playback API usage
                    "audio_relative_path": os.path.relpath(item["path"], REC_DIR),
                }
            
                # Derive source
                rel = d["audio_relative_path"]
                if "/" in rel:
                   d["source"] = rel.split("/")[0]
                else:
                   d["source"] = "Default"
                   
                items.append(d)

            return items

        except Exception as e:
            logger.error(f"Recorder History Error: {e}")
            return []

    @staticmethod
    def get_creation_rate(minutes: int = 60) -> float:
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

            for root, _dirs, files in os.walk(REC_DIR):
                for f in files:
                    if not f.endswith(".flac"):
                        continue

                    # Parse time from filename
                    # Pattern: YYYY-mm-dd_HH-MM-SS.flac
                    try:
                        # Extract timestamp string
                        ts_str = f.split(".")[0]
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

                        # folder_date = root.split("/")[-1]  # if folders are dates

                        # Try parsing name first
                        dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                        ts = dt.replace(tzinfo=UTC).timestamp()  # Assuming UTC filenames

                        if ts >= cutoff:
                            count += 1
                    except Exception:
                        # Fallback to mtime
                        try:
                            mtime = os.path.getmtime(os.path.join(root, f))
                            if mtime >= cutoff:
                                count += 1
                        except Exception:
                            pass

            # Return rate per minute
            return round(count / minutes, 2)

        except Exception as e:
            logger.error(f"Recorder Rate Error: {e}")
            return 0.0

    @staticmethod
    def get_latest_filename() -> str | None:
        """Get the filename of the most recent recording on disk."""
        try:
            if not os.path.exists(REC_DIR):
                return None
            # Find latest file. os.scandir is fast.
            # We assume YYYY-MM-DD naming sort works
            # Optimization: check only recent folders if deeply nested?
            # For now, recursive walk
            all_files = []
            for _root, _dirs, files in os.walk(REC_DIR):
                for f in files:
                    if f.endswith(".flac"):
                        all_files.append(f)

            if not all_files:
                return None
            return max(all_files)
        except Exception:
            return None

    @staticmethod
    def count_files_after(filename: str | None) -> int:
        """Count how many files on disk are lexicographically 'after' the given filename."""
        if not filename:
            # If no comparison file provided, count ALL files (queue is full)
            # But this might be huge if starting fresh.
            # If processed table is empty, lag is Everything.
            # We should probably count all.
            pass

        try:
            if not os.path.exists(REC_DIR):
                return 0
            count = 0
            for _root, _dirs, files in os.walk(REC_DIR):
                for f in files:
                    if f.endswith(".flac"):
                        if not filename or f > filename:
                            count += 1
            return count
        except Exception as e:
            logger.error(f"Recorder Count After Error: {e}")
            return 0
