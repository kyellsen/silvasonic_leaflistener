import bisect
import datetime
import os
import threading
import time
from typing import ClassVar

from .common import REC_DIR, logger


class StatsManager:
    _instance: ClassVar["StatsManager | None"] = None
    _lock = threading.Lock()

    # Cache Data
    _filenames: list[str] = []  # Sorted list of all .flac filenames
    _timestamps: list[
        float
    ] = []  # Timestamps corresponding to filenames (if reliable) or just list of all timestamps for rate calc
    # actually getting timestamp from filename is fast.
    # Let's just store filenames. We can parse timestamp from them if they follow pattern.

    _last_update: float = 0
    _updating = False

    @classmethod
    def get_instance(cls) -> "StatsManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_background_task(self) -> None:
        """Starts the background thread logic."""
        t = threading.Thread(target=self._update_loop, daemon=True)
        t.start()
        logger.info("StatsManager background thread started.")

    def _update_loop(self) -> None:
        while True:
            try:
                self._refresh_cache()
            except Exception as e:
                logger.error(f"StatsManager refresh failed: {e}")

            # Sleep 60s? Or 10s?
            # If user wants "Real-time" lag, 5-10s is better.
            # But walking huge dir every 5s is heavy.
            # Maybe 30s is a good compromise.
            time.sleep(15)

    def _refresh_cache(self) -> None:
        if not os.path.exists(REC_DIR):
            return

        start = time.time()
        new_files = []

        # Fast walk
        for _root, _, files in os.walk(REC_DIR):
            for f in files:
                if f.endswith(".flac"):
                    new_files.append(f)

        new_files.sort()

        # Parsed timestamps for rate calculation
        # optimize: only parse if needed? No, pre-compute for speed.
        # But keeping 100k floats is cheap.
        new_timestamps = []

        for f in new_files:
            # Try parse YYYY-MM-DD_HH-MM-SS
            try:
                # Expected: 2024-01-01_12-00-00.flac
                # Slice first 19 chars
                if len(f) >= 19:
                    ts_str = f[:19]
                    # Manual parsing is faster than strptime?
                    # let's trust strptime for now, optimize if slow.
                    dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                    new_timestamps.append(dt.replace(tzinfo=datetime.UTC).timestamp())
            except ValueError:
                # If filename doesn't match, maybe use mtime?
                # Doing stat() on 100k files is SLOW. Avoid if possible.
                # Just skip or ignore for rate stats.
                pass

        # Swap safely
        self._filenames = new_files
        self._timestamps = sorted(new_timestamps)  # Sort timestamps too
        self._last_update = time.time()

        duration = time.time() - start
        if duration > 1.0:
            logger.warning(
                f"StatsManager: Cache rebuild took {duration:.2f}s for {len(new_files)} files."
            )

    def count_files_after(self, filename: str | None) -> int:
        """Counts how many files are lexicographically larger than filename."""
        if not self._filenames:
            return 0

        if not filename:
            # If None, return total? Or 0?
            # Logic in dashboard: if no cursor, lag is everything?
            return len(self._filenames)

        # Bisect to find position
        # bisect_right returns insertion point after existing entries
        # idx is existing count <= filename?
        idx = bisect.bisect_right(self._filenames, filename)
        return len(self._filenames) - idx

    def get_creation_rate(self, minutes: int = 60) -> float:
        """Files created per minute in last X minutes."""
        if not self._timestamps:
            return 0.0

        cutoff = time.time() - (minutes * 60)

        # bisect_left to find first timestamp >= cutoff
        idx = bisect.bisect_left(self._timestamps, cutoff)

        count = len(self._timestamps) - idx
        return round(count / minutes, 2)
