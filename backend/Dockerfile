# Root Dockerfile for Python Backend with Node.js
FROM python:3.14.2-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN python --version && node --version && npm --version

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p downloads uploads bin logs

# Expose port (adjust as needed)
EXPOSE 5000

# Set environment variables
ARG FIREBASE_SERVICE_ACCOUNT_KEY_PATH
ENV FIREBASE_SERVICE_ACCOUNT_KEY_PATH=$FIREBASE_SERVICE_ACCOUNT_KEY_PATH
ARG SERVICE_ACCOUNT_JSON
ENV SERVICE_ACCOUNT_JSON=$SERVICE_ACCOUNT_JSON
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start the server using gunicorn via start_server.py bootstrap
# The bootstrap flow handles:
#   1. Creating firebase-service-account.json from SERVICE_ACCOUNT_JSON env var
#   2. Fetching Firebase Remote Config and injecting into env
#   3. Setting up FFmpeg
#   4. Starting the Flask app
CMD ["gunicorn", "-c", "gunicorn_config.py", "start_server:create_application()"]
