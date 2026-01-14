"""Redis cache service for session management."""
import json
import logging
from typing import Optional, Any
import redis
from redis.exceptions import ConnectionError, RedisError

from src.config import Config

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service for managing sessions and temporary data."""
    
    _instance = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection."""
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish connection to Redis."""
        try:
            if self._client is None:
                self._client = redis.Redis(
                    host=Config.REDIS_HOST,
                    port=Config.REDIS_PORT,
                    password=Config.REDIS_PASSWORD if Config.REDIS_PASSWORD else None,
                    db=Config.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # Test connection
                self._client.ping()
                logger.info(f"Connected to Redis at {Config.REDIS_HOST}:{Config.REDIS_PORT}")
                
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = self._client.get(key)
            if value:
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
            
        except RedisError as e:
            logger.warning(f"Redis get error for key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, expiration: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if dict/list)
            expiration: Expiration time in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize value if it's a dict or list
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if expiration:
                self._client.setex(key, expiration, value)
            else:
                self._client.set(key, value)
            return True
            
        except RedisError as e:
            logger.warning(f"Redis set error for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._client.delete(key)
            return True
            
        except RedisError as e:
            logger.warning(f"Redis delete error for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            logger.warning(f"Redis exists error for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get session data from cache.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dict or None
        """
        return self.get(f"session:{session_id}")
    
    def set_session(self, session_id: str, session_data: dict, expiration: int) -> bool:
        """
        Store session data in cache.
        
        Args:
            session_id: Session ID
            session_data: Session data to store
            expiration: Expiration time in seconds
            
        Returns:
            True if successful
        """
        return self.set(f"session:{session_id}", session_data, expiration)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session from cache.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful
        """
        return self.delete(f"session:{session_id}")
    
    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Redis connection closed")


# Global cache service instance
cache_service = CacheService()


def init_cache():
    """Initialize cache connection. Call this on application startup."""
    cache_service.connect()
    return cache_service


def get_cache() -> CacheService:
    """Get the cache service instance."""
    return cache_service
