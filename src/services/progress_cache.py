
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Try to import Redis, fall back to local dict
try:
    import redis
    from src.config import Config
    
    # Try to connect to Redis
    try:
        redis_uri = getattr(Config, 'REDIS_URI', 'redis://localhost:6379/0')
        redis_client = redis.from_url(
            redis_uri,
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
    
    @staticmethod
    def set_progress(video_id: str, progress_data: Dict, ttl: int = 3600) -> bool:
        """
        Set progress data for a video.
        
        Args:
            video_id: Video or job ID
            progress_data: Progress information dict
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            if REDIS_AVAILABLE and redis_client:
                # Store in Redis with custom TTL
                key = f"video:progress:{video_id}"
                redis_client.hset(key, mapping=progress_data)
                redis_client.expire(key, ttl)
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
