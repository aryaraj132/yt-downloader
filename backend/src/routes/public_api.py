"""
Public API routes for video clipping and encoding without authentication.
Rate limited by IP + browser fingerprint.
NO DATABASE STORAGE - processes requests directly and cleans up after.
"""
import logging
import os
import uuid
import threading
from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.utils import secure_filename

from src.middleware.auth import require_public_rate_limit
from src.services.rate_limiter_service import RateLimiterService
from src.services.validation_service import ValidationService
from src.services.video_service import VideoService
from src.services.encoding_service import EncodingService
from src.services.storage_service import StorageService
from src.services.progress_cache import ProgressCache
from src.config import Config

logger = logging.getLogger(__name__)

public_api_bp = Blueprint('public_api', __name__, url_prefix='/api/public')


@public_api_bp.route('/clip', methods=['POST'])
@require_public_rate_limit
def download_public_clip():
    """
    Download video clip directly (public endpoint - no DB storage).
    Rate limited to PUBLIC_API_RATE_LIMIT operations per day.
    Max clip duration: PUBLIC_API_MAX_CLIP_DURATION seconds.

    Request body:
        {
            "url": "https://youtube.com/watch?v=...",
            "start_time": 10,
            "end_time": 45,
            "cookies": "..." (optional),
            "format": "mp4" (optional),
            "resolution": "720p" (optional)
        }

    Returns:
        Video file as binary download or job ID for async processing
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or 'url' not in data or 'start_time' not in data or 'end_time' not in data:
            return jsonify({'error': 'Missing required fields: url, start_time, end_time'}), 400

        url = data['url']
        start_time = int(data['start_time'])
        end_time = int(data['end_time'])
        cookies = data.get('cookies')
        format_pref = data.get('format', 'mp4')
        resolution_pref = data.get('resolution', 'best')

        # Validate YouTube URL
        is_valid_url, url_error = ValidationService.validate_youtube_url(url)
        if not is_valid_url:
            return jsonify({'error': url_error}), 400

        # Validate clip duration for public API
        is_valid_duration, duration_error = ValidationService.validate_clip_duration(
            start_time, end_time, is_public=True
        )
        if not is_valid_duration:
            return jsonify({'error': duration_error}), 400

        # Increment rate limit counter BEFORE processing
        RateLimiterService.increment_usage(
            g.client_id,
            'clip',
            g.client_ip,
            g.client_fingerprint
        )

        # Generate temporary job ID for progress tracking
        job_id = f"public_clip_{uuid.uuid4().hex}"

        # Store job info in Redis temporarily (30 minutes TTL)
        ProgressCache.set_progress(job_id, {
            'status': 'processing',
            'current_phase': 'initializing',
            'progress': 0
        }, ttl=1800)

        # Process video download in background thread
        def process_clip():
            try:
                # Update progress
                ProgressCache.set_progress(job_id, {
                    'status': 'processing',
                    'current_phase': 'downloading',
                    'progress': 10
                }, ttl=1800)

                # Download video segment (creates temp file)
                from src.services.youtube_service import YouTubeService

                # Create temporary download directory
                temp_dir = os.path.join(Config.DOWNLOADS_DIR, 'public_temp')
                os.makedirs(temp_dir, exist_ok=True)

                output_file = os.path.join(temp_dir, f"{job_id}.mp4")

                # Use yt-dlp to download segment
                success = YouTubeService.download_segment(
                    url=url,
                    start_time=start_time,
                    end_time=end_time,
                    output_path=output_file,
                    cookies=cookies,
                    format_preference=format_pref,
                    resolution_preference=resolution_pref,
                    progress_callback=lambda p: ProgressCache.set_progress(job_id, {
                        'status': 'processing',
                        'current_phase': 'downloading',
                        'progress': 10 + int(p.get('percent', 0) * 0.9)
                    }, ttl=1800)
                )

                if success and os.path.exists(output_file):
                    # Upload to SeaweedFS
                    s3_key = f"public/clips/{job_id}.mp4"
                    success_upload, upload_result = StorageService.upload_file(output_file, object_name=s3_key)

                    if success_upload:
                        # Clean up local file immediately
                        try:
                            os.remove(output_file)
                        except:
                            pass

                        # Mark as complete with S3 path
                        ProgressCache.set_progress(job_id, {
                            'status': 'completed',
                            'current_phase': 'completed',
                            'progress': 100,
                            'storage_path': upload_result,
                            'storage_mode': 's3',
                            'file_ready': True
                        }, ttl=1800)
                    else:
                        raise Exception(f"Upload to storage failed: {upload_result}")
                else:
                    raise Exception("Download failed")

            except Exception as e:
                logger.error(f"Public clip processing error: {str(e)}")
                ProgressCache.set_progress(job_id, {
                    'status': 'failed',
                    'current_phase': 'failed',
                    'progress': 0,
                    'error': str(e)
                }, ttl=300)

        # Start background processing
        thread = threading.Thread(target=process_clip)
        thread.daemon = True
        thread.start()

        # Get updated rate limit info
        remaining = RateLimiterService.get_remaining(g.client_id)

        return jsonify({
            'job_id': job_id,
            'message': 'Clip processing started',
            'status_url': f'/api/public/status/{job_id}',
            'download_url': f'/api/public/download/{job_id}',
            'rate_limit': {
                'remaining': remaining,
                'limit': Config.PUBLIC_API_RATE_LIMIT,
                'reset_at': g.rate_limit_reset.isoformat()
            }
        }), 202  # 202 Accepted

    except ValueError:
        return jsonify({'error': 'Invalid time values'}), 400
    except Exception as e:
        logger.error(f"Error in download_public_clip: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500


@public_api_bp.route('/encode', methods=['POST'])
@require_public_rate_limit
def encode_public_video():
    """
    Upload and encode video directly (public endpoint - no DB storage).
    Rate limited to PUBLIC_API_RATE_LIMIT operations per day.
    Max video duration: PUBLIC_API_MAX_ENCODE_DURATION seconds (5 minutes).

    Form data:
        - video: File upload
        - video_codec: "h264" | "h265" | "av1"
        - quality_preset: "lossless" | "high" | "medium"
        - duration: Client-provided duration in seconds (for pre-validation)

    Returns:
        Job ID for async processing
    """
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        video_file = request.files['video']

        if video_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Get form parameters
        video_codec = request.form.get('video_codec', 'h264')
        quality_preset = request.form.get('quality_preset', 'high')
        client_duration = request.form.get('duration')

        # Validate codec and quality
        valid_codecs = ['h264', 'h265', 'av1']
        valid_presets = ['lossless', 'high', 'medium']

        if video_codec not in valid_codecs:
            return jsonify({'error': f'Invalid codec. Must be one of: {", ".join(valid_codecs)}'}), 400

        if quality_preset not in valid_presets:
            return jsonify({'error': f'Invalid quality preset. Must be one of: {", ".join(valid_presets)}'}), 400

        # Validate client-provided duration (pre-check)
        if client_duration:
            try:
                duration_seconds = float(client_duration)
                is_valid, error = ValidationService.validate_upload_duration(duration_seconds, is_public=True)
                if not is_valid:
                    return jsonify({'error': error}), 400
            except ValueError:
                logger.warning("Invalid duration format from client")

        # Check file extension
        allowed_extensions = Config.ALLOWED_VIDEO_FORMATS
        file_ext = video_file.filename.rsplit('.', 1)[1].lower() if '.' in video_file.filename else ''

        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file format. Allowed: {", ".join(allowed_extensions)}'}), 400

        # Save uploaded file temporarily
        filename = secure_filename(video_file.filename)
        temp_dir = os.path.join(Config.UPLOADS_DIR, 'public_temp')
        os.makedirs(temp_dir, exist_ok=True)

        job_id = f"public_encode_{uuid.uuid4().hex}"
        input_path = os.path.join(temp_dir, f"{job_id}_input.{file_ext}")
        output_path = os.path.join(temp_dir, f"{job_id}_output.mp4")

        video_file.save(input_path)
        logger.info(f"Saved uploaded file: {input_path}")

        # Validate video file
        is_valid, error_msg = EncodingService.validate_video_file(input_path)
        if not is_valid:
            os.remove(input_path)
            return jsonify({'error': error_msg}), 400

        # Get actual video metadata and validate duration
        metadata = EncodingService.get_video_metadata(input_path)
        if not metadata:
            os.remove(input_path)
            return jsonify({'error': 'Could not read video metadata'}), 400

        actual_duration = metadata.get('duration', 0)
        is_valid_duration, duration_error = ValidationService.validate_upload_duration(
            actual_duration, is_public=True
        )

        if not is_valid_duration:
            os.remove(input_path)
            return jsonify({'error': duration_error}), 400

        # Increment rate limit counter BEFORE processing
        RateLimiterService.increment_usage(
            g.client_id,
            'encode',
            g.client_ip,
            g.client_fingerprint
        )

        # Store job info in Redis temporarily
        ProgressCache.set_progress(job_id, {
            'status': 'processing',
            'current_phase': 'initializing',
            'progress': 0,
            'original_filename': filename
        }, ttl=3600)  # 1 hour TTL

        # Start encoding in background
        def process_encode():
            try:
                success, error = EncodingService.encode_video_to_mp4(
                    input_path=input_path,
                    output_path=output_path,
                    video_codec=video_codec,
                    quality_preset=quality_preset,
                    use_gpu=True,
                    encode_id=job_id,  # For progress tracking
                    progress_callback=None
                )

                if success and os.path.exists(output_path):
                    # Upload to SeaweedFS
                    s3_key = f"public/encodes/{job_id}.mp4"
                    success_upload, upload_result = StorageService.upload_file(output_path, object_name=s3_key)

                    # Clean up input file
                    try:
                        os.remove(input_path)
                    except:
                        pass

                    if success_upload:
                        # Clean up output file
                        try:
                            os.remove(output_path)
                        except:
                            pass

                        # Mark as complete
                        ProgressCache.set_progress(job_id, {
                            'status': 'completed',
                            'current_phase': 'completed',
                            'progress': 100,
                            'storage_path': upload_result,
                            'storage_mode': 's3',
                            'file_ready': True,
                            'original_filename': filename
                        }, ttl=3600)
                    else:
                        raise Exception(f"Upload failed: {upload_result}")

                else:
                    raise Exception(error or "Encoding failed")

            except Exception as e:
                logger.error(f"Public encode processing error: {str(e)}")
                # Clean up files
                for path in [input_path, output_path]:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except:
                        pass

                ProgressCache.set_progress(job_id, {
                    'status': 'failed',
                    'current_phase': 'failed',
                    'progress': 0,
                    'error': str(e)
                }, ttl=300)

        thread = threading.Thread(target=process_encode)
        thread.daemon = True
        thread.start()

        # Get updated rate limit info
        remaining = RateLimiterService.get_remaining(g.client_id)

        return jsonify({
            'job_id': job_id,
            'message': 'Video uploaded successfully. Encoding started...',
            'status_url': f'/api/public/status/{job_id}',
            'download_url': f'/api/public/download/{job_id}',
            'rate_limit': {
                'remaining': remaining,
                'limit': Config.PUBLIC_API_RATE_LIMIT,
                'reset_at': g.rate_limit_reset.isoformat()
            }
        }), 202  # 202 Accepted

    except Exception as e:
        logger.error(f"Error in encode_public_video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500


@public_api_bp.route('/status/<job_id>', methods=['GET'])
def get_public_job_status(job_id):
    """
    Get status of public job (no authentication required).
    Checks Redis cache only - no database.
    """
    try:
        progress_data = ProgressCache.get_progress(job_id)

        if not progress_data:
            return jsonify({'error': 'Job not found or expired'}), 404

        response = {
            'job_id': job_id,
            'status': progress_data.get('status', 'unknown'),
            'progress': progress_data.get('progress', 0),
            'current_phase': progress_data.get('current_phase', 'unknown'),
            'file_ready': progress_data.get('file_ready', False)
        }

        if 'error' in progress_data:
            response['error_message'] = progress_data['error']

        if 'original_filename' in progress_data:
            response['original_filename'] = progress_data['original_filename']

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@public_api_bp.route('/download/<job_id>', methods=['GET'])
def download_public_file(job_id):
    """
    Download processed file (no authentication required).
    File is automatically deleted after download.
    """
    try:
        progress_data = ProgressCache.get_progress(job_id)

        if not progress_data:
            return jsonify({'error': 'Job not found or expired'}), 404

        if progress_data.get('status') != 'completed':
            return jsonify({'error': 'File not ready for download'}), 400

        # Check storage mode
        if progress_data.get('storage_mode') == 's3':
            storage_path = progress_data.get('storage_path')
            if storage_path:
                url = StorageService.get_presigned_url(storage_path, expiration=3600)
                if url:
                    return jsonify({'download_url': url})

        file_path = progress_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Determine download filename
        if 'clip' in job_id:
            download_name = 'clip.mp4'
        else:
            original = progress_data.get('original_filename', 'video.mp4')
            name_without_ext = os.path.splitext(original)[0]
            download_name = f"{name_without_ext}_encoded.mp4"

        # Send file and schedule cleanup
        def cleanup_after_send(file_path, job_id):
            """Delete file and Redis entry after short delay"""
            import time
            time.sleep(2)  # Wait for download to start
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file: {str(e)}")

            # Remove from cache
            ProgressCache.delete_progress(job_id)

        # Schedule cleanup
        cleanup_thread = threading.Thread(target=cleanup_after_send, args=(file_path, job_id))
        cleanup_thread.daemon = True
        cleanup_thread.start()

        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@public_api_bp.route('/rate-limit', methods=['GET'])
@require_public_rate_limit
def get_rate_limit_status():
    """
    Get current rate limit status (requires browser fingerprint header).
    """
    try:
        remaining = RateLimiterService.get_remaining(g.client_id)
        client_info = RateLimiterService.get_client_info(g.client_id)

        used = client_info.get('count', 0) if client_info else 0

        return jsonify({
            'limit': Config.PUBLIC_API_RATE_LIMIT,
            'used': used,
            'remaining': remaining,
            'reset_at': g.rate_limit_reset.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error getting rate limit status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
