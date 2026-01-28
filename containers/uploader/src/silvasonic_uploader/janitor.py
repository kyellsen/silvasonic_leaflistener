import logging
import os
import typing
from operator import itemgetter

logger = logging.getLogger("Janitor")


class StorageJanitor:
    """Manages local storage by deleting old files when space is low."""

    def __init__(self, source_dir: str, threshold_percent: int = 70, target_percent: int = 60):
        """Initialize the StorageJanitor.

        Args:
            source_dir: Directory to clean.
            threshold_percent: Disk usage percentage to trigger cleanup.
            target_percent: Target disk usage percentage after cleanup.
        """
        self.source_dir = source_dir
        self.threshold_percent = threshold_percent
        self.target_percent = target_percent

    def check_and_clean(
        self, remote_files: dict[str, int] | None, get_usage_callback: typing.Callable[[str], float]
    ) -> None:
        """Checks disk usage and deletes old files if threshold is exceeded.

        Args:
            remote_files: Dict of {relative_path: size} from the remote, or None if network failed.
            get_usage_callback: Function that returns current disk usage %.
        """
        if remote_files is None:
            logger.warning(
                "Remote file list is unknown (None). Aborting cleanup to prevent data loss."
            )
            return

        current_usage = get_usage_callback(self.source_dir)

        if current_usage < self.threshold_percent:
            # OPTIMIZATION: Early Exit. Don't scan directory if usage is fine.
            logger.info(
                f"Disk usage {current_usage:.1f}% is below threshold {self.threshold_percent}%. "
                "No cleanup needed."
            )
            return

        logger.warning(
            f"Disk usage {current_usage:.1f}% exceeds threshold {self.threshold_percent}%. "
            "Starting cleanup..."
        )

        # 1. Collect all local files efficiently
        # Store as tuples: (mtime, size, relative_path) to save memory and avoid relpath calls.
        # This list materialization is necessary for global sorting (oldest first).
        try:
            local_files = list(self._yield_local_files())
        except Exception as e:
            logger.error(f"Failed to scan local files: {e}")
            return

        # 2. Sort by age (oldest first)
        # itemgetter(0) is optimized C-level fetch
        local_files.sort(key=itemgetter(0))

        deleted_count = 0
        deleted_size = 0

        for _, size, rel_path in local_files:
            # Check if we've reached the target
            # Optimization: Check usage every N files or subtract deleted bytes from total?
            # Re-checking disk usage (syscall) is cheap enough (statvfs).
            if get_usage_callback(self.source_dir) <= self.target_percent:
                logger.info(f"Target usage {self.target_percent}% reached. Stopping cleanup.")
                break

            # 3. VERIFY: Exists on remote?
            if rel_path not in remote_files:
                # logger.debug(f"Skipping {rel_path}: Not found on remote.")
                continue

            # 4. VERIFY: Size matches?
            remote_size = remote_files[rel_path]
            local_size = size

            if remote_size == 0 and local_size > 0:
                logger.warning(f"Skipping {rel_path}: Remote size is 0.")
                continue

            # 5. Delete
            abs_path = os.path.join(self.source_dir, rel_path)
            try:
                os.remove(abs_path)
                logger.info(f"Deleted {rel_path} (Local: {local_size}b)")
                deleted_count += 1
                deleted_size += local_size
            except Exception as e:
                logger.error(f"Failed to delete {abs_path}: {e}")

        logger.info(
            f"Cleanup finished. Deleted {deleted_count} files "
            f"({deleted_size / 1024 / 1024:.2f} MB)."
        )

    def _yield_local_files(self) -> typing.Iterator[tuple[float, int, str]]:
        """Yields local files as (mtime, size, relative_path) tuples using os.scandir."""
        # Stack stores (absolute_path, relative_prefix)
        # Root: (source_dir, "")
        stack = [(self.source_dir, "")]

        while stack:
            current_abs, current_rel = stack.pop()
            if not os.path.exists(current_abs):
                continue

            try:
                with os.scandir(current_abs) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            # Push subdirectory
                            # New rel path is current_rel + entry.name
                            new_rel = os.path.join(current_rel, entry.name)
                            stack.append((entry.path, new_rel))
                        elif entry.is_file(follow_symlinks=False):
                            try:
                                stat = entry.stat()
                                # Yield relative path!
                                rel_path = os.path.join(current_rel, entry.name)
                                yield (stat.st_mtime, stat.st_size, rel_path)
                            except FileNotFoundError:
                                pass
            except OSError as e:
                logger.warning(f"Failed to scan directory {current_abs}: {e}")
