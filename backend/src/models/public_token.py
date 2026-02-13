"""Public Token model for managing user-specific public API tokens."""
import logging
from datetime import datetime
from typing import Optional, Dict, List
from bson import ObjectId

from src.services.db_service import get_database
from src.utils.token import generate_public_token

logger = logging.getLogger(__name__)


class PublicToken:
    """Public Token model for managing tokens used with public APIs and Nightbot."""
    
    @staticmethod
    def create_token(user_id: str, name: str = "Untitled Token", expires_at: Optional[datetime] = None) -> Optional[str]:
        """
        Create a new public token for a user.
        
        Args:
            user_id: User ID as string
            name: User-defined name for the token
            expires_at: Optional expiry datetime
            
        Returns:
            Token ID as string if successful, None otherwise
        """
        try:
            db = get_database()
            
            # Generate unique token
            token = generate_public_token()
            
            # Create token document
            token_doc = {
                'user_id': user_id,
                'token': token,
                'name': name,
                'created_at': datetime.utcnow(),
                'expires_at': expires_at,
                'last_used_at': None,
                'usage_count': 0,
                'is_revoked': False
            }
            
            result = db.public_tokens.insert_one(token_doc)
            logger.info(f"Public token created for user {user_id}: {name}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create public token: {str(e)}")
            return None
    
    @staticmethod
    def find_by_id(token_id: str) -> Optional[Dict]:
        """
        Find token by ID.
        
        Args:
            token_id: Token ID as string
            
        Returns:
            Token document or None if not found
        """
        try:
            db = get_database()
            token_doc = db.public_tokens.find_one({'_id': ObjectId(token_id)})
            return token_doc
            
        except Exception as e:
            logger.error(f"Failed to find token by ID: {str(e)}")
            return None
    
    @staticmethod
    def find_by_token_string(token: str) -> Optional[Dict]:
        """
        Find token by token string.
        
        Args:
            token: The actual token string
            
        Returns:
            Token document or None if not found
        """
        try:
            db = get_database()
            token_doc = db.public_tokens.find_one({'token': token, 'is_revoked': False})
            return token_doc
            
        except Exception as e:
            logger.error(f"Failed to find token by string: {str(e)}")
            return None
    
    @staticmethod
    def find_by_user(user_id: str) -> List[Dict]:
        """
        Find all tokens for a user.
        
        Args:
            user_id: User ID as string
            
        Returns:
            List of token documents
        """
        try:
            db = get_database()
            tokens = list(db.public_tokens.find({'user_id': user_id}).sort('created_at', -1))
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to find tokens for user: {str(e)}")
            return []
    
    @staticmethod
    def revoke_token(token_id: str, user_id: str) -> bool:
        """
        Revoke a token (mark as revoked, don't delete).
        
        Args:
            token_id: Token ID as string
            user_id: User ID to verify ownership
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            
            result = db.public_tokens.update_one(
                {'_id': ObjectId(token_id), 'user_id': user_id},
                {'$set': {'is_revoked': True, 'updated_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Token revoked: {token_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            return False
    
    @staticmethod
    def is_valid(token_doc: Dict) -> bool:
        """
        Check if a token is valid (not revoked, not expired).
        
        Args:
            token_doc: Token document from database
            
        Returns:
            True if valid, False otherwise
        """
        if token_doc.get('is_revoked'):
            return False
        
        expires_at = token_doc.get('expires_at')
        if expires_at and expires_at <= datetime.utcnow():
            return False
        
        return True
    
    @staticmethod
    def record_usage(token: str) -> bool:
        """
        Record usage of a token (increment counter, update last used).
        
        Args:
            token: The token string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = get_database()
            
            result = db.public_tokens.update_one(
                {'token': token},
                {
                    '$set': {'last_used_at': datetime.utcnow()},
                    '$inc': {'usage_count': 1}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to record token usage: {str(e)}")
            return False
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """
        Get user ID from a valid token string.
        
        Args:
            token: The public token string
            
        Returns:
            User ID as string or None if token is invalid
        """
        token_doc = PublicToken.find_by_token_string(token)
        
        if not token_doc:
            return None
        
        if not PublicToken.is_valid(token_doc):
            return None
        
        # Record usage
        PublicToken.record_usage(token)
        
        return token_doc.get('user_id')
