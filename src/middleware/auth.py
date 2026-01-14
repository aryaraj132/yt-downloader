"""Authentication middleware for protecting routes."""
import logging
from functools import wraps
from flask import request, jsonify, g

from src.utils.token import verify_public_token, verify_private_token
from src.models.session import Session
from src.models.user import User

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
