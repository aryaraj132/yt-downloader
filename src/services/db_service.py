
import logging
from typing import Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure

from src.config import Config

logger = logging.getLogger(__name__)

class DatabaseService:
    
    _instance = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        
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
        
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db
    
    def close(self):
        
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Database connection closed")
    
    @property
    def users(self):
        
        return self.get_db().users
    
    @property
    def sessions(self):
        
        return self.get_db().sessions
    
    @property
    def videos(self):
        
        return self.get_db().videos

# Global database service instance
db_service = DatabaseService()

def init_database():
    
    db_service.connect()
    return db_service

def get_database() -> DatabaseService:
    
    return db_service
