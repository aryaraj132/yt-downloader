"""Session model for managing user sessions."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from bson import ObjectId
import secrets

from src.services.db_service import get_database
from src.services.cache_service import get_cache
from src.config import Config

logger = logging.getLogger(__name__)


class Session:
    """Session model for user authentication sessions."""
    
    @staticmethod
    def create_session(user_id: str, token: str) -> Optional[str]:
        """
        Create a new user session in both MongoDB and Redis cache.
        
        Args:
            user_id: User ID as string
            token: JWT token for this session
            
        Returns:
            Session ID as string if successful, None otherwise
        """
        try:
            db = get_database()
            cache = get_cache()
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(seconds=Config.JWT_PRIVATE_EXPIRATION)
            
            # Create session document
            session_doc = {
                'user_id': ObjectId(user_id),
                'token': token,
                'created_at': datetime.utcnow(),
                'expires_at': expires_at
            }
            
            # Save to MongoDB
            result = db.sessions.insert_one(session_doc)
            session_id = str(result.inserted_id)
            
            # Save to Redis cache
            session_data = {
                'user_id': user_id,
                'session_id': session_id,
                'created_at': session_doc['created_at'].isoformat()
            }
            cache.set_session(session_id, session_data, Config.JWT_PRIVATE_EXPIRATION)
            
            logger.info(f"Session created for user: {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            return None
    
    @staticmethod
    def find_by_token(token: str) -> Optional[Dict]:
        """
        Find session by token.
        
        Args:
            token: JWT token
            
        Returns:
            Session document or None if not found
        """
        try:
            db = get_database()
            session = db.sessions.find_one({'token': token})
            return session
            
        except Exception as e:
            logger.error(f"Failed to find session by token: {str(e)}")
            return None
    
    @staticmethod
    def find_by_id(session_id: str) -> Optional[Dict]:
        """
        Find session by ID. Checks cache first, then falls back to MongoDB.
        
        Args:
            session_id: Session ID as string
            
        Returns:
            Session document or None if not found
        """
        try:
            cache = get_cache()
            
            # Try cache first
            cached_session = cache.get_session(session_id)
            if cached_session:
                logger.debug(f"Session found in cache: {session_id}")
                return cached_session
            
            # Fall back to MongoDB
            db = get_database()
            session = db.sessions.find_one({'_id': ObjectId(session_id)})
            
            if session:
                # Repopulate cache
                session_data = {
                    'user_id': str(session['user_id']),
                    'session_id': session_id,
                    'created_at': session['created_at'].isoformat()
                }
                
                # Calculate remaining TTL
                if session.get('expires_at'):
                    ttl = int((session['expires_at'] - datetime.utcnow()).total_seconds())
                    if ttl > 0:
                        cache.set_session(session_id, session_data, ttl)
                
                logger.debug(f"Session found in database: {session_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to find session by ID: {str(e)}")
            return None
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete session from both MongoDB and Redis cache.
        
        Args:
            session_id: Session ID as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            cache = get_cache()
            
            # Delete from MongoDB
            result = db.sessions.delete_one({'_id': ObjectId(session_id)})
            
            # Delete from cache
            cache.delete_session(session_id)
            
            if result.deleted_count > 0:
                logger.info(f"Session deleted: {session_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            return False
    
    @staticmethod
    def delete_user_sessions(user_id: str) -> int:
        """
        Delete all sessions for a user.
        
        Args:
            user_id: User ID as string
            
        Returns:
            Number of sessions deleted
        """
        try:
            db = get_database()
            cache = get_cache()
            
            # Find all sessions for user
            sessions = db.sessions.find({'user_id': ObjectId(user_id)})
            
            # Delete from cache
            for session in sessions:
                session_id = str(session['_id'])
                cache.delete_session(session_id)
            
            # Delete from MongoDB
            result = db.sessions.delete_many({'user_id': ObjectId(user_id)})
            
            logger.info(f"Deleted {result.deleted_count} sessions for user: {user_id}")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete user sessions: {str(e)}")
            return 0
    
    @staticmethod
    def cleanup_expired() -> int:
        """
        Delete expired sessions from database.
        
        Returns:
            Number of sessions deleted
        """
        try:
            db = get_database()
            
            # Delete expired sessions
            result = db.sessions.delete_many({'expires_at': {'$lte': datetime.utcnow()}})
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired sessions")
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0
    
    @staticmethod
    def is_valid(session: Dict) -> bool:
        """
        Check if session is still valid (not expired).
        
        Args:
            session: Session document
            
        Returns:
            True if valid, False if expired
        """
        if not session:
            return False
        
        expires_at = session.get('expires_at')
        if not expires_at:
            return False
        
        # Handle both datetime objects and ISO strings
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        return expires_at > datetime.utcnow()
