"""Authentication middleware for protecting routes."""
import logging
from functools import wraps
from flask import request, jsonify, g

from src.utils.token import verify_public_token, verify_private_token
from src.models.session import Session
from src.models.user import User
from src.config import Config

logger = logging.getLogger(__name__)


def get_token_from_request() -> str:
    """
    Extract token from request headers.
    
    Returns:
        Token string or None
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Support both "Bearer <token>" and plain token
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    elif len(parts) == 1:
        return parts[0]
    
    return None


def require_public_token(f):
    """
    Middleware to require a valid public token.
    Used for public-facing endpoints like saving video info.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            logger.warning("Missing token in request")
            return jsonify({'error': 'Missing authentication token'}), 401
        
        if not verify_public_token(token):
            logger.warning("Invalid public token")
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Public token is valid, proceed
        return f(*args, **kwargs)
    
    return decorated_function


def require_private_token(f):
    """
    Middleware to require a valid private token with user session.
    Used for authenticated endpoints like downloading videos.
    Attaches user data to request context (g.user and g.user_id).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            logger.warning("Missing token in request")
            return jsonify({'error': 'Missing authentication token'}), 401
        
        # Verify private token and extract user info
        user_id, session_id, error = verify_private_token(token)
        
        if error:
            logger.warning(f"Invalid private token: {error}")
            return jsonify({'error': error}), 401
        
        # Verify session exists and is valid
        session = Session.find_by_id(session_id)
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return jsonify({'error': 'Invalid session'}), 401
        
        if not Session.is_valid(session):
            logger.warning(f"Session expired: {session_id}")
            return jsonify({'error': 'Session expired'}), 401
        
        # Get user data
        user = User.find_by_id(user_id)
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 401
        
        # Attach user data to request context
        g.user_id = user_id
        g.user = {
            '_id': str(user['_id']),
            'email': user['email'],
            'created_at': user['created_at'].isoformat() if user.get('created_at') else None
        }
        
        logger.debug(f"Authenticated user: {user['email']}")
        
        # Proceed with the request
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Optional authentication middleware.
    Attaches user data if valid token is provided, but doesn't require it.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if token:
            user_id, session_id, error = verify_private_token(token)
            
            if not error:
                session = Session.find_by_id(session_id)
                if session and Session.is_valid(session):
                    user = User.find_by_id(user_id)
                    if user:
                        g.user_id = user_id
                        g.user = {
                            '_id': str(user['_id']),
                            'email': user['email'],
                            'created_at': user['created_at'].isoformat() if user.get('created_at') else None
                        }
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_public_rate_limit(f):
    """
    Middleware to enforce rate limits on public API endpoints.
    Uses IP address + browser fingerprint for client identification.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from src.utils.client_info import get_client_ip, get_browser_fingerprint
        from src.services.rate_limiter_service import RateLimiterService
        from datetime import datetime
        
        # Extract client information
        ip = get_client_ip(request)
        fingerprint = get_browser_fingerprint(request)
        
        if not fingerprint:
            logger.warning("Missing or invalid browser fingerprint")
            return jsonify({'error': 'Browser fingerprint required'}), 400
        
        # Create client ID
        client_id = RateLimiterService.create_client_id(ip, fingerprint)
        
        # Check rate limit
        allowed, remaining, reset_time = RateLimiterService.check_rate_limit(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for client {client_id[:8]}... (IP: {ip})")
            response = jsonify({
                'error': 'Rate limit exceeded',
                'message': f'You have reached the daily limit of {Config.PUBLIC_API_RATE_LIMIT} operations. Please sign in for unlimited access.',
                'limit': Config.PUBLIC_API_RATE_LIMIT,
                'remaining': 0,
                'reset_at': reset_time.isoformat()
            })
            response.status_code = 429
            
            # Add rate limit headers
            response.headers['X-RateLimit-Limit'] = str(Config.PUBLIC_API_RATE_LIMIT)
            response.headers['X-RateLimit-Remaining'] = '0'
            response.headers['X-RateLimit-Reset'] = str(int(reset_time.timestamp()))
            
            return response
        
        # Attach client info to request context
        g.client_id = client_id
        g.client_ip = ip
        g.client_fingerprint = fingerprint
        g.rate_limit_remaining = remaining
        g.rate_limit_reset = reset_time
        
        # Execute the route function
        response = f(*args, **kwargs)
        
        # If response is a tuple (data, status_code), extract the response object
        if isinstance(response, tuple):
            response_obj = response[0]
            status_code = response[1] if len(response) > 1 else 200
        else:
            response_obj = response
            status_code = 200
        
        # Add rate limit headers to response
        if hasattr(response_obj, 'headers'):
            response_obj.headers['X-RateLimit-Limit'] = str(Config.PUBLIC_API_RATE_LIMIT)
            response_obj.headers['X-RateLimit-Remaining'] = str(remaining - 1)  # Subtract 1 for current operation
            response_obj.headers['X-RateLimit-Reset'] = str(int(reset_time.timestamp()))
        
        return response
    
    return decorated_function
