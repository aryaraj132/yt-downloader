"""Firebase Admin SDK service."""
import logging
import firebase_admin
from firebase_admin import auth

logger = logging.getLogger(__name__)


class FirebaseService:
    """Firebase Admin SDK service wrapper."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def verify_id_token(self, id_token: str):
        """
        Verify Firebase ID token (if using Firebase Authentication).
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            Decoded token with user information
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Failed to verify Firebase ID token: {str(e)}")
            raise
    
    def get_user(self, uid: str):
        """
        Get user by Firebase UID.
        
        Args:
            uid: Firebase user ID
            
        Returns:
            User record
        """
        try:
            user = auth.get_user(uid)
            return user
        except Exception as e:
            logger.error(f"Failed to get Firebase user: {str(e)}")
            raise


# Global Firebase service instance
firebase_service = FirebaseService()


def get_firebase() -> FirebaseService:
    """Get the Firebase service instance."""
    return firebase_service
