"""Token utilities for JWT generation and validation."""
import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from src.config import Config

logger = logging.getLogger(__name__)


class TokenType:
    """Token type constants."""
    PUBLIC = "public"
    PRIVATE = "private"


def generate_public_token() -> str:
    """
    Generate a public API token for saving video information.
    This token has limited permissions and can be used publicly.
    
    Returns:
        str: JWT token string
    """
    try:
        payload = {
            'type': TokenType.PUBLIC,
            'exp': datetime.utcnow() + timedelta(seconds=Config.JWT_PUBLIC_EXPIRATION),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, Config.JWT_PUBLIC_SECRET, algorithm='HS256')
        logger.debug("Public token generated successfully")
        return token
        
    except Exception as e:
        logger.error(f"Failed to generate public token: {str(e)}")
        raise


def generate_private_token(user_id: str, session_id: str) -> str:
    """
    Generate a private user token for authenticated operations.
    This token includes user_id and session_id for full access.
    
    Args:
        user_id: MongoDB ObjectId of the user as string
        session_id: Session ID from MongoDB/Redis
        
    Returns:
        str: JWT token string
    """
    try:
        payload = {
            'type': TokenType.PRIVATE,
            'user_id': user_id,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(seconds=Config.JWT_PRIVATE_EXPIRATION),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, Config.JWT_PRIVATE_SECRET, algorithm='HS256')
        logger.debug(f"Private token generated for user {user_id}")
        return token
        
    except Exception as e:
        logger.error(f"Failed to generate private token: {str(e)}")
        raise


def decode_token(token: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (payload dict, error message). If successful, error is None.
        If failed, payload is None and error contains the error message.
    """
    try:
        # First, decode without verification to check token type
        unverified = jwt.decode(token, options={"verify_signature": False})
        token_type = unverified.get('type')
        
        # Select the appropriate secret based on token type
        if token_type == TokenType.PUBLIC:
            secret = Config.JWT_PUBLIC_SECRET
        elif token_type == TokenType.PRIVATE:
            secret = Config.JWT_PRIVATE_SECRET
        else:
            return None, "Invalid token type"
        
        # Decode and verify the token
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        logger.debug(f"Token decoded successfully: type={token_type}")
        return payload, None
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None, "Token has expired"
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None, f"Invalid token: {str(e)}"
    except Exception as e:
        logger.error(f"Failed to decode token: {str(e)}")
        return None, f"Token validation error: {str(e)}"


def verify_public_token(token: str) -> bool:
    """
    Verify that a token is a valid public token.
    
    Args:
        token: JWT token string
        
    Returns:
        bool: True if valid public token, False otherwise
    """
    payload, error = decode_token(token)
    if error or not payload:
        return False
    
    return payload.get('type') == TokenType.PUBLIC


def verify_private_token(token: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Verify that a token is a valid private token and extract user information.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (user_id, session_id, error). If successful, error is None.
        If failed, user_id and session_id are None, error contains the message.
    """
    payload, error = decode_token(token)
    if error or not payload:
        return None, None, error or "Invalid token"
    
    if payload.get('type') != TokenType.PRIVATE:
        return None, None, "Not a private token"
    
    user_id = payload.get('user_id')
    session_id = payload.get('session_id')
    
    if not user_id or not session_id:
        return None, None, "Token missing required fields"
    
    return user_id, session_id, None
