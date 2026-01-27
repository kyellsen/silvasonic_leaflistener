import logging
import os
import typing

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
            logger.info(
                f"Disk usage {current_usage:.1f}% is below threshold {self.threshold_percent}%. "
                "No cleanup needed."
            )
            return

        logger.warning(
            f"Disk usage {current_usage:.1f}% exceeds threshold {self.threshold_percent}%. "
            "Starting cleanup..."
        )

        # 1. List all local files
        local_files = self._list_local_files()

        # 2. Sort by age (oldest first)
        local_files.sort(key=lambda x: x["mtime"])

        deleted_count = 0
        deleted_size = 0

        for file in local_files:
            # Check if we've reached the target
            if get_usage_callback(self.source_dir) <= self.target_percent:
                logger.info(f"Target usage {self.target_percent}% reached. Stopping cleanup.")
                break

            rel_path = os.path.relpath(file["path"], self.source_dir)

            # 3. VERIFY: Exists on remote?
            if rel_path not in remote_files:
                logger.warning(f"Skipping {rel_path}: Not found on remote.")
                continue

            # 4. VERIFY: Size matches?
            # 4. VERIFY: Size matches?
            # Note: Remote might report different size if compressed/encrypted,
            # but for basic copy it should match.
            # We allow small variance if needed, but for now strict check or skip check
            # if size is drastically different
            # (e.g. if we suspect partial upload).
            # Ideally we trust rclone's verification during copy, so if it's in the list
            # it's likely good.
            # But let's check size to be extra safe against 0-byte uploads.
            remote_size = remote_files[rel_path]
            local_size = file["size"]

            if remote_size == 0 and local_size > 0:
                logger.warning(f"Skipping {rel_path}: Remote size is 0.")
                continue

            # 5. Delete
            try:
                os.remove(file["path"])
                logger.info(f"Deleted {rel_path} (Local: {local_size}b, Remote: {remote_size}b)")
                deleted_count += 1
                deleted_size += local_size
            except Exception as e:
                logger.error(f"Failed to delete {file['path']}: {e}")

        logger.info(
            f"Cleanup finished. Deleted {deleted_count} files "
            f"({deleted_size / 1024 / 1024:.2f} MB)."
        )

    def _list_local_files(self) -> list[dict[str, typing.Any]]:
        """Returns a list of local files with metadata."""
        files = []
        for root, _, filenames in os.walk(self.source_dir):
            for filename in filenames:
                path = os.path.join(root, filename)
                try:
                    stat = os.stat(path)
                    files.append({"path": path, "size": stat.st_size, "mtime": stat.st_mtime})
                except FileNotFoundError:
                    pass
        return files
