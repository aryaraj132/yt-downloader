
import os
import logging
import subprocess
import json
import re
import time
from typing import Optional, Tuple, Dict, Callable
from datetime import datetime
from pathlib import Path

from src.config import Config
from src.models.video import Video, VideoStatus
from src.services import ffmpeg_utils_service

logger = logging.getLogger(__name__)

# GPU Encoder configurations
GPU_ENCODER_CONFIGS = {
    'h264': {
        'nvenc': {'encoder': 'h264_nvenc', 'lossless': ['-preset', 'p7', '-cq', '19', '-b:v', '0'], 
                  'high': ['-preset', 'p5', '-cq', '23', '-b:v', '0']},
        'amf': {'encoder': 'h264_amf', 'lossless': ['-quality', 'quality', '-qp_i', '18', '-qp_p', '18'],
                'high': ['-quality', 'balanced', '-qp_i', '23', '-qp_p', '23']},
        'qsv': {'encoder': 'h264_qsv', 'lossless': ['-preset', 'veryslow', '-global_quality', '18'],
                'high': ['-preset', 'medium', '-global_quality', '23']},
    },
    'h265': {
        'nvenc': {'encoder': 'hevc_nvenc', 'lossless': ['-preset', 'p7', '-cq', '20', '-b:v', '0'],
                  'high': ['-preset', 'p5', '-cq', '25', '-b:v', '0']},
        'amf': {'encoder': 'hevc_amf', 'lossless': ['-quality', 'quality', '-qp_i', '20', '-qp_p', '20'],
                'high': ['-quality', 'balanced', '-qp_i', '25', '-qp_p', '25']},
        'qsv': {'encoder': 'hevc_qsv', 'lossless': ['-preset', 'veryslow', '-global_quality', '20'],
                'high': ['-preset', 'medium', '-global_quality', '25']},
    },
    'av1': {
        'nvenc': {'encoder': 'av1_nvenc', 'lossless': ['-cq', '18', '-b:v', '0'],
                  'high': ['-cq', '23', '-b:v', '0']},
        'amf': {'encoder': 'av1_amf', 'lossless': ['-cq', '18', '-b:v', '0'],
                'high': ['-cq', '23', '-b:v', '0']},
        'qsv': {'encoder': 'av1_qsv', 'lossless': ['-cq', '18', '-b:v', '0'],
                'high': ['-cq', '23', '-b:v', '0']},
    }
}

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
            'lossless': {'crf': '18', 'preset': '6'},
            'high': {'crf': '23', 'preset': '8'},
            'medium': {'crf': '28', 'preset': '10'}
        }
    }
}

# Audio encoding configuration
AUDIO_CONFIG = {
    'codec': 'aac',
    'bitrate': '192k',
    'sample_rate': '48000'
}

