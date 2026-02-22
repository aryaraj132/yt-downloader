"""
Worker bootstrap — pre-flight checks before starting consumers.

Startup order:
  1. Load .env (for SERVICE_ACCOUNT_JSON & FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
  2. Create Firebase service-account JSON file on disk if it doesn't exist
  3. Initialize Firebase Admin SDK & inject Remote Config values into os.environ
  4. Setup FFmpeg (verify or install via imageio-ffmpeg)
  5. Add bin/ to PATH so yt-dlp can find ffmpeg

Based on legacy backend/start_server.py, adapted for the worker context.
"""
import os
import sys
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from setup_ffmpeg import verify_ffmpeg, setup_ffmpeg

logger = logging.getLogger(__name__)

# ── Resolve paths ────────────────────────────────────────────────────
_worker_dir = Path(__file__).resolve().parent
_project_root = _worker_dir.parent


def _load_env():
    """Load .env from project root or current directory."""
    env_file = _project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()  # fallback for Docker (env vars injected directly)


def _setup_path():
    """Add local bin/ directory to PATH so yt-dlp can find ffmpeg."""
    bin_dir = _worker_dir / 'bin'
    if bin_dir.exists():
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
        logger.info(f"Added {bin_dir} to PATH")


def create_credentials_file():
    """
    Write the Firebase service-account JSON file to disk if it doesn't
    already exist.  The JSON content comes from the SERVICE_ACCOUNT_JSON
    env var, and the target filename from FIREBASE_SERVICE_ACCOUNT_KEY_PATH.
    """
    service_account_json = os.getenv('SERVICE_ACCOUNT_JSON')
    credentials_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH',
                                 'firebase-service-account.json')

    if not service_account_json:
        logger.info("SERVICE_ACCOUNT_JSON not set – skipping credentials "
                     "file creation (assuming file already exists)")
        return

    if os.path.exists(credentials_path):
        logger.info(f"✓ Credentials file already exists: {credentials_path}")
        return

    try:
        json.loads(service_account_json)  # validate JSON

        with open(credentials_path, 'w') as f:
            f.write(service_account_json)

        logger.info(f"✓ Created credentials file: {credentials_path}")
    except json.JSONDecodeError as e:
        logger.error(f"✗ SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Failed to write credentials file: {e}")
        sys.exit(1)


def load_remote_config():
    """
    Fetch Firebase Remote Config and inject its parameters into
    os.environ (only if the key is not already set locally).
    Local .env values take precedence over Remote Config.
    """
    import asyncio

    credentials_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH',
                                 'firebase-service-account.json')

    try:
        import firebase_admin
        from firebase_admin import credentials as fb_credentials

        # Initialize Firebase Admin SDK if not already done
        if not firebase_admin._apps:
            if not os.path.exists(credentials_path):
                logger.warning("Credentials file not found – skipping Firebase "
                               "init (using .env values only)")
                return

            cred = fb_credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info("✓ Firebase Admin SDK initialized")

        from firebase_admin import remote_config

        # Fetch remote config (async API)
        template = remote_config.init_server_template()
        asyncio.run(template.load())
        config = template.evaluate()

        params = config._config_values

        if not params:
            logger.info("No Remote Config parameters found – using .env values only")
            return

        injected = 0
        for key in params:
            # Only inject if not already set locally (local .env takes precedence)
            if key not in os.environ:
                os.environ[key] = config.get_string(key)
                injected += 1

        logger.info(f"✓ Injected {injected} value(s) from Remote Config "
                    f"(total params: {len(params)})")

    except ImportError:
        logger.warning("firebase-admin not installed – skipping Remote Config")
    except Exception as e:
        logger.error(f"✗ Failed to fetch Remote Config: {e}")
        logger.info("Falling back to .env values")


def check_and_setup_ffmpeg():
    """Check if FFmpeg is available, set it up if not."""
    logger.info("Checking FFmpeg setup...")

    try:
        if verify_ffmpeg():
            logger.info("✓ FFmpeg is ready")
            return True

        logger.info("FFmpeg not found. Setting up via imageio-ffmpeg...")

        if setup_ffmpeg():
            logger.info("✓ FFmpeg setup completed")
            return True
        else:
            logger.error("✗ FFmpeg setup failed")
            return False

    except Exception as e:
        logger.error(f"FFmpeg check failed: {str(e)}")
        return False


def bootstrap():
    """
    Run all pre-flight steps in order.
    Must be called before Config is read so that Remote Config values
    are available in os.environ.
    """
    logger.info("=" * 60)
    logger.info("Worker Bootstrap Starting")
    logger.info("=" * 60)

    # Step 0 – Load .env
    _load_env()

    # Step 1 – Add bin/ to PATH
    _setup_path()

    # Step 2 – Create credentials file from env var
    create_credentials_file()

    # Step 3 – Init Firebase + inject Remote Config into os.environ
    load_remote_config()

    # Step 4 – Ensure FFmpeg is available
    if not check_and_setup_ffmpeg():
        logger.error("❌ FFmpeg setup failed. Cannot start worker.")
        logger.error("Please ensure 'imageio-ffmpeg' is installed or "
                     "'ffmpeg' is in PATH (Docker).")
        sys.exit(1)

    logger.info("✓ Bootstrap complete")
