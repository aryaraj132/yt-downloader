"""User model for managing user accounts."""
import logging
from datetime import datetime
from typing import Optional, Dict
from bson import ObjectId
import bcrypt

from src.services.db_service import get_database

logger = logging.getLogger(__name__)


class User:
    """User model for authentication and account management."""
    
    @staticmethod
    def create_user(email: str, password: str) -> Optional[str]:
        """
        Create a new user account.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            
        Returns:
            User ID as string if successful, None otherwise
        """
        try:
            db = get_database()
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create user document
            user_doc = {
                'email': email.lower(),
                'password_hash': password_hash,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = db.users.insert_one(user_doc)
            logger.info(f"User created: {email}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            return None
    
    @staticmethod
    def find_by_email(email: str) -> Optional[Dict]:
        """
        Find user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User document or None if not found
        """
        try:
            db = get_database()
            user = db.users.find_one({'email': email.lower()})
            return user
            
        except Exception as e:
            logger.error(f"Failed to find user by email: {str(e)}")
            return None
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict]:
        """
        Find user by ID.
        
        Args:
            user_id: User ID as string
            
        Returns:
            User document or None if not found
        """
        try:
            db = get_database()
            user = db.users.find_one({'_id': ObjectId(user_id)})
            return user
            
        except Exception as e:
            logger.error(f"Failed to find user by ID: {str(e)}")
            return None
    
    @staticmethod
    def verify_password(user: Dict, password: str) -> bool:
        """
        Verify user password.
        
        Args:
            user: User document from database
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            password_hash = user.get('password_hash')
            if isinstance(password_hash, str):
                password_hash = password_hash.encode('utf-8')
            
            return bcrypt.checkpw(password.encode('utf-8'), password_hash)
            
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    @staticmethod
    def update_password(user_id: str, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID as string
            new_password: New plain text password (will be hashed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            
            # Hash new password
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            
            # Update user document
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'password_hash': password_hash,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Password updated for user: {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update password: {str(e)}")
            return False
    
    @staticmethod
    def update_google_tokens(user_id: str, tokens: Dict) -> bool:
        """
        Update user's Google OAuth tokens.
        
        Args:
            user_id: User ID as string
            tokens: Dictionary containing access_token, refresh_token, expiry, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'google_tokens': tokens,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Google tokens updated for user: {user_id}")
                return True
            return True # Return true even if not modified (e.g. tokens same)
            
        except Exception as e:
            logger.error(f"Failed to update google tokens: {str(e)}")
            return False
    
    @staticmethod
    def email_exists(email: str) -> bool:
        """
        Check if email already exists in database.
        
        Args:
            email: Email address to check
            
        Returns:
            True if exists, False otherwise
        """
        user = User.find_by_email(email)
        return user is not None
