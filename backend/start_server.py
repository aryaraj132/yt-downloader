"""
Application startup script.
This is the main entrypoint for starting the server.

Startup order:
  1. Load .env (for SERVICE_ACCOUNT_JSON & FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
  2. Create Firebase service-account JSON file on disk if it doesn't exist
  3. Initialize Firebase Admin SDK & inject Remote Config values into os.environ
  4. Setup FFmpeg
  5. Start the Flask server (run.py imports Config at this point, reading the final env)
"""
import os
import sys
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from setup_ffmpeg import verify_ffmpeg, setup_ffmpeg

# ── 0. Bootstrap logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── 0.1 Setup PATH for FFmpeg ───────────────────────────────────────
# Ensure local bin/ directory is in PATH so yt-dlp can find ffmpeg
_backend_dir = Path(__file__).resolve().parent
_bin_dir = _backend_dir / 'bin'
if _bin_dir.exists():
    os.environ["PATH"] = str(_bin_dir) + os.pathsep + os.environ["PATH"]
    logger.info(f"Added {_bin_dir} to PATH")

# ── 1. Load .env ─────────────────────────────────────────────────────
# .env lives at the project root (one level above backend/).
# In Docker, env vars are injected directly so this is a no-op.
_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent
_env_file = _project_root / '.env'
if _env_file.exists():
    load_dotenv(_env_file)
else:
    # Fallback: try CWD (for Docker or when .env is alongside backend files)
    load_dotenv()


# ─────────────────────────────────────────────────────────────────────
#  Pre-flight helpers
# ─────────────────────────────────────────────────────────────────────

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
        # Validate that the value is proper JSON
        json.loads(service_account_json)

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
    Skips entirely when ENVIRONMENT is 'local'.
    """
    import asyncio
    import firebase_admin
    from firebase_admin import credentials as fb_credentials

    credentials_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_PATH',
                                 'firebase-service-account.json')

    # Initialize Firebase Admin SDK if not already done
    if not firebase_admin._apps:
        if not os.path.exists(credentials_path):
            logger.warning("Credentials file not found – skipping Firebase "
                           "init (using .env values only)")
            return

        cred = fb_credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred)
        logger.info("✓ Firebase Admin SDK initialized")

    environment = os.getenv('ENVIRONMENT', 'local')
    #if environment in ('local',):
        #logger.info("ENVIRONMENT is 'local' – skipping Remote Config fetch")
        #return

    try:
        from firebase_admin import remote_config

        # Init template and fetch from Firebase (async API)
        template = remote_config.init_server_template()
        asyncio.run(template.load())
        config = template.evaluate()

        # _config_values holds the keys; use get_string() for actual values
        params = config._config_values

        if not params:
            logger.info("No Remote Config parameters found – "
                        "using .env values only")
            return

        injected = 0
        for key in params:
            # Only inject if not already set locally (local .env takes precedence)
            if key not in os.environ:
                os.environ[key] = config.get_string(key)
                injected += 1

        logger.info(f"✓ Injected {injected} value(s) from Remote Config "
                    f"(total params: {len(params)})")

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

        logger.info("FFmpeg not found. Setting up...")

        if setup_ffmpeg():
            logger.info("✓ FFmpeg setup completed")
            return True
        else:
            logger.error("✗ FFmpeg setup failed")
            return False

    except Exception as e:
        logger.error(f"FFmpeg check failed: {str(e)}")
        return False


# ─────────────────────────────────────────────────────────────────────
#  Entrypoints
# ─────────────────────────────────────────────────────────────────────

def bootstrap():
    """
    Run all pre-flight steps in order.
    Returns after env is fully configured and FFmpeg is ready.
    """
    # Step 1 – Create credentials file from env var
    create_credentials_file()

    # Step 2 – Init Firebase + inject Remote Config into os.environ
    load_remote_config()

    # Step 3 – Ensure FFmpeg is available
    if not check_and_setup_ffmpeg():
        print("\n❌ FFmpeg setup failed. Cannot start server.")
        print("Please ensure 'imageio-ffmpeg' is installed:")
        print("  pip install imageio-ffmpeg")
        sys.exit(1)


def create_application():
    """
    Application factory for production WSGI servers.
    Called by gunicorn:
        gunicorn -c gunicorn_config.py 'start_server:create_application()'
    """
    bootstrap()

    from run import main as run_server
    return run_server()


def main():
    """Main entrypoint for direct execution."""
    print("\n" + "=" * 60)
    print("YouTube Video Downloader - Server Startup")
    print("=" * 60 + "\n")

    bootstrap()

    print("\n✓ Pre-flight checks passed. Starting server...\n")

    from run import main as run_server
    run_server()


if __name__ == '__main__':
    main()
