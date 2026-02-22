"""
Queue consumer — reads jobs from Redis lists using BLPOP (blocking pop).
Implements retry logic with exponential backoff.
"""
import json
import logging
import time
import traceback
import redis as redis_lib

from config import Config
from services import db_service, progress_service
from services.download_service import download_video_segment
from services.encoding_service import encode_video

logger = logging.getLogger(__name__)


class QueueConsumer:
    """
    Consumes jobs from a Redis list queue.
    Uses BLPOP for efficient blocking reads.
    """

    def __init__(self, queue_name, job_type, shutdown_event):
        self.queue_name = queue_name
        self.job_type = job_type  # 'download' or 'encode'
        self.shutdown_event = shutdown_event
        self.redis_client = None
        self.dead_letter_queue = f"{queue_name}:dead"

    def _get_redis(self):
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis_lib.from_url(
                Config.REDIS_URI,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self.redis_client

    def run(self):
        """Main consumer loop. Runs until shutdown_event is set."""
        logger.info(f"[Consumer:{self.job_type}] Starting on queue: {self.queue_name}")

        while not self.shutdown_event.is_set():
            try:
                r = self._get_redis()

                # BLPOP with timeout — blocks until a job is available or timeout
                result = r.blpop(self.queue_name, timeout=5)

                if result is None:
                    # Timeout, no job available — loop back
                    continue

                queue_name, raw_payload = result
                logger.info(f"[Consumer:{self.job_type}] Received job from {queue_name}")

                try:
                    job_data = json.loads(raw_payload)
                except json.JSONDecodeError as e:
                    logger.error(f"[Consumer:{self.job_type}] Invalid JSON payload: {e}")
                    continue

                self._process_job(job_data, raw_payload)

            except redis_lib.ConnectionError as e:
                logger.error(f"[Consumer:{self.job_type}] Redis connection error: {e}")
                self.redis_client = None  # Force reconnect
                time.sleep(5)  # Wait before retrying
            except Exception as e:
                logger.error(f"[Consumer:{self.job_type}] Unexpected error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(2)

        logger.info(f"[Consumer:{self.job_type}] Stopped")

    def _process_job(self, job_data, raw_payload):
        """Process a single job with retry logic."""
        job_id = job_data.get('job_id', 'unknown')
        video_id = job_data.get('video_id', 'unknown')
        retry_count = job_data.get('_retry_count', 0)

        logger.info(
            f"[Consumer:{self.job_type}] Processing job {job_id} "
            f"(video: {video_id}, retry: {retry_count}/{Config.MAX_RETRIES})"
        )

        try:
            if self.job_type == 'download':
                success, error = download_video_segment(job_data)
            elif self.job_type == 'encode':
                success, error = encode_video(job_data)
            else:
                logger.error(f"[Consumer:{self.job_type}] Unknown job type")
                return

            if success:
                logger.info(f"[Consumer:{self.job_type}] Job {job_id} completed successfully")
            else:
                logger.error(f"[Consumer:{self.job_type}] Job {job_id} failed: {error}")
                self._handle_failure(job_data, raw_payload, error, retry_count)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Consumer:{self.job_type}] Job {job_id} threw exception: {error_msg}")
            logger.error(traceback.format_exc())
            self._handle_failure(job_data, raw_payload, error_msg, retry_count)

    def _handle_failure(self, job_data, raw_payload, error, retry_count):
        """Handle job failure with retry or dead-letter queue."""
        job_id = job_data.get('job_id', 'unknown')
        video_id = job_data.get('video_id', 'unknown')

        if retry_count < Config.MAX_RETRIES:
            # Retry with exponential backoff
            delay = Config.RETRY_DELAY_SECONDS * (2 ** retry_count)
            logger.info(
                f"[Consumer:{self.job_type}] Retrying job {job_id} "
                f"in {delay}s (attempt {retry_count + 1}/{Config.MAX_RETRIES})"
            )

            # Update retry count
            job_data['_retry_count'] = retry_count + 1

            # Wait then re-queue
            time.sleep(delay)
            try:
                r = self._get_redis()
                r.rpush(self.queue_name, json.dumps(job_data))
            except Exception as e:
                logger.error(f"[Consumer:{self.job_type}] Failed to re-queue job {job_id}: {e}")
                self._mark_failed(video_id, job_id, error)
        else:
            logger.error(
                f"[Consumer:{self.job_type}] Job {job_id} failed after "
                f"{Config.MAX_RETRIES} retries. Moving to dead-letter queue."
            )
            # Move to dead-letter queue
            try:
                r = self._get_redis()
                r.rpush(self.dead_letter_queue, json.dumps({
                    **job_data,
                    '_error': error,
                    '_failed_at': time.time(),
                }))
            except:
                pass

            self._mark_failed(video_id, job_id, error)

    def _mark_failed(self, video_id, job_id, error):
        """Mark job as failed in DB and progress cache."""
        try:
            db_service.update_video_status(
                video_id, 'failed',
                error_message=error[:500] if error else 'Unknown error'
            )
        except:
            pass

        try:
            progress_service.set_progress(job_id, {
                'status': 'failed',
                'current_phase': 'failed',
                'error_message': error[:200] if error else 'Unknown error',
            })
            progress_service.set_video_progress(video_id, {
                'status': 'failed',
                'current_phase': 'failed',
                'error_message': error[:200] if error else 'Unknown error',
            })
        except:
            pass
