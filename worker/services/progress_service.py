"""
Progress service for writing job progress to Redis.
The API server reads from these same Redis keys.
"""
import json
import logging
import redis

from config import Config

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    """Get Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            Config.REDIS_URI,
            decode_responses=True,
            socket_connect_timeout=5
        )
        _redis_client.ping()
        logger.info("Redis connection established for progress service")
    return _redis_client


def set_progress(job_id, progress_data, ttl=86400):
    """
    Set progress data for a job.
    Writes to Redis hash `job:{job_id}:progress`.
    Also writes to legacy key `video:progress:{video_id}` for backward compat.
    """
    try:
        r = get_redis()
        key = f"job:{job_id}:progress"

        # Convert all values to strings for Redis hash
        str_data = {k: str(v) for k, v in progress_data.items()}
        r.hset(key, mapping=str_data)
        r.expire(key, ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to set progress for job {job_id}: {e}")
        return False


def set_video_progress(video_id, progress_data, ttl=86400):
    """
    Set progress using the legacy video:progress key format.
    This ensures backward compatibility with the API server's progress reading.
    """
    try:
        r = get_redis()
        key = f"video:progress:{video_id}"
        str_data = {k: str(v) for k, v in progress_data.items()}
        r.hset(key, mapping=str_data)
        r.expire(key, ttl)
        return True
    except Exception as e:
        logger.error(f"Failed to set video progress for {video_id}: {e}")
        return False


def delete_progress(job_id):
    """Delete progress data for a job."""
    try:
        r = get_redis()
        r.delete(f"job:{job_id}:progress")
        return True
    except Exception as e:
        logger.error(f"Failed to delete progress for job {job_id}: {e}")
        return False
