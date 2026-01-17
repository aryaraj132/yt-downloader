"""Progress cache service - stores video processing progress in Redis or local dict.

This service provides a cache layer for storing real-time progress data that:
- Doesn't need persistence (temporary progress data)
- Needs fast read/write (polled frequently)
- Works across multiple servers (if using Redis)
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Try to import Redis, fall back to local dict
try:
    import redis
    from src.config import Config
    
    # Try to connect to Redis
    try:
        redis_client = redis.Redis(
            host=getattr(Config, 'REDIS_HOST', 'localhost'),
            port=getattr(Config, 'REDIS_PORT', 6379),
            db=getattr(Config, 'REDIS_DB', 0),
            decode_responses=True,
            socket_connect_timeout=2
        )
        # Test connection
        redis_client.ping()
        REDIS_AVAILABLE = True
        logger.info("Redis connection established for progress cache")
    except Exception as e:
        logger.warning(f"Redis not available, using local dict fallback: {e}")
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    logger.warning("redis package not installed, using local dict fallback")
    REDIS_AVAILABLE = False
    redis_client = None

# Local fallback dict
_local_progress_cache = {}


class ProgressCache:
    """Cache service for storing video processing progress."""
    
    @staticmethod
    def set_progress(video_id: str, progress_data: Dict) -> bool:
        """
        Store progress data for a video.
        
        Args:
            video_id: Video document ID
            progress_data: Dict containing progress info
                {
                    'download_progress': 0-100,
                    'encoding_progress': 0-100,
                    'current_phase': 'downloading|encoding|initializing',
                    'speed': '2.3x',
                    'eta': '03:24',
                    ...
                }
        
        Returns:
            bool: Success status
        """
        try:
            if REDIS_AVAILABLE and redis_client:
                # Store in Redis with 1 hour expiry
                key = f"video:progress:{video_id}"
                redis_client.hset(key, mapping=progress_data)
                redis_client.expire(key, 3600)  # 1 hour TTL
                return True
            else:
                # Store in local dict
                _local_progress_cache[video_id] = progress_data
                return True
        except Exception as e:
            logger.error(f"Failed to set progress for {video_id}: {e}")
            # Try local fallback
            try:
                _local_progress_cache[video_id] = progress_data
                return True
            except:
                return False
    
    @staticmethod
    def get_progress(video_id: str) -> Optional[Dict]:
        """
        Get progress data for a video.
        
        Args:
            video_id: Video document ID
            
        Returns:
            Dict with progress data or None if not found
        """
        try:
            if REDIS_AVAILABLE and redis_client:
                # Get from Redis
                key = f"video:progress:{video_id}"
                data = redis_client.hgetall(key)
                
                if data:
                    # Convert string values back to appropriate types
                    result = {}
                    for k, v in data.items():
                        # Try to convert to number if possible
                        try:
                            if '.' in v:
                                result[k] = float(v)
                            else:
                                result[k] = int(v)
                        except (ValueError, AttributeError):
                            result[k] = v
                    return result
                return None
            else:
                # Get from local dict
                return _local_progress_cache.get(video_id)
        except Exception as e:
            logger.error(f"Failed to get progress for {video_id}: {e}")
            # Try local fallback
            try:
                return _local_progress_cache.get(video_id)
            except:
                return None
    
    @staticmethod
    def delete_progress(video_id: str) -> bool:
        """
        Delete progress data for a video (e.g., when completed or failed).
        
        Args:
            video_id: Video document ID
            
        Returns:
            bool: Success status
        """
        try:
            if REDIS_AVAILABLE and redis_client:
                key = f"video:progress:{video_id}"
                redis_client.delete(key)
            
            # Also remove from local cache if exists
            _local_progress_cache.pop(video_id, None)
            return True
        except Exception as e:
            logger.error(f"Failed to delete progress for {video_id}: {e}")
            return False
    
    @staticmethod
    def update_field(video_id: str, field: str, value) -> bool:
        """
        Update a single field in progress data.
        
        Args:
            video_id: Video document ID
            field: Field name to update
            value: New value
            
        Returns:
            bool: Success status
        """
        try:
            if REDIS_AVAILABLE and redis_client:
                key = f"video:progress:{video_id}"
                redis_client.hset(key, field, value)
                redis_client.expire(key, 3600)  # Refresh TTL
                return True
            else:
                # Update in local dict
                if video_id not in _local_progress_cache:
                    _local_progress_cache[video_id] = {}
                _local_progress_cache[video_id][field] = value
                return True
        except Exception as e:
            logger.error(f"Failed to update field {field} for {video_id}: {e}")
            return False
