
import json
import logging
from typing import Optional, Any
import redis
from redis.exceptions import ConnectionError, RedisError

from src.config import Config

logger = logging.getLogger(__name__)

class CacheService:
    
    _instance = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        
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
        
        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            logger.warning(f"Redis exists error for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[dict]:
        
        return self.get(f"session:{session_id}")
    
    def set_session(self, session_id: str, session_data: dict, expiration: int) -> bool:
        
        return self.set(f"session:{session_id}", session_data, expiration)
    
    def delete_session(self, session_id: str) -> bool:
        
        return self.delete(f"session:{session_id}")
    
    def close(self):
        
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Redis connection closed")

# Global cache service instance
cache_service = CacheService()

def init_cache():
    
    cache_service.connect()
    return cache_service

def get_cache() -> CacheService:
    
    return cache_service
