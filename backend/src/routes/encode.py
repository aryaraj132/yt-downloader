"""Video encoding routes for uploading and converting videos to MP4."""
import logging
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.utils import secure_filename

from src.models.video import Video, VideoStatus
from src.services.encoding_service import EncodingService
from src.middleware.auth import require_private_token
from src.config import Config

logger = logging.getLogger(__name__)

encode_bp = Blueprint('encode', __name__, url_prefix='/api/encode')


def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_VIDEO_FORMATS


@encode_bp.route('/upload', methods=['POST'])
@require_private_token
def upload_video():
    """
    Upload a video file for encoding.
    Requires private authentication token.

    Form data:
        video: Video file (multipart/form-data)

    Returns:
        {
            "message": "Video uploaded successfully",
            "encode_id": "...",
            "original_filename": "..."
        }
    """
    try:
        # Check if file is present in request
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'Invalid file format. Allowed formats: {", ".join(Config.ALLOWED_VIDEO_FORMATS)}'
            }), 400

        # Secure the filename and generate unique name
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}_{original_filename}"
        upload_path = os.path.join(Config.UPLOADS_DIR, unique_filename)

        # Ensure uploads directory exists
        os.makedirs(Config.UPLOADS_DIR, exist_ok=True)

        # Save the file
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)

        # Check file size
        max_size_bytes = Config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            os.remove(upload_path)  # Clean up
            return jsonify({
                'error': f'File too large. Maximum size: {Config.MAX_UPLOAD_SIZE_MB}MB'
            }), 400

        logger.info(f"File uploaded: {original_filename} ({file_size} bytes)")

        # Validate it's actually a video file
        is_valid, error = EncodingService.validate_video_file(upload_path)
        if not is_valid:
            os.remove(upload_path)  # Clean up
            return jsonify({'error': f'Invalid video file: {error}'}), 400

        # Get video metadata
        metadata = EncodingService.get_video_metadata(upload_path)

        # Create encode request in database
        encode_id = Video.create_encode_request(
            user_id=g.user_id,
            original_filename=original_filename,
            input_file_path=upload_path
        )

        if not encode_id:
            os.remove(upload_path)  # Clean up
            return jsonify({'error': 'Failed to create encode request'}), 500

        logger.info(f"Encode request created: {encode_id}")

        response_data = {
            'message': 'Video uploaded successfully',
            'encode_id': encode_id,
            'original_filename': original_filename,
            'file_size_mb': round(file_size / (1024 * 1024), 2)
        }

        if metadata:
            response_data['metadata'] = {
                'duration': metadata.get('duration'),
                'resolution': f"{metadata.get('width')}x{metadata.get('height')}" if metadata.get('width') else None,
                'original_codec': metadata.get('video_codec')
            }

        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@encode_bp.route('/start/<encode_id>', methods=['POST'])
