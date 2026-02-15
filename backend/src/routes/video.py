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


@video_bp.route('/save/stream/<token>/<chat_id>', methods=['GET', 'POST'])
def save_video_from_stream(token, chat_id):
    """
    Save video clip from live stream based on specific chat message ID.
    Designed for Nightbot and public API usage.

    URL Parameters:
        token: User's public API token
        chat_id: YouTube chat message ID (from Nightbot $(chatid))

    Query Parameters:
        offset: Seconds to capture before chat message (default: 30)
        duration: Total clip duration in seconds (default: 60, max: 120)

    Returns:
        {
            "message": "Clip saved successfully",
            "video_id": "...",
            "clip_start": seconds,
            "clip_end": seconds
        }
    """
    try:
        # Get user from public token
        user = User.find_by_public_token(token)

        if not user:
            return jsonify({'error': 'Invalid or missing public token'}), 401

        user_id = str(user['_id'])

        # Get query parameters
        try:
            offset = int(request.args.get('offset', 30))
            duration = int(request.args.get('duration', 60))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid offset or duration values'}), 400

        # Validate duration
        if duration > Config.MAX_VIDEO_DURATION:
            return jsonify({'error': f'Duration exceeds maximum of {Config.MAX_VIDEO_DURATION} seconds'}), 400

        # Use server-side API Key for reliability
        api_key = Config.YOUTUBE_API_KEY

        if not api_key:
            return jsonify({'error': 'YouTube API Key not configured on server.'}), 500

        # Get chat message details by ID
        from src.services.youtube_api_service import YouTubeAPIService

        # Use API Key for all data fetching
        chat_msg = YouTubeAPIService.get_chat_message_by_id(
            chat_id,
            api_key=api_key
        )

        if not chat_msg:
            return jsonify({'error': 'Chat message not found'}), 404

        # Get video ID from the live chat ID in the message
        live_chat_id = chat_msg.get('live_chat_id')

        if not live_chat_id:
            return jsonify({'error': 'Live chat ID not found in message'}), 500

        video_id = YouTubeAPIService.get_video_id_from_live_chat(
            live_chat_id,
            api_key=api_key
        )

        if not video_id:
            return jsonify({'error': 'Could not determine video ID from chat message'}), 500

        # Validate video ID
        is_valid, error = validate_video_id(video_id)
        if not is_valid:
            return jsonify({'error': error}), 400

        # Get stream details from YouTube API
        stream_details = YouTubeAPIService.get_video_stream_details(
            video_id,
            api_key=api_key
        )

        if not stream_details:
            return jsonify({'error': 'Failed to fetch stream details from YouTube'}), 500

        # Check if the chat message is from the user
        # Note: This check requires an OAuth token to know who the "user" is on YouTube.
        # Since we are using API Key only for reliability, we can't verify ownership.
        # We default to False.
        is_user_message = False

        # Calculate clip time
        start_seconds, end_seconds = YouTubeAPIService.calculate_clip_time(
            stream_details['actual_start_time'],
            chat_msg['published_at'],
            offset,
            duration
        )

        # Check if user sent this message
        is_user_msg = YouTubeAPIService.is_user_channel(
            chat_msg['author_channel_id'],
            access_token
        )

        # Construct YouTube URL
        url = YouTubeService.construct_video_url(video_id)

        # Fetch available formats
        try:
            available_formats = YouTubeService.get_available_formats(video_id)
        except Exception as e:
            logger.warning(f"Could not fetch available formats: {e}")
            available_formats = None

        # Save video info with chat metadata
        saved_video_id = Video.create_video_info(
            user_id=user_id,
            url=url,
            start_time=clip_start,
            end_time=clip_end,
            available_formats=available_formats,
            youtube_video_id=video_id,
            chat_id=chat_msg['id'],
            chat_author=chat_msg['author_display_name'],
            chat_author_channel_id=chat_msg['author_channel_id'],
            chat_message=chat_msg['message_text'],
            is_user_message=is_user_msg,
            stream_start_time=stream_start_time,
            chat_timestamp=chat_msg['published_at'],
            public_token=token
        )

        if not saved_video_id:
            return jsonify({'error': 'Failed to save video clip'}), 500

        logger.info(f"Stream clip saved: {saved_video_id} from chat message {chat_id} in {video_id}")

        return jsonify({
            'message': 'Clip saved successfully',
            'video_id': saved_video_id,
            'youtube_video_id': video_id,
            'chat_id': chat_msg['id'],
            'clip_start': clip_start,
            'clip_end': clip_end,
            'chat_author': chat_msg['author_display_name'],
            'chat_message': chat_msg['message_text'],
            'is_your_message': is_user_msg
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
        cookies = data.get('cookies') # Extract cookies from request

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
            storage_mode = video.get('storage_mode', 'local')

            if storage_mode == 's3':
                url = f"{Config.S3_ENDPOINT_URL}/{Config.S3_BUCKET_NAME}/{file_path}"
                logger.info(f"Redirecting to S3 for cached video: {video_id}")
                return jsonify({
                    'message': 'Download link generated',
                    'download_url': url
                }), 200

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
            resolution_preference=resolution_pref,
            cookies_content=cookies
        )

        if not success:
            return jsonify({
                'error': 'Failed to download video',
                'message': error
            }), 500

        # Check if it was uploaded to S3 (file_path will be object name, not full path)
        # We need to re-fetch the video or check return path format
        # VideoData.download_video returns file_path which is object name if S3, or absolute path if local

        # Ideally we check the video storage_mode again
        video = Video.find_by_id(video_id)
        storage_mode = video.get('storage_mode', 'local')

        if storage_mode == 's3':
            url = f"{Config.S3_ENDPOINT_URL}/{Config.S3_BUCKET_NAME}/{file_path}"
            logger.info(f"Redirecting to S3 for downloaded video: {video_id}")
            return jsonify({
                'message': 'Download link generated',
                'download_url': url
            }), 200

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

        # specific check for file availability
        file_path = video.get('file_path')
        file_available = False
        if file_path:
            if video.get('storage_mode') == 's3':
                file_available = True
            elif os.path.exists(file_path):
                file_available = True

        response = {
            'video_id': video_id,
            'status': video['status'],
            'url': video['url'],
            'start_time': video['start_time'],
            'end_time': video['end_time'],
            'created_at': video['created_at'].isoformat(),
            'file_available': file_available,
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
    List all videos for the authenticated user with pagination support.
    Requires private authentication token.

    Query Parameters:
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)

    Returns:
        {
            "videos": [...],
            "pagination": {
                "page": 1,
                "limit": 20,
                "total": 150,
                "has_more": true
            }
        }
    """
    try:
        # Get pagination parameters
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 20))))
        skip = (page - 1) * limit

        db = get_database()

        # Get total count
        total = db.videos.count_documents({'user_id': ObjectId(g.user_id)})

        # Get paginated videos
        videos = list(db.videos.find(
            {'user_id': ObjectId(g.user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

        # Get user info for clipper details
        from src.models.user import User
        user = User.find_by_id(g.user_id)
        clipper_name = user.get('email', 'Unknown') if user else 'Unknown'

        video_list = []
        for video in videos:
            file_path = video.get('file_path')
            file_available = False
            if file_path:
                if video.get('storage_mode') == 's3':
                    file_available = True
                elif os.path.exists(file_path):
                    file_available = True

            video_list.append({
                'video_id': str(video['_id']),
                'url': video['url'],
                'start_time': video['start_time'],
                'end_time': video['end_time'],
                'status': video['status'],
                'created_at': video['created_at'].isoformat(),
                'file_available': file_available,
                'youtube_video_id': video.get('youtube_video_id'),
                'clipped_by': clipper_name
            })

        has_more = (skip + limit) < total

        return jsonify({
            'videos': video_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'has_more': has_more
            }
        }), 200

    except ValueError as e:
        logger.error(f"Invalid pagination parameters: {str(e)}")
        return jsonify({'error': 'Invalid pagination parameters'}), 400
    except Exception as e:
        logger.error(f"List videos error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500



@video_bp.route('/formats', methods=['POST'])
@require_private_token
def get_available_formats_post():
    """
    Get available formats and resolutions for a video with optional cookies.
    Requires private authentication token.

    Request body:
        {
            "video_id": "...",
            "cookies": "..."
        }

    Returns:
        {
            "video_id": "...",
            "resolutions": [...],
            "extensions": [...],
            "formats": {...}
        }
    """
    try:
        data = request.get_json() or {}
        video_id = data.get('video_id')
        cookies = data.get('cookies')

        if not video_id:
            return jsonify({'error': 'Video ID is required'}), 400

        # First check if it's a video document ID
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
        formats_info = YouTubeService.get_available_formats(yt_video_id, cookies_content=cookies)

        if not formats_info:
            return jsonify({'error': 'Failed to retrieve available formats'}), 500

        logger.info(f"Retrieved available formats for video {yt_video_id}")
        return jsonify(formats_info), 200

    except Exception as e:
        logger.error(f"Get available formats error: {str(e)}")
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
    # ... legacy implementation or redirect ...
    # Reusing the logic via internal call or just duplication for now to avoid breaking changes if any
    # But since frontend is updated, we can just keep this for backward compatibility or remove it.
    # I'll keep it as is, but implemented using the new helper if I refactored.
    # For now, I'll just leave the existing implementation below if I didn't replace it.
    # Wait, I am replacing the existing block. I should preserve the GET route too.

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

        # Get available formats using YouTube service (no cookies)
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


@video_bp.route('/debug/connectivity', methods=['GET'])
def debug_connectivity():
    """Debug endpoint to check backend internet connectivity."""
    import socket
    import requests
    import subprocess

    results = {
        'dns_google': 'failed',
        'http_google': 'failed',
        'http_youtube': 'failed',
        'ytdlp_version': 'failed',
        'external_ip': 'failed'
    }

    # Check 1: External IP
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
        results['external_ip'] = ip
    except Exception as e:
        results['external_ip'] = f"Failed: {str(e)}"

    # Check 2: DNS Resolution
    try:
        ip = socket.gethostbyname('www.google.com')
        results['dns_google'] = f"Success: {ip}"
    except Exception as e:
        results['dns_google'] = f"Failed: {str(e)}"

    # Check 3: Google HTTP
    try:
        resp = requests.get('https://www.google.com', timeout=5)
        results['http_google'] = f"Status: {resp.status_code}"
    except Exception as e:
        results['http_google'] = f"Failed: {str(e)}"

    # Check 4: YouTube HTTP
    try:
        resp = requests.get('https://www.youtube.com', timeout=5)
        results['http_youtube'] = f"Status: {resp.status_code}"
    except Exception as e:
        results['http_youtube'] = f"Failed: {str(e)}"

    # Check 5: yt-dlp version check
    try:
        cmd = ['yt-dlp', '--version']
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if process.returncode == 0:
             results['ytdlp_version'] = process.stdout.strip()
        else:
             results['ytdlp_version'] = f"Failed: {process.stderr}"
    except Exception as e:
        results['ytdlp_version'] = f"Exception: {str(e)}"

    return jsonify(results)
