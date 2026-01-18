"""Video routes for saving and downloading videos."""
import logging
import os
from flask import Blueprint, request, jsonify, g, send_file

from src.models.video import Video, VideoStatus
from src.data import VideoData  # Use data layer
from src.services.youtube_service import YouTubeService
from src.utils.validators import (
    validate_youtube_url, validate_time_range, validate_video_id,
    validate_format_preference, validate_resolution_preference
)
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
        
        # Optional fields
        additional_message = data.get('additional_message')
        clip_offset = data.get('clip_offset')
        
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
            if clip_offset is not None:
                clip_offset = int(clip_offset)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid time values'}), 400
        
        is_valid_time, time_error = validate_time_range(
            start_time, end_time, Config.MAX_VIDEO_DURATION
        )
        if not is_valid_time:
            return jsonify({'error': time_error}), 400
        
        # Fetch available formats for this video (720p+)
        try:
            youtube_video_id = YouTubeService.parse_video_id_from_url(url)
            if youtube_video_id:
                available_formats = YouTubeService.get_available_formats(youtube_video_id)
            else:
                available_formats = None
        except Exception as e:
            logger.warning(f"Could not fetch available formats: {e}")
            available_formats = None
        
        # Save video info (without format/resolution - those are download-time choices)
        video_id = Video.create_video_info(
            user_id, url, start_time, end_time,
            additional_message=additional_message,
            clip_offset=clip_offset,
            available_formats=available_formats  # Store available formats
        )
        
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


