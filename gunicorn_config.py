"""
Gunicorn configuration for production deployment.

NOTE: When gunicorn loads this config, start_server.py's bootstrap has
already run (via create_application()), so all Remote Config values
are in os.environ by the time gunicorn reads them.
"""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 300  # 5 minutes for video processing
keepalive = 2

# Logging (defaults to stdout/stderr; set ACCESS_LOG/ERROR_LOG env vars for files)
accesslog = os.getenv('ACCESS_LOG', '-')
errorlog = os.getenv('ERROR_LOG', '-')
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'yt-downloader'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Path to the application
pythonpath = os.path.dirname(__file__)


def on_starting(server):
    """Called just before the master process is initialized."""
    # Ensure log directory exists for gunicorn
    for log_path in [accesslog, errorlog]:
        if log_path and log_path != '-':
            log_dir = os.path.dirname(log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
    print("Starting YouTube Video Downloader server...")

def on_reload(server):
    """Called to recycle workers during a reload."""
    print("Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"Server is ready. Listening on {bind}")
