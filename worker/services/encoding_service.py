"""
Encoding service — uses ffmpeg to encode uploaded videos.
Migrated from backend/src/services/encoding_service.py.
Downloads source from S3, encodes, uploads result to S3, cleans up.
"""
import os
import logging
import subprocess
import json
import uuid
from datetime import datetime

from config import Config
from services import progress_service, storage_service, db_service

logger = logging.getLogger(__name__)

# CPU Codec configurations
CPU_CODEC_CONFIGS = {
    'h264': {
        'encoder': 'libx264',
        'quality_presets': {
            'lossless': {'crf': '18', 'preset': 'slow'},
            'high': {'crf': '23', 'preset': 'medium'},
            'medium': {'crf': '28', 'preset': 'fast'}
        }
    },
    'h265': {
        'encoder': 'libx265',
        'quality_presets': {
            'lossless': {'crf': '20', 'preset': 'slow'},
            'high': {'crf': '25', 'preset': 'medium'},
            'medium': {'crf': '30', 'preset': 'fast'}
        }
    },
    'av1': {
        'encoder': 'libsvtav1',
        'quality_presets': {
            'lossless': {'crf': '20', 'preset': '6'},
            'high': {'crf': '23', 'preset': '8'},
            'medium': {'crf': '28', 'preset': '10'}
        }
    }
}


def encode_video(job_data):
    """
    Encode a video file.

    Args:
        job_data: dict with keys:
            - job_id: str
            - video_id: str (MongoDB document ID)
            - s3_input_key: str (S3 key for source file)
            - original_filename: str
            - video_codec: str (h264, h265, av1)
            - quality_preset: str (lossless, high, medium)

    Returns:
        (success: bool, error_message: str or None)
    """
    job_id = job_data['job_id']
    video_id = job_data['video_id']
    s3_input_key = job_data['s3_input_key']
    original_filename = job_data.get('original_filename', 'video')
    video_codec = job_data.get('video_codec', 'h264')
    quality_preset = job_data.get('quality_preset', 'high')

    logger.info(f"[Encode] Starting job {job_id} for video {video_id}: {video_codec}/{quality_preset}")

    # Update status
    db_service.update_video_status(video_id, 'processing')
    progress_service.set_progress(job_id, {
        'status': 'processing',
        'current_phase': 'downloading_source',
        'download_progress': 0,
        'encoding_progress': 0,
    })
    progress_service.set_video_progress(video_id, {
        'status': 'processing',
        'current_phase': 'downloading_source',
        'download_progress': 0,
        'encoding_progress': 0,
    })

    os.makedirs(Config.TEMP_DIR, exist_ok=True)

    # Download source file from S3
    input_ext = os.path.splitext(original_filename)[1] or '.mp4'
    local_input = os.path.join(Config.TEMP_DIR, f"input_{uuid.uuid4().hex}{input_ext}")

    download_ok, download_err = storage_service.download_file(s3_input_key, local_input)
    if not download_ok:
        error = f"Failed to download source: {download_err}"
        logger.error(f"[Encode] {error}")
        return False, error

    logger.info(f"[Encode] Source downloaded to {local_input}")

    try:
        # Get video duration for progress tracking
        duration = _get_video_duration(local_input)

        progress_service.set_progress(job_id, {
            'status': 'processing',
            'current_phase': 'encoding',
            'download_progress': 100,
            'encoding_progress': 0,
        })
        progress_service.set_video_progress(video_id, {
            'status': 'processing',
            'current_phase': 'encoding',
            'download_progress': 100,
            'encoding_progress': 0,
        })

        # Build ffmpeg command
        output_filename = f"encoded_{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.mp4"
        output_path = os.path.join(Config.TEMP_DIR, output_filename)

        codec_config = CPU_CODEC_CONFIGS.get(video_codec, CPU_CODEC_CONFIGS['h264'])
        encoder = codec_config['encoder']
        quality = codec_config['quality_presets'].get(quality_preset, codec_config['quality_presets']['high'])

        cmd = ['ffmpeg', '-y', '-i', local_input]

        if video_codec == 'av1':
            cmd.extend(['-c:v', encoder, '-crf', quality['crf'], '-preset', quality['preset']])
        else:
            cmd.extend(['-c:v', encoder, '-crf', quality['crf'], '-preset', quality['preset']])

        # Audio
        cmd.extend(['-c:a', 'aac', '-b:a', '192k', '-ar', '48000'])

        # Progress output
        cmd.extend(['-progress', 'pipe:1', output_path])

        logger.info(f"[Encode] Running: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        for line in process.stdout:
            if 'out_time_ms=' in line:
                try:
                    time_ms = int(line.split('=')[1].strip())
                    if duration and duration > 0:
                        total_ms = duration * 1_000_000
                        enc_pct = min((time_ms / total_ms) * 100, 100)
                    else:
                        enc_pct = 0

                    progress_service.set_progress(job_id, {
                        'status': 'processing',
                        'current_phase': 'encoding',
                        'download_progress': 100,
                        'encoding_progress': round(enc_pct, 1),
                    })
                    progress_service.set_video_progress(video_id, {
                        'status': 'processing',
                        'current_phase': 'encoding',
                        'download_progress': 100,
                        'encoding_progress': round(enc_pct, 1),
                    })

                    # Also update DB progress
                    db_service.update_encoding_progress(video_id, round(enc_pct, 1))
                except (ValueError, ZeroDivisionError):
                    pass

        process.wait()

        # Clean up source file
        try:
            os.remove(local_input)
        except:
            pass

        if process.returncode != 0:
            stderr = process.stderr.read()
            error = f"ffmpeg exited with code {process.returncode}: {stderr[:500]}"
            logger.error(f"[Encode] {error}")
            return False, error

        if not os.path.exists(output_path):
            return False, "Encoding completed but output file not found"

        file_size = os.path.getsize(output_path)
        logger.info(f"[Encode] Encoded file: {output_path} ({file_size} bytes)")

        # Upload to S3
        progress_service.set_progress(job_id, {
            'status': 'processing',
            'current_phase': 'uploading',
            'download_progress': 100,
            'encoding_progress': 100,
        })

        object_name = f"{Config.S3_KEY_PREFIX}{os.path.basename(output_path)}"
        upload_ok, upload_result = storage_service.upload_file(output_path, object_name)

        # Clean up local file
        try:
            os.remove(output_path)
        except:
            pass

        if not upload_ok:
            return False, f"S3 upload failed: {upload_result}"

        # Delete old S3 source file (for encoding-only jobs where user uploaded)
        storage_service.delete_file(s3_input_key)
        logger.info(f"[Encode] Deleted old source from S3: {s3_input_key}")

        # Update DB
        db_service.update_video_status(
            video_id, 'completed',
            file_path=object_name,
            storage_mode='s3',
            file_size_bytes=file_size,
        )
        db_service.update_encoding_progress(video_id, 100, completed_at=datetime.utcnow())

        progress_service.set_progress(job_id, {
            'status': 'completed',
            'current_phase': 'completed',
            'download_progress': 100,
            'encoding_progress': 100,
        })
        progress_service.set_video_progress(video_id, {
            'status': 'completed',
            'current_phase': 'completed',
            'download_progress': 100,
            'encoding_progress': 100,
        })

        logger.info(f"[Encode] Job {job_id} completed: {object_name}")
        return True, None

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Encode] Job {job_id} failed: {error_msg}")
        # Clean up temp files
        for f in [local_input, locals().get('output_path', '')]:
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except:
                pass
        return False, error_msg


def _get_video_duration(file_path):
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get('format', {}).get('duration', 0))
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")
    return 0