@video_bp.route('/save/stream/<token>/<video_id>', methods=['GET', 'POST'])
def save_video_from_stream(token, video_id):
    """
    Save video clip from live stream using video ID and querystring parameters.
    This endpoint is designed for use with Nightbot urlfetch.
    Public-facing endpoint that accepts token in URL path.
    
    URL Parameters:
        token: Public API token
        video_id: YouTube video ID (11 characters)
    
    Query Parameters:
        message: User message/description for the clip (optional)
        offset: Seconds to capture before/after timestamp (default: 60)
        duration: Total clip duration in seconds (default: 120)
        user_id: User ID who owns the public token (required)
    
    Returns:
        {
            "message": "Video clip saved successfully",
            "video_id": "..."
        }
    """
    try:
        # Get query parameters
        message = request.args.get('message', '')
        user_id = request.args.get('user_id')
        
        try:
            offset = int(request.args.get('offset', 60))
            duration = int(request.args.get('duration', 120))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid offset or duration values'}), 400
        
        # Validate user_id is provided
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        # Validate video ID format
        is_valid, error = validate_video_id(video_id)
        if not is_valid:
            return jsonify({'error': error}), 400
        
        # Construct YouTube URL from video ID
        url = YouTubeService.construct_video_url(video_id)
        
        # Calculate start and end times
        # For live streams, we use current timestamp and offset
        # Note: For actual live streams, you might need to adjust this logic
        # based on when the stream started
        import time
        current_time = int(time.time())
        
        # For now, we'll use a simple offset-based approach
        # In a real implementation, you'd need to:
        # 1. Determine if the video is currently live
        # 2. Calculate the actual timestamp in the video timeline
        # 3. Use that as the center point for the clip
        
        # Simple implementation: capture offset seconds before to (duration - offset) seconds after
        start_time = 0  # Placeholder - would be calculated based on live stream position
        end_time = duration
        
        # Validate time range
        is_valid_time, time_error = validate_time_range(
            start_time, end_time, Config.MAX_VIDEO_DURATION
        )
        if not is_valid_time:
            return jsonify({'error': time_error}), 400
        
        # Fetch available formats for this video (720p+)
        try:
            available_formats = YouTubeService.get_available_formats(video_id)
        except Exception as e:
            logger.warning(f"Could not fetch available formats: {e}")
            available_formats = None
        
        # Save video info
        saved_video_id = Video.create_video_info(
            user_id, url, start_time, end_time,
            additional_message=message,
            clip_offset=offset,
            available_formats=available_formats
        )
        
        if not saved_video_id:
            return jsonify({'error': 'Failed to save video clip'}), 500
        
        logger.info(f"Stream clip saved: {saved_video_id} from video {video_id}")
        
        return jsonify({
            'message': 'Video clip saved successfully',
            'video_id': saved_video_id,
            'youtube_video_id': video_id
        }), 201
        
    except Exception as e:
        logger.error(f"Save stream clip error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/download/<video_id>', methods=['POST'])
@require_private_token
def download_video(video_id):
    """
    Download video segment with optional format and resolution preferences.
    Requires private authentication token.
    
    Request body (optional):
        {
            "format_preference": "mp4|webm|best",
            "resolution_preference": "1080p|720p|best"
        }
    
    Returns:
        File download or processing status
    """
    try:
        # Get optional preferences from request body
        data = request.get_json() or {}
        format_pref = data.get('format_preference', Config.DEFAULT_VIDEO_FORMAT)
        resolution_pref = data.get('resolution_preference', Config.DEFAULT_VIDEO_RESOLUTION)
        
        # Validate preferences if provided
        if format_pref != Config.DEFAULT_VIDEO_FORMAT:
            is_valid, error = validate_format_preference(format_pref)
            if not is_valid:
                return jsonify({'error': error}), 400
        
        if resolution_pref != Config.DEFAULT_VIDEO_RESOLUTION:
            is_valid, error = validate_resolution_preference(resolution_pref)
            if not is_valid:
                return jsonify({'error': error}), 400
        
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
        
        # Start download using data layer with format/resolution preferences
        success, file_path, error = VideoData.download_video(
            video_id,
            format_preference=format_pref,
            resolution_preference=resolution_pref
        )
        
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
    Get video processing status with real-time progress from cache.
    Requires private authentication token.
    
    Returns:
        {
            "status": "pending|processing|completed|failed",
            "progress": {
                "download_progress": 0-100,      // When downloading
                "encoding_progress": 0-100,      // When encoding
                "current_phase": "downloading|encoding|initializing",
                "speed": "2.3x",
                "eta": "03:24",
                "fps": 45.2
            },
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
        
        response = {
            'video_id': video_id,
            'status': video['status'],
            'url': video['url'],
            'start_time': video['start_time'],
            'end_time': video['end_time'],
            'created_at': video['created_at'].isoformat(),
            'file_available': video.get('file_path') is not None and os.path.exists(video.get('file_path', '')),
            'error_message': video.get('error_message'),
            'available_formats': video.get('available_formats')  # Include available formats
        }
        
        # Add progress information if processing (read from cache)
        if video['status'] == VideoStatus.PROCESSING:
            from src.services.progress_cache import ProgressCache
            progress_data = ProgressCache.get_progress(video_id)
            
            if progress_data:
                response['progress'] = progress_data
            else:
                # No cache data yet, return minimal progress
                response['progress'] = {
                    'current_phase': 'initializing'
                }
        
        return jsonify(response), 200
        
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
        
        logger.error(f"List videos error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/formats/<video_id>', methods=['GET'])
@require_private_token
def get_available_formats(video_id):
    """
    Get available formats and resolutions for a video.
    Requires private authentication token.
    
    Args:
        video_id: Can be either a video document ID or YouTube video ID
    
    Returns:
        {
            "video_id": "...",
            "resolutions": ["1080p", "720p", ...],
            "extensions": ["mp4", "webm", ...],
            "formats": {...}
        }
    """
    try:
        #First check if it's a video document ID
        video = Video.find_by_id(video_id)
        
        if video:
            # Verify ownership
            if not Video.verify_ownership(video_id, g.user_id):
                return jsonify({'error': 'Unauthorized access to video'}), 403
            
            # Extract YouTube video ID from URL
            yt_video_id = YouTubeService.parse_video_id_from_url(video['url'])
            if not yt_video_id:
                return jsonify({'error': 'Could not extract YouTube video ID from URL'}), 400
        else:
            # Assume it's a YouTube video ID
            is_valid, error = validate_video_id(video_id)
            if not is_valid:
                return jsonify({'error': error}), 400
            yt_video_id = video_id
        
        # Get available formats using YouTube service
        formats_info = YouTubeService.get_available_formats(yt_video_id)
        
        if not formats_info:
            return jsonify({'error': 'Failed to retrieve available formats'}), 500
        
        logger.info(f"Retrieved available formats for video {yt_video_id}")
        return jsonify(formats_info), 200
        
    except Exception as e:
        logger.error(f"Get available formats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@video_bp.route('/resolutions', methods=['POST'])
def get_available_resolutions():
    """
    Get available resolutions for a YouTube video URL.
    Public endpoint - no authentication required.
    
    Request body:
        {
            "url": "https://youtube.com/watch?v=..."
        }
    
    Returns:
        {
            "video_id": "dQw4w9WgXcQ",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "resolutions": ["1440p", "1080p", "720p"]
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400
        
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate YouTube URL
        is_valid_url, url_error = validate_youtube_url(url)
        if not is_valid_url:
            return jsonify({'error': url_error}), 400
        
        # Parse video ID from URL
        video_id = YouTubeService.parse_video_id_from_url(url)
        if not video_id:
            return jsonify({'error': 'Could not extract YouTube video ID from URL'}), 400
        
        # Get available formats
        resolutions = YouTubeService.get_available_formats(video_id)
        
        if resolutions is None:
            return jsonify({'error': 'Failed to retrieve available resolutions'}), 500
        
        logger.info(f"Retrieved available resolutions for video {video_id}")
        
        return jsonify({
            'video_id': video_id,
            'url': url,
            'resolutions': resolutions if resolutions else []
        }), 200
        
    except Exception as e:
        logger.error(f"Get available resolutions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