@require_private_token
def start_encoding(encode_id):
    """
    Start encoding a video with specified options.
    Requires private authentication token.

    Request body:
        {
            "video_codec": "h264|h265|av1",
            "quality_preset": "lossless|high|medium"
        }

    Returns:
        {
            "message": "Encoding started",
            "encode_id": "..."
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        video_codec = data.get('video_codec', 'h264')
        quality_preset = data.get('quality_preset', 'high')

        # Validate codec and preset
        supported_codecs = EncodingService.get_supported_codecs()
        if video_codec not in supported_codecs:
            return jsonify({
                'error': f'Invalid codec. Supported: {", ".join(supported_codecs.keys())}'
            }), 400

        if quality_preset not in supported_codecs[video_codec]:
            return jsonify({
                'error': f'Invalid quality preset. Supported: {", ".join(supported_codecs[video_codec])}'
            }), 400

        # Get encode request
        encode_request = Video.find_by_id(encode_id)

        if not encode_request:
            return jsonify({'error': 'Encode request not found'}), 404

        # Verify ownership
        if not Video.verify_ownership(encode_id, g.user_id):
            return jsonify({'error': 'Unauthorized access to encode request'}), 403

        # Check if already processing or completed
        if encode_request['status'] == VideoStatus.PROCESSING:
            return jsonify({
                'message': 'Video is currently being encoded',
                'status': 'processing'
            }), 202

        if encode_request['status'] == VideoStatus.COMPLETED:
            return jsonify({
                'message': 'Video already encoded',
                'status': 'completed'
            }), 200

        # Update codec and quality settings
        from src.services.db_service import get_database
        from bson import ObjectId
        db = get_database()
        db.videos.update_one(
            {'_id': ObjectId(encode_id)},
            {'$set': {
                'video_codec': video_codec,
                'quality_preset': quality_preset,
                'encoding_started_at': datetime.utcnow()
            }}
        )

        # Generate output path
        output_filename = f"encoded_{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.mp4"
        output_path = os.path.join(Config.DOWNLOADS_DIR, output_filename)

        # Start encoding
        input_path = encode_request['input_file_path']
        success, error = EncodingService.encode_video_to_mp4(
            input_path=input_path,
            output_path=output_path,
            video_codec=video_codec,
            quality_preset=quality_preset,
            encode_id=encode_id
        )

        if not success:
            Video.update_status(encode_id, VideoStatus.FAILED, error_message=error)
            return jsonify({
                'error': 'Encoding failed',
                'message': error
            }), 500

        # Update status to completed
        from datetime import timedelta
        db.videos.update_one(
            {'_id': ObjectId(encode_id)},
            {'$set': {
                'encoding_completed_at': datetime.utcnow(),
                'encoding_progress': 100
            }}
        )

        # Upload to SeaweedFS
        from src.services.storage_service import StorageService
        object_name = f"{Config.S3_KEY_PREFIX}{os.path.basename(output_path)}"
        logger.info(f"Uploading encoded video to SeaweedFS: {object_name}")

        upload_success, upload_result = StorageService.upload_file(output_path, object_name)

        if upload_success:
            Video.update_status(
                encode_id,
                VideoStatus.COMPLETED,
                file_path=object_name,
                storage_mode='s3'
            )
            # Delete local file
            try:
                os.remove(output_path)
                logger.info(f"Removed local encoded file: {output_path}")
            except Exception as e:
                logger.warning(f"Failed to remove local file: {e}")

            # Also set response file_size (we used os.path.getsize before upload/delete)
            # We already calculated file_size before upload
        else:
            logger.error(f"S3 upload failed: {upload_result}, keeping file local")
            Video.update_status(
                encode_id,
                VideoStatus.COMPLETED,
                file_path=output_path,
                storage_mode='local'
            )

        # Get file size (if local file exists, get size, otherwise it was uploaded and we might have missed it if we deleted it)
        # Wait, I need file size before deleting.
        # I can just assume file_size is correct from the line 234 in original code which is executed before this block?
        # In original code:
        # file_size = os.path.getsize(output_path)
        # db.videos.update_one(..., {'$set': {'file_size_bytes': file_size}})

        # So I need to keep that logic or ensure it's done.
        # The replacement modifies from line 223.
        # Original lines 233-238 handled file size.

        # Let's verify context.
        # Original:
        # 222:         # Update status to completed
        # ...
        # 231:         Video.update_status(encode_id, VideoStatus.COMPLETED, file_path=output_path)
        # 232:
        # 233:         # Get file size
        # 234:         file_size = os.path.getsize(output_path)
        # 235:         db.videos.update_one(
        # 236:             {'_id': ObjectId(encode_id)},
        # 237:             {'$set': {'file_size_bytes': file_size}}
        # 238:         )

        # So I should do getsize BEFORE upload/delete.

        file_size = os.path.getsize(output_path)
        db.videos.update_one(
            {'_id': ObjectId(encode_id)},
            {'$set': {'file_size_bytes': file_size}}
        )

        logger.info(f"Encoding completed: {encode_id}")

        return jsonify({
            'message': 'Video encoded successfully',
            'encode_id': encode_id,
            'file_size_mb': round(file_size / (1024 * 1024), 2)
        }), 200

    except Exception as e:
        logger.error(f"Start encoding error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@encode_bp.route('/status/<encode_id>', methods=['GET'])
@require_private_token
def get_encoding_status(encode_id):
    """
    Get encoding status and progress.
    Requires private authentication token.

    Returns:
        {
            "encode_id": "...",
            "status": "pending|processing|completed|failed",
            "progress": 0-100,
            "original_filename": "...",
            "codec": "...",
            "quality": "...",
            "file_available": true|false
        }
    """
    try:
        encode_request = Video.find_by_id(encode_id)

        if not encode_request:
            return jsonify({'error': 'Encode request not found'}), 404

        # Verify ownership
        if not Video.verify_ownership(encode_id, g.user_id):
            return jsonify({'error': 'Unauthorized access to encode request'}), 403

        response = {
            'encode_id': encode_id,
            'status': encode_request['status'],
            'progress': encode_request.get('encoding_progress', 0),
            'original_filename': encode_request.get('original_filename'),
            'video_codec': encode_request.get('video_codec'),
            'quality_preset': encode_request.get('quality_preset'),
            'created_at': encode_request['created_at'].isoformat(),
            'file_available': encode_request.get('file_path') is not None and os.path.exists(encode_request.get('file_path', ''))
        }

        if encode_request.get('file_size_bytes'):
            response['file_size_mb'] = round(encode_request['file_size_bytes'] / (1024 * 1024), 2)

        if encode_request.get('error_message'):
            response['error_message'] = encode_request['error_message']

        if encode_request.get('encoding_started_at'):
            response['encoding_started_at'] = encode_request['encoding_started_at'].isoformat()

        if encode_request.get('encoding_completed_at'):
            response['encoding_completed_at'] = encode_request['encoding_completed_at'].isoformat()
            duration = encode_request['encoding_completed_at'] - encode_request['encoding_started_at']
            response['encoding_duration_seconds'] = int(duration.total_seconds())

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Get encoding status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@encode_bp.route('/download/<encode_id>', methods=['POST'])
@require_private_token
def download_encoded_video(encode_id):
    """
    Download encoded video file.
    Requires private authentication token.

    Returns:
        File download or error message
    """
    try:
        encode_request = Video.find_by_id(encode_id)

        if not encode_request:
            return jsonify({'error': 'Encode request not found'}), 404

        # Verify ownership
        if not Video.verify_ownership(encode_id, g.user_id):
            return jsonify({'error': 'Unauthorized access to encode request'}), 403

        # Check status
        if encode_request['status'] == VideoStatus.PROCESSING:
            return jsonify({
                'message': 'Video is still being encoded',
                'progress': encode_request.get('encoding_progress', 0)
            }), 202

        if encode_request['status'] == VideoStatus.FAILED:
            return jsonify({
                'error': 'Encoding failed',
                'message': encode_request.get('error_message', 'Unknown error')
            }), 500

        if encode_request['status'] != VideoStatus.COMPLETED:
            return jsonify({'error': 'Video not yet encoded'}), 400

        file_path = encode_request.get('file_path')

        if not file_path:
             return jsonify({'error': 'Encoded file path missing'}), 404

        # Check storage mode
        storage_mode = encode_request.get('storage_mode', 'local')

        if storage_mode == 's3':
             from src.services.storage_service import StorageService
             # We can generate a presigned URL or just a public URL depending on bucket policy.
             # User requested: "send the downloadable link to the frontend and frontend can redirect to that link"
             # Since this is a POST request, a 302 redirect might not work well for AJAX/fetch if it's expecting JSON.
             # However, browser form submit works with 302.
             # If sending JSON:
             url = f"{Config.S3_ENDPOINT_URL}/{Config.S3_BUCKET_NAME}/{file_path}"
             # Or use presigned if needed
             # url = StorageService.get_presigned_url(file_path)

             logger.info(f"Redirecting to S3 for encoded video: {encode_id}")
             # Returning JSON with 'download_url' so frontend can handle it
             return jsonify({
                 'message': 'Download link generated',
                 'download_url': url
             }), 200

        if not os.path.exists(file_path):
            return jsonify({'error': 'Encoded file not found locally'}), 404

        # Generate download filename
        original_name = encode_request.get('original_filename', 'video')
        name_without_ext = os.path.splitext(original_name)[0]
        codec = encode_request.get('video_codec', 'h264')
        quality = encode_request.get('quality_preset', 'high')
        download_name = f"{name_without_ext}_{codec}_{quality}.mp4"

        logger.info(f"Serving encoded video: {encode_id}")

        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        logger.error(f"Download encoded video error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@encode_bp.route('/codecs', methods=['GET'])
def get_supported_codecs():
    """
    Get list of supported codecs and quality presets.
    No authentication required.

    Returns:
        {
            "codecs": {
                "h264": ["lossless", "high", "medium"],
                "h265": ["lossless", "high", "medium"],
                "av1": ["lossless", "high", "medium"]
            }
        }
    """
    try:
        codecs = EncodingService.get_supported_codecs()
        return jsonify({'codecs': codecs}), 200
    except Exception as e:
        logger.error(f"Get codecs error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
