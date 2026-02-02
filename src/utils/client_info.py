"""
Utility functions for extracting client information from requests.
"""
import logging
import json
from typing import Optional
from flask import Request

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract real client IP from request headers.
    Checks X-Forwarded-For, X-Real-IP, and falls back to remote_addr.
    
    Args:
        request: Flask request object
        
    Returns:
        Client IP address
    """
    try:
        # Check X-Forwarded-For header (used by proxies/load balancers)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(',')[0].strip()
        
        # Check X-Real-IP header (used by nginx)
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to remote_addr
        return request.remote_addr or '0.0.0.0'
        
    except Exception as e:
        logger.error(f"Error extracting client IP: {str(e)}")
        return '0.0.0.0'


def get_browser_fingerprint(request: Request) -> Optional[dict]:
    """
    Parse browser fingerprint from request headers.
    
    Args:
        request: Flask request object
        
    Returns:
        Browser fingerprint dict or None
    """
    try:
        fingerprint_header = request.headers.get('X-Browser-Fingerprint')
        
        if not fingerprint_header:
            logger.warning("Missing X-Browser-Fingerprint header")
            # Return minimal fingerprint from User-Agent
            return {
                'userAgent': request.headers.get('User-Agent', ''),
                'screen': '',
                'timezone': 0,
                'language': '',
                'platform': ''
            }
        
        # Parse JSON fingerprint
        fingerprint = json.loads(fingerprint_header)
        
        # Validate required fields
        required_fields = ['userAgent', 'screen', 'timezone', 'language', 'platform']
        for field in required_fields:
            if field not in fingerprint:
                fingerprint[field] = ''
        
        return fingerprint
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in X-Browser-Fingerprint header")
        # Return minimal fingerprint
        return {
            'userAgent': request.headers.get('User-Agent', ''),
            'screen': '',
            'timezone': 0,
            'language': '',
            'platform': ''
        }
    except Exception as e:
        logger.error(f"Error parsing browser fingerprint: {str(e)}")
        return None
