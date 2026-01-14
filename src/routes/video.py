"""Video routes for saving and downloading videos."""
import logging
import os
from flask import Blueprint, request, jsonify, g, send_file

from src.models.video import Video, VideoStatus
from src.services.video_service import VideoService
from src.utils.validators import validate_youtube_url, validate_time_range
from src.middleware.auth import require_public_token, require_private_token
from src.config import Config

logger = logging.getLogger(__name__)

video_bp = Blueprint('video', __name__, url_prefix='/api/video')


@video_bp.route('/save', methods=['POST'])
@require_public_token
def save_video_info():
    """
    Save video information for later download.
    Requires public API token.
    
    Request body:
        {
            "url": "https://youtube.com/watch?v=...",
            "start_time": 60,
            "end_time": 120,
            "user_id": "..." (required for saving against user)
        }
    
    Returns:
        {
            "message": "Video info saved successfully",
            "video_id": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400
        
        url = data.get('url')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        user_id = data.get('user_id')  # Required with public token
        
        # Validate input
        if not url or start_time is None or end_time is None or not user_id:
            return jsonify({'error': 'Missing required fields: url, start_time, end_time, user_id'}), 400
        
        # Validate YouTube URL
        is_valid_url, url_error = validate_youtube_url(url)
        if not is_valid_url:
            return jsonify({'error': url_error}), 400
        
        # Validate time range
        try:
            start_time = int(start_time)
            end_time = int(end_time)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid time values'}), 400
        
        is_valid_time, time_error = validate_time_range(
            start_time, end_time, Config.MAX_VIDEO_DURATION
        )
        if not is_valid_time:
            return jsonify({'error': time_error}), 400
        
        # Save video info
        video_id = Video.create_video_info(user_id, url, start_time, end_time)
        
        if not video_id:
            return jsonify({'error': 'Failed to save video info'}), 500
        
        logger.info(f"Video info saved: {video_id}")
        
        return jsonify({
            'message': 'Video info saved successfully',
            'video_id': video_id
        }), 201
        
    except Exception as e:
        logger.error(f"Save video info error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/download/<video_id>', methods=['POST'])
@require_private_token
def download_video(video_id):
    """
    Download video segment.
    Requires private authentication token.
    
    Returns:
        File download or processing status
    """
    try:
        # Verify video exists
        video = Video.find_by_id(video_id)
        
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Verify ownership
        if not Video.verify_ownership(video_id, g.user_id):
            return jsonify({'error': 'Unauthorized access to video'}), 403
        
        # Check if already downloaded
        if video['status'] == VideoStatus.COMPLETED and video.get('file_path'):
            file_path = video['file_path']
            
            if os.path.exists(file_path):
                logger.info(f"Serving cached video: {video_id}")
                return send_file(
                    file_path,
                    mimetype='video/mp4',
                    as_attachment=True,
                    download_name=f"video_{video_id}.mp4"
                )
        
        # Check if currently processing
        if video['status'] == VideoStatus.PROCESSING:
            return jsonify({
                'message': 'Video is currently being processed',
                'status': 'processing'
            }), 202
        
        # Check if previously failed
        if video['status'] == VideoStatus.FAILED:
            return jsonify({
                'error': 'Video processing failed',
                'message': video.get('error_message', 'Unknown error')
            }), 500
        
        # Start download
        success, file_path, error = VideoService.download_video(video_id)
        
        if not success:
            return jsonify({
                'error': 'Failed to download video',
                'message': error
            }), 500
        
        # Send file
        logger.info(f"Serving downloaded video: {video_id}")
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"video_{video_id}.mp4"
        )
        
    except Exception as e:
        logger.error(f"Download video error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/status/<video_id>', methods=['GET'])
@require_private_token
def get_video_status(video_id):
    """
    Get video processing status.
    Requires private authentication token.
    
    Returns:
        {
            "status": "pending|processing|completed|failed",
            "file_path": "...",
            "error_message": "..."
        }
    """
    try:
        video = Video.find_by_id(video_id)
        
        if not video:
            return jsonify({'error': 'Video not found'}), 404
        
        # Verify ownership
        if not Video.verify_ownership(video_id, g.user_id):
            return jsonify({'error': 'Unauthorized access to video'}), 403
        
        return jsonify({
            'video_id': video_id,
            'status': video['status'],
            'url': video['url'],
            'start_time': video['start_time'],
            'end_time': video['end_time'],
            'created_at': video['created_at'].isoformat(),
            'file_available': video.get('file_path') is not None and os.path.exists(video.get('file_path', '')),
            'error_message': video.get('error_message')
        }), 200
        
    except Exception as e:
        logger.error(f"Get video status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/list', methods=['GET'])
@require_private_token
def list_user_videos():
    """
    List all videos for the authenticated user.
    Requires private authentication token.
    
    Returns:
        {
            "videos": [...]
        }
    """
    try:
        videos = Video.find_by_user(g.user_id)
        
        video_list = []
        for video in videos:
            video_list.append({
                'video_id': str(video['_id']),
                'url': video['url'],
                'start_time': video['start_time'],
                'end_time': video['end_time'],
                'status': video['status'],
                'created_at': video['created_at'].isoformat(),
                'file_available': video.get('file_path') is not None and os.path.exists(video.get('file_path', ''))
            })
        
        return jsonify({'videos': video_list}), 200
        
    except Exception as e:
        logger.error(f"List videos error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
