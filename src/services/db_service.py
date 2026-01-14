"""MongoDB database service."""
import logging
from typing import Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure

from src.config import Config

logger = logging.getLogger(__name__)


class DatabaseService:
    """MongoDB database service for managing connections and operations."""
    
    _instance = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single database connection."""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            if self._client is None:
                self._client = MongoClient(
                    Config.MONGODB_URI,
                    serverSelectionTimeoutMS=5000
                )
                # Test connection
                self._client.admin.command('ping')
                self._db = self._client[Config.MONGODB_DB_NAME]
                logger.info(f"Connected to MongoDB database: {Config.MONGODB_DB_NAME}")
                
                # Initialize indexes
                self._create_indexes()
                
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for optimal query performance."""
        try:
            # Users collection indexes
            self._db.users.create_index([("email", ASCENDING)], unique=True)
            self._db.users.create_index([("created_at", DESCENDING)])
            
            # Sessions collection indexes
            self._db.sessions.create_index([("user_id", ASCENDING)])
            self._db.sessions.create_index([("token", ASCENDING)], unique=True)
            self._db.sessions.create_index([("expires_at", ASCENDING)])
            
            # Videos collection indexes
            self._db.videos.create_index([("user_id", ASCENDING)])
            self._db.videos.create_index([("status", ASCENDING)])
            self._db.videos.create_index([("created_at", DESCENDING)])
            self._db.videos.create_index([("expires_at", ASCENDING)])
            
            logger.info("Database indexes created successfully")
            
        except OperationFailure as e:
            logger.warning(f"Index creation warning: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
    
    def get_db(self) -> Database:
        """
        Get database instance.
        
        Returns:
            Database instance
            
        Raises:
            RuntimeError: If not connected to database
        """
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db
    
    def close(self):
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Database connection closed")
    
    @property
    def users(self):
        """Get users collection."""
        return self.get_db().users
    
    @property
    def sessions(self):
        """Get sessions collection."""
        return self.get_db().sessions
    
    @property
    def videos(self):
        """Get videos collection."""
        return self.get_db().videos


# Global database service instance
db_service = DatabaseService()


def init_database():
    """Initialize database connection. Call this on application startup."""
    db_service.connect()
    return db_service


def get_database() -> DatabaseService:
    """Get the database service instance."""
    return db_service
