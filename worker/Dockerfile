FROM python:3.11-slim

# Install system dependencies including Node.js and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN python --version && node --version && npm --version && ffmpeg -version | head -1

# Install yt-dlp globally
RUN pip install --no-cache-dir yt-dlp

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create necessary directories
RUN mkdir -p /app/tmp /app/bin /app/logs

# Cookie file mount point
VOLUME /app/cookiesFile

# Firebase credentials (injected via env or build args)
ARG FIREBASE_SERVICE_ACCOUNT_KEY_PATH
ENV FIREBASE_SERVICE_ACCOUNT_KEY_PATH=$FIREBASE_SERVICE_ACCOUNT_KEY_PATH
ARG SERVICE_ACCOUNT_JSON
ENV SERVICE_ACCOUNT_JSON=$SERVICE_ACCOUNT_JSON
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

CMD ["python", "main.py"]