class EncodingService:
    
    @staticmethod
    def validate_video_file(file_path: str) -> Tuple[bool, Optional[str]]:
        
        if not os.path.exists(file_path):
            return False, "File not found"
        
        ffmpeg_path, _ = ffmpeg_utils_service.get_ffmpeg_path()
        if not ffmpeg_path:
            return False, "FFmpeg not available"
        
        try:
            # Use ffprobe to check if file is a valid video
            ffprobe_path = str(Path(ffmpeg_path).parent / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe'))
            if not os.path.exists(ffprobe_path):
                ffprobe_path = 'ffprobe'
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False, "Invalid video file or unsupported format"
            
            data = json.loads(result.stdout)
            if not data.get('streams'):
                return False, "No video stream found in file"
            
            return True, None
            
        except subprocess.TimeoutExpired:
            return False, "Validation timeout"
        except Exception as e:
            logger.error(f"Video validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def get_video_metadata(file_path: str) -> Optional[Dict]:
        
        ffmpeg_path, _ = ffmpeg_utils_service.get_ffmpeg_path()
        if not ffmpeg_path:
            logger.error("FFmpeg not available")
            return None
        
        try:
            ffprobe_path = str(Path(ffmpeg_path).parent / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe'))
            if not os.path.exists(ffprobe_path):
                ffprobe_path = 'ffprobe'
            
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration,size:stream=codec_name,codec_type,width,height,bit_rate',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                logger.error(f"ffprobe error: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Extract relevant information
            metadata = {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'size_bytes': int(data.get('format', {}).get('size', 0)),
            }
            
            # Find video and audio streams
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    metadata['video_codec'] = stream.get('codec_name')
                    metadata['width'] = stream.get('width')
                    metadata['height'] = stream.get('height')
                    metadata['video_bitrate'] = stream.get('bit_rate')
                elif stream.get('codec_type') == 'audio':
                    metadata['audio_codec'] = stream.get('codec_name')
                    metadata['audio_bitrate'] = stream.get('bit_rate')
            
            return metadata
            
        except Exception as e:
            logger.error(f"Get metadata error: {str(e)}")
            return None
    
    @staticmethod
    def encode_video_to_mp4(
        input_path: str,
        output_path: str,
        video_codec: str = 'h264',
        quality_preset: str = 'high',
        use_gpu: bool = True,
        encode_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> Tuple[bool, Optional[str]]:
        
        try:
            ffmpeg_path, _ = ffmpeg_utils_service.get_ffmpeg_path()
            if not ffmpeg_path:
                return False, "FFmpeg not available"
            
            # Get video duration for progress tracking
            duration = ffmpeg_utils_service.get_video_duration(ffmpeg_path, input_path)
            
            # Try GPU encoding first if requested
            gpu_encoder = None
            gpu_type = None
            if use_gpu:
                gpu_encoder_name, gpu_type = ffmpeg_utils_service.detect_gpu_encoder(ffmpeg_path, video_codec)
                if gpu_encoder_name:
                    # Find GPU config
                    for encoder_type_key in GPU_ENCODER_CONFIGS.get(video_codec, {}).keys():
                        if encoder_type_key in gpu_encoder_name:
                            gpu_encoder = GPU_ENCODER_CONFIGS[video_codec][encoder_type_key]
                            break
            
            # Build encoding command
            if gpu_encoder:
                # GPU encoding
                logger.info(f"Using GPU encoder: {gpu_type} ({gpu_encoder['encoder']})")
                cmd = [
                    ffmpeg_path,
                    '-i', input_path,
                    '-progress', 'pipe:2',
                    '-c:v', gpu_encoder['encoder']
                ] + gpu_encoder.get(quality_preset, gpu_encoder['high']) + [
                    '-c:a', AUDIO_CONFIG['codec'],
                    '-b:a', AUDIO_CONFIG['bitrate'],
                    '-ar', AUDIO_CONFIG['sample_rate'],
                    '-movflags', '+faststart',
                    '-pix_fmt', 'yuv420p',
                    '-y',
                    output_path
                ]
            else:
                # CPU encoding
                if video_codec == 'av1' and not use_gpu:
                    # AV1 without GPU -> fallback to H.265
                    logger.warning("⚠️  AV1 GPU encoder not available, falling back to H.265")
                    video_codec = 'h265'
                
                logger.info(f"Using CPU encoder: {CPU_CODEC_CONFIGS[video_codec]['encoder']}")
                codec_config = CPU_CODEC_CONFIGS[video_codec]
                preset_config = codec_config['quality_presets'][quality_preset]
                
                cmd = [
                    ffmpeg_path,
                    '-i', input_path,
                    '-progress', 'pipe:2',
                    '-c:v', codec_config['encoder']
                ]
                
                # Add codec-specific parameters
                if video_codec == 'av1':
                    cmd.extend(['-crf', preset_config['crf'], '-preset', preset_config['preset']])
                else:
                    cmd.extend(['-crf', preset_config['crf'], '-preset', preset_config['preset']])
                
                cmd.extend([
                    '-c:a', AUDIO_CONFIG['codec'],
                    '-b:a', AUDIO_CONFIG['bitrate'],
                    '-ar', AUDIO_CONFIG['sample_rate'],
                    '-movflags', '+faststart',
                    '-pix_fmt', 'yuv420p',
                    '-y',
                    output_path
                ])
            
            # Update status to processing
            if encode_id:
                Video.update_status(encode_id, VideoStatus.PROCESSING)
            
            logger.info(f"Starting encoding: {video_codec} ({quality_preset})")
            
            # Execute FFmpeg with progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            start_time = time.time()
            last_update = 0
            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            spinner_idx = 0
            
            # Parse progress from stderr
            for line in process.stderr:
                # Look for time progress
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                
                if time_match:
                    now = time.time()
                    if now - last_update >= 0.5:  # Throttle updates
                        last_update = now
                        
                        hours, minutes, seconds = time_match.groups()
                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                        
                        # Build progress data
                        progress_data = {}
                        
                        if duration:
                            # Progress with duration
                            progress_pct = (current_time / duration) * 100
                            elapsed = now - start_time
                            
                            if current_time > 0:
                                eta_seconds = ((elapsed / current_time) * duration) - elapsed
                                progress_data['eta'] = f"{int(eta_seconds//60):02d}:{int(eta_seconds%60):02d}"
                            else:
                                progress_data['eta'] = "calculating..."
                            
                            progress_data['percent'] = min(progress_pct, 99)
                        else:
                            # Progress without duration
                            progress_data['current_time'] = current_time
                            progress_data['spinner'] = spinner_chars[spinner_idx % len(spinner_chars)]
                            spinner_idx += 1
                        
                        # Extract FPS and speed
                        fps_match = re.search(r'fps=\s*([\d.]+)', line)
                        speed_match = re.search(r'speed=\s*([\d.]+)x', line)
                        frame_match = re.search(r'frame=\s*(\d+)', line)
                        
                        if fps_match:
                            progress_data['fps'] = float(fps_match.group(1))
                        if speed_match:
                            progress_data['speed'] = speed_match.group(1) + 'x'
                        if frame_match:
                            progress_data['frame'] = int(frame_match.group(1))
                        
                        # Store in cache for status API
                        from src.services.progress_cache import ProgressCache
                        cache_data = {
                            'current_phase': 'encoding'
                        }
                        if 'percent' in progress_data:
                            cache_data['encoding_progress'] = progress_data['percent']
                            cache_data['eta'] = progress_data.get('eta', '??:??')
                        if 'speed' in progress_data:
                            cache_data['speed'] = progress_data['speed']
                        if 'fps' in progress_data:
                            cache_data['fps'] = progress_data['fps']
                        
                        if encode_id:
                            ProgressCache.set_progress(encode_id, cache_data)
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(progress_data)
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0:
                # If GPU encoding failed, retry with CPU
                if gpu_encoder and use_gpu:
                    logger.warning(f"⚠️  GPU encoding failed, retrying with CPU...")
                    return EncodingService.encode_video_to_mp4(
                        input_path, output_path, video_codec, quality_preset,
                        use_gpu=False, encode_id=encode_id, progress_callback=progress_callback
                    )
                else:
                    error_msg = f"Encoding failed (exit code {process.returncode})"
                    logger.error(error_msg)
                    return False, error_msg
            
            # Verify output file exists
            if not os.path.exists(output_path):
                return False, "Output file not created"
            
            logger.info(f"Encoding completed successfully: {output_path}")
            return True, None
            
        except subprocess.TimeoutExpired:
            error_msg = f"Encoding timeout"
            logger.error(error_msg)
            if process:
                process.kill()
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Encoding error: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    @staticmethod
    def get_supported_codecs() -> Dict[str, list]:
        
        return {
            codec: list(config['quality_presets'].keys())
            for codec, config in CPU_CODEC_CONFIGS.items()
        }
