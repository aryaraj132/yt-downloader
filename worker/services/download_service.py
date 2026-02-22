"""
Download service — uses yt-dlp to download YouTube video segments.
Migrated from backend/src/services/video_service.py with cookie file support.
"""
import os
import sys
import logging
import subprocess
import re
import time
import uuid
from datetime import datetime

from config import Config
from services import progress_service, storage_service, db_service

logger = logging.getLogger(__name__)


def download_video_segment(job_data):
    """
    Download a YouTube video segment using yt-dlp.

    Args:
        job_data: dict with keys:
            - job_id: str
            - video_id: str (MongoDB document ID)
            - url: str
            - start_time: int (seconds)
            - end_time: int (seconds)
            - format_preference: str (mp4, webm, best)
            - resolution_preference: str (1080p, 720p, best, etc.)

    Returns:
        (success: bool, error_message: str or None)
    """
    job_id = job_data['job_id']
    video_id = job_data['video_id']
    url = job_data['url']
    start_time = int(job_data['start_time'])
    end_time = int(job_data['end_time'])
    format_pref = job_data.get('format_preference', 'mp4')
    resolution_pref = job_data.get('resolution_preference', '1080p')

    logger.info(f"[Download] Starting job {job_id} for video {video_id}: {url} [{start_time}-{end_time}]")

    # Update status
    db_service.update_video_status(video_id, 'processing')
    progress_service.set_progress(job_id, {
        'status': 'processing',
        'current_phase': 'downloading',
        'download_progress': 0,
        'encoding_progress': 0,
    })
    progress_service.set_video_progress(video_id, {
        'status': 'processing',
        'current_phase': 'downloading',
        'download_progress': 0,
        'encoding_progress': 0,
    })

    # Prepare output path
    file_ext = format_pref if format_pref != 'best' else 'mp4'
    filename = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.{file_ext}"
    output_path = os.path.join(Config.TEMP_DIR, filename)
    os.makedirs(Config.TEMP_DIR, exist_ok=True)

    try:
        # Build yt-dlp command
        duration = end_time - start_time
        format_string = _build_format_string(resolution_pref, format_pref)

        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--newline',
            '-f', format_string,
            '--download-sections', f'*{start_time}-{end_time}',
            '--force-keyframes-at-cuts',
            '-o', output_path,
            '--merge-output-format', file_ext,
        ]

        # Add cookie file if present
        cookies_path = Config.get_cookies_path()
        if cookies_path:
            cmd.extend(['--cookies', cookies_path])
            logger.info(f"[Download] Using cookies from {cookies_path}")

        cmd.append(url)

        logger.info(f"[Download] Running: {' '.join(cmd)}")

        # Run yt-dlp with progress parsing
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # Parse download progress
            progress_match = re.search(r'(\d+\.?\d*)%', line)
            if progress_match:
                download_pct = float(progress_match.group(1))
                speed_match = re.search(r'at\s+(\S+)', line)
                eta_match = re.search(r'ETA\s+(\S+)', line)

                progress_data = {
                    'status': 'processing',
                    'current_phase': 'downloading',
                    'download_progress': min(download_pct, 100),
                    'encoding_progress': 0,
                }
                if speed_match:
                    progress_data['speed'] = speed_match.group(1)
                if eta_match:
                    progress_data['eta'] = eta_match.group(1)

                progress_service.set_progress(job_id, progress_data)
                progress_service.set_video_progress(video_id, progress_data)

        process.wait()

        if process.returncode != 0:
            error = f"yt-dlp exited with code {process.returncode}"
            logger.error(f"[Download] {error}")
            return False, error

        # Check if file exists
        if not os.path.exists(output_path):
            # yt-dlp might add extension
            possible_files = [f for f in os.listdir(Config.TEMP_DIR) if f.startswith(filename.rsplit('.', 1)[0])]
            if possible_files:
                output_path = os.path.join(Config.TEMP_DIR, possible_files[0])
            else:
                return False, "Download completed but output file not found"

        file_size = os.path.getsize(output_path)
        logger.info(f"[Download] File downloaded: {output_path} ({file_size} bytes)")

        # Check if we need to re-encode (high-res MP4 from WebM)
        needs_encoding = (
            resolution_pref in ['1440p', '2160p', '4320p'] and
            format_pref == 'mp4' and
            output_path.endswith('.webm')
        )

        if needs_encoding:
            logger.info("[Download] High-res MP4 requested, re-encoding from WebM...")
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

            encoded_path = output_path.rsplit('.', 1)[0] + '.mp4'
            encode_cmd = [
                'ffmpeg', '-y', '-i', output_path,
                '-c:v', 'libx265', '-crf', '18', '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '192k',
                '-progress', 'pipe:1',
                encoded_path
            ]

            enc_process = subprocess.Popen(
                encode_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            for line in enc_process.stdout:
                if 'out_time_ms=' in line:
                    try:
                        time_ms = int(line.split('=')[1].strip())
                        total_ms = duration * 1_000_000
                        enc_pct = min((time_ms / total_ms) * 100, 100) if total_ms > 0 else 0
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
                    except (ValueError, ZeroDivisionError):
                        pass

            enc_process.wait()

            # Clean up WebM
            try:
                os.remove(output_path)
            except:
                pass

            if enc_process.returncode != 0:
                stderr = enc_process.stderr.read()
                return False, f"Encoding failed: {stderr[:500]}"

            output_path = encoded_path

        # Upload to S3
        progress_service.set_progress(job_id, {
            'status': 'processing',
            'current_phase': 'uploading',
            'download_progress': 100,
            'encoding_progress': 100,
        })
        progress_service.set_video_progress(video_id, {
            'status': 'processing',
            'current_phase': 'uploading',
            'download_progress': 100,
            'encoding_progress': 100,
        })

        object_name = f"{Config.S3_KEY_PREFIX}{os.path.basename(output_path)}"
        upload_success, upload_result = storage_service.upload_file(output_path, object_name)

        # Clean up local file
        try:
            os.remove(output_path)
        except:
            pass

        if upload_success:
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else file_size
            db_service.update_video_status(
                video_id, 'completed',
                file_path=object_name,
                storage_mode='s3',
                file_size_bytes=file_size,
            )
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
            logger.info(f"[Download] Job {job_id} completed: {object_name}")
            return True, None
        else:
            return False, f"S3 upload failed: {upload_result}"

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Download] Job {job_id} failed: {error_msg}")
        return False, error_msg


def _build_format_string(resolution, format_ext):
    """Build yt-dlp format selection string."""
    if resolution == 'best':
        if format_ext == 'mp4':
            return 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
        elif format_ext == 'webm':
            return 'bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/bv*+ba/b'
        else:
            return 'bv*+ba/b'

    # Extract height from resolution string
    height = resolution.replace('p', '')
    try:
        height = int(height)
    except ValueError:
        height = 1080

    if format_ext == 'mp4':
        return f'bv*[height<={height}][ext=mp4]+ba[ext=m4a]/bv*[height<={height}]+ba/b[height<={height}]'
    elif format_ext == 'webm':
        return f'bv*[height<={height}][ext=webm]+ba[ext=webm]/bv*[height<={height}]+ba/b[height<={height}]'
    else:
        return f'bv*[height<={height}]+ba/b[height<={height}]'
