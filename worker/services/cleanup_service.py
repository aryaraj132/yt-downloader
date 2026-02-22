"""
Cleanup service — periodically deletes S3 files older than 24 hours.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

from config import Config
from services import storage_service

logger = logging.getLogger(__name__)


class CleanupService:
    """Runs periodic cleanup of old S3 files."""

    def run(self, shutdown_event):
        """Run cleanup loop until shutdown."""
        logger.info(f"[Cleanup] Starting (interval: {Config.CLEANUP_INTERVAL_HOURS}h, max age: {Config.S3_FILE_MAX_AGE_HOURS}h)")

        while not shutdown_event.is_set():
            try:
                self._cleanup_old_files()
            except Exception as e:
                logger.error(f"[Cleanup] Error during cleanup: {e}")

            # Wait for next interval (check shutdown every 60s)
            for _ in range(Config.CLEANUP_INTERVAL_HOURS * 60):
                if shutdown_event.is_set():
                    break
                time.sleep(60)

        logger.info("[Cleanup] Stopped")

    def _cleanup_old_files(self):
        """Delete S3 files older than the configured max age."""
        logger.info("[Cleanup] Running S3 cleanup...")

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=Config.S3_FILE_MAX_AGE_HOURS)
        objects = storage_service.list_objects(prefix=Config.S3_KEY_PREFIX)

        deleted_count = 0
        for obj in objects:
            last_modified = obj.get('LastModified')
            if last_modified and last_modified < cutoff_time:
                key = obj['Key']
                if storage_service.delete_file(key):
                    deleted_count += 1
                    logger.info(f"[Cleanup] Deleted old file: {key}")

        if deleted_count > 0:
            logger.info(f"[Cleanup] Deleted {deleted_count} old file(s) from S3")
        else:
            logger.debug("[Cleanup] No old files to clean up")

        # Also clean up local temp directory
        self._cleanup_temp_dir()

    def _cleanup_temp_dir(self):
        """Clean up old files in the local temp directory."""
        import os

        if not os.path.exists(Config.TEMP_DIR):
            return

        cutoff_time = time.time() - (Config.S3_FILE_MAX_AGE_HOURS * 3600)
        deleted_count = 0

        for filename in os.listdir(Config.TEMP_DIR):
            filepath = os.path.join(Config.TEMP_DIR, filename)
            if os.path.isfile(filepath):
                if os.path.getmtime(filepath) < cutoff_time:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"[Cleanup] Failed to delete temp file {filepath}: {e}")

        if deleted_count > 0:
            logger.info(f"[Cleanup] Deleted {deleted_count} old temp file(s)")
