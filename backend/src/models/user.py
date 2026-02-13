"""User model for managing user accounts."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from bson import ObjectId
import bcrypt
import requests

from src.services.db_service import get_database

logger = logging.getLogger(__name__)


class User:
    """User model for authentication and account management."""
    
    @staticmethod
    def create_user(email: str, password: str) -> Optional[str]:
        """
        Create a new user account (legacy - for backward compatibility).
        
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
                'oauth_provider': None,
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
    def create_oauth_user(email: str, google_id: str, tokens: Dict) -> Optional[str]:
        """
        Create a new user account from Google OAuth.
        
        Args:
            email: User email address from Google
            google_id: Google user ID
            tokens: OAuth tokens dict containing access_token, refresh_token, expires_in, scope
            
        Returns:
            User ID as string if successful, None otherwise
        """
        try:
            db = get_database()
            
            # Calculate token expiry
            expires_in = tokens.get('expires_in', 3600)
            expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Create user document with OAuth data
            user_doc = {
                'email': email.lower(),
                'password_hash': None,  # No password for OAuth users
                'google_id': google_id,
                'google_access_token': tokens.get('access_token'),
                'google_refresh_token': tokens.get('refresh_token'),
                'google_token_expiry': expiry_time,
                'google_scopes': tokens.get('scope', '').split(),
                'oauth_provider': 'google',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = db.users.insert_one(user_doc)
            logger.info(f"OAuth user created: {email} (Google ID: {google_id})")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create OAuth user: {str(e)}")
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
    
    @staticmethod
    def find_by_google_id(google_id: str) -> Optional[Dict]:
        """
        Find user by Google ID.
        
        Args:
            google_id: Google user ID
            
        Returns:
            User document or None if not found
        """
        try:
            db = get_database()
            user = db.users.find_one({'google_id': google_id})
            return user
            
        except Exception as e:
            logger.error(f"Failed to find user by Google ID: {str(e)}")
            return None
    
    @staticmethod
    def refresh_google_token(user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Refresh user's Google OAuth access token using refresh token.
        
        Args:
            user_id: User ID as string
            
        Returns:
            Tuple of (success: bool, new_access_token: str | None)
        """
        try:
            from src.config import Config
            
            db = get_database()
            user = User.find_by_id(user_id)
            
            if not user or not user.get('google_refresh_token'):
                logger.error(f"Cannot refresh token: no refresh token for user {user_id}")
                return False, None
            
            # Request new access token from Google
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                'client_id': Config.GOOGLE_CLIENT_ID,
                'client_secret': Config.GOOGLE_CLIENT_SECRET,
                'refresh_token': user['google_refresh_token'],
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(token_url, data=data)
            
            if response.status_code != 200:
                logger.error(f"Failed to refresh token: {response.text}")
                return False, None
            
            tokens = response.json()
            new_access_token = tokens.get('access_token')
            expires_in = tokens.get('expires_in', 3600)
            expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Update user with new token
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'google_access_token': new_access_token,
                        'google_token_expiry': expiry_time,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Token refreshed for user: {user_id}")
                return True, new_access_token
            
            return False, None
            
        except Exception as e:
            logger.error(f"Failed to refresh Google token: {str(e)}")
            return False, None
    
    @staticmethod
    def get_valid_access_token(user_id: str) -> Optional[str]:
        """
        Get a valid Google access token for the user, refreshing if necessary.
        
        Args:
            user_id: User ID as string
            
        Returns:
            Valid access token or None
        """
        try:
            user = User.find_by_id(user_id)
            
            if not user or not user.get('google_access_token'):
                logger.error(f"No access token found for user {user_id}")
                return None
            
            # Check if token is expired or about to expire (within 5 minutes)
            expiry = user.get('google_token_expiry')
            if expiry and expiry <= datetime.utcnow() + timedelta(minutes=5):
                logger.info(f"Token expired or expiring soon for user {user_id}, refreshing...")
                success, new_token = User.refresh_google_token(user_id)
                if success:
                    return new_token
                else:
                    logger.error(f"Failed to refresh token for user {user_id}")
                    return None
            
            return user['google_access_token']
            
        except Exception as e:
            logger.error(f"Failed to get valid access token: {str(e)}")
            return None
    
    @staticmethod
    def generate_public_token(user_id: str) -> Optional[str]:
        """
        Generate a new public token for the user.
        Overwrites any existing public token.
        
        Args:
            user_id: User ID as string
            
        Returns:
            Generated public token or None
        """
        try:
            from src.utils.token import generate_public_token
            
            # Generate unique token
            token = generate_public_token()
            
            # Update user document
            db = get_database()
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'public_token': token}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Public token generated for user {user_id}")
                return token
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate public token: {str(e)}")
            return None
    
    @staticmethod
    def find_by_public_token(token: str) -> Optional[Dict]:
        """
        Find user by their public token.
        
        Args:
            token: Public token string
            
        Returns:
            User document or None
        """
        try:
            db = get_database()
            user = db.users.find_one({'public_token': token})
            return user
            
        except Exception as e:
            logger.error(f"Failed to find user by public token: {str(e)}")
            return None

