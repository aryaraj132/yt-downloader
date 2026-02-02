"""
Rate limiting service for public API endpoints.
Uses IP address + browser fingerprint composite key to track usage.
"""
import logging
import hashlib
import json
from typing import Optional, Tuple
from datetime import datetime, timedelta
from src.services.cache_service import get_cache
from src.config import Config

logger = logging.getLogger(__name__)


class RateLimiterService:
    """Service for managing rate limits on public API endpoints."""
    
    KEY_PREFIX = "rate_limit:public:"
    
    @staticmethod
    def create_client_id(ip: str, fingerprint: dict) -> str:
        """
        Create a unique client ID from IP and browser fingerprint.
        
        Args:
            ip: Client IP address
            fingerprint: Browser fingerprint data (userAgent, screen, timezone, language, platform)
            
        Returns:
            SHA256 hash of composite client data
        """
        try:
            composite = f"{ip}:{fingerprint.get('userAgent', '')}:{fingerprint.get('screen', '')}:{fingerprint.get('timezone', 0)}:{fingerprint.get('language', '')}"
            client_id = hashlib.sha256(composite.encode()).hexdigest()
            return client_id
        except Exception as e:
            logger.error(f"Error creating client ID: {str(e)}")
            # Fallback to IP only if fingerprint processing fails
            return hashlib.sha256(ip.encode()).hexdigest()
    
    @staticmethod
    def _get_reset_time() -> datetime:
        """Calculate when the rate limit will reset (midnight UTC)."""
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        reset_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
        return reset_time
    
    @staticmethod
    def _get_ttl_seconds() -> int:
        """Get seconds until midnight UTC."""
        now = datetime.utcnow()
        reset_time = RateLimiterService._get_reset_time()
        return int((reset_time - now).total_seconds())
    
    @staticmethod
    def check_rate_limit(client_id: str) -> Tuple[bool, int, datetime]:
        """
        Check if client has remaining quota.
        
        Args:
            client_id: Client identifier hash
            
        Returns:
            Tuple of (allowed, remaining_count, reset_time)
        """
        try:
            cache = get_cache()
            key = f"{RateLimiterService.KEY_PREFIX}{client_id}"
            
            data = cache.get(key)
            
            if not data:
                # No data = full quota available
                return (True, Config.PUBLIC_API_RATE_LIMIT, RateLimiterService._get_reset_time())
            
            count = data.get('count', 0)
            remaining = Config.PUBLIC_API_RATE_LIMIT - count
            
            if remaining > 0:
                return (True, remaining, RateLimiterService._get_reset_time())
            else:
                return (False, 0, RateLimiterService._get_reset_time())
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # On error, allow request (fail open)
            return (True, Config.PUBLIC_API_RATE_LIMIT, RateLimiterService._get_reset_time())
    
    @staticmethod
    def increment_usage(client_id: str, operation_type: str, ip: str, fingerprint: dict) -> bool:
        """
        Increment usage counter for client.
        
        Args:
            client_id: Client identifier hash
            operation_type: Type of operation ('clip' or 'encode')
            ip: Client IP address
            fingerprint: Browser fingerprint data
            
        Returns:
            True if successful
        """
        try:
            cache = get_cache()
            key = f"{RateLimiterService.KEY_PREFIX}{client_id}"
            
            data = cache.get(key)
            
            if not data:
                data = {
                    'count': 0,
                    'operations': [],
                    'ip': ip,
                    'fingerprint': fingerprint
                }
            
            # Increment count
            data['count'] = data.get('count', 0) + 1
            
            # Add operation record
            operations = data.get('operations', [])
            operations.append({
                'type': operation_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            data['operations'] = operations
            
            # Save with TTL until midnight
            ttl = RateLimiterService._get_ttl_seconds()
            cache.set(key, data, ttl)
            
            logger.info(f"Rate limit incremented for client {client_id[:8]}... ({operation_type}): {data['count']}/{Config.PUBLIC_API_RATE_LIMIT}")
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing usage: {str(e)}")
            return False
    
    @staticmethod
    def get_remaining(client_id: str) -> int:
        """
        Get remaining quota for client.
        
        Args:
            client_id: Client identifier hash
            
        Returns:
            Number of operations remaining
        """
        try:
            cache = get_cache()
            key = f"{RateLimiterService.KEY_PREFIX}{client_id}"
            
            data = cache.get(key)
            
            if not data:
                return Config.PUBLIC_API_RATE_LIMIT
            
            count = data.get('count', 0)
            remaining = Config.PUBLIC_API_RATE_LIMIT - count
            return max(0, remaining)
            
        except Exception as e:
            logger.error(f"Error getting remaining quota: {str(e)}")
            return Config.PUBLIC_API_RATE_LIMIT
    
    @staticmethod
    def get_client_info(client_id: str) -> Optional[dict]:
        """
        Get detailed usage information for client.
        
        Args:
            client_id: Client identifier hash
            
        Returns:
            Dict with usage details or None
        """
        try:
            cache = get_cache()
            key = f"{RateLimiterService.KEY_PREFIX}{client_id}"
            
            data = cache.get(key)
            return data
            
        except Exception as e:
            logger.error(f"Error getting client info: {str(e)}")
            return None
    
    @staticmethod
    def reset_limit(client_id: str) -> bool:
        """
        Reset rate limit for client (admin function).
        
        Args:
            client_id: Client identifier hash
            
        Returns:
            True if successful
        """
        try:
            cache = get_cache()
            key = f"{RateLimiterService.KEY_PREFIX}{client_id}"
            
            cache.delete(key)
            logger.info(f"Rate limit reset for client {client_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}")
            return False
