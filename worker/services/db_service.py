"""
MongoDB helper for the worker.
Direct pymongo connection — no need for full ORM since worker only updates status/progress.
"""
import logging
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)

_client = None
_db = None


def get_database():
    """Get MongoDB database connection."""
    global _client, _db
    if _db is None:
        _client = MongoClient(Config.MONGODB_URI)
        _db = _client[Config.MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB: {Config.MONGODB_DB_NAME}")
    return _db


def update_video_status(video_id, status, file_path=None, storage_mode=None,
                        error_message=None, file_size_bytes=None):
    """Update video document status in MongoDB."""
    db = get_database()
    update = {
        '$set': {
            'status': status,
            'updated_at': datetime.utcnow(),
        }
    }
    if file_path is not None:
        update['$set']['file_path'] = file_path
    if storage_mode is not None:
        update['$set']['storage_mode'] = storage_mode
    if error_message is not None:
        update['$set']['error_message'] = error_message
    if file_size_bytes is not None:
        update['$set']['file_size_bytes'] = file_size_bytes

    result = db.videos.update_one(
        {'_id': ObjectId(video_id)},
        update
    )
    logger.info(f"Updated video {video_id} status to {status} (matched: {result.matched_count})")
    return result.modified_count > 0


def update_encoding_progress(video_id, progress, completed_at=None):
    """Update encoding progress in MongoDB."""
    db = get_database()
    update = {
        '$set': {
            'encoding_progress': progress,
            'updated_at': datetime.utcnow(),
        }
    }
    if completed_at:
        update['$set']['encoding_completed_at'] = completed_at

    db.videos.update_one(
        {'_id': ObjectId(video_id)},
        update
    )


def get_video(video_id):
    """Get video document by ID."""
    db = get_database()
    return db.videos.find_one({'_id': ObjectId(video_id)})
