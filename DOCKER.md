# Docker Deployment Guide

This guide explains how to build and run the YT-Downloader application using Docker.

## Architecture

The application consists of four services:

1. **Backend** - Python 3.14.2 + Node.js (Flask + yt-dlp)
2. **Frontend** - Next.js 14 (React application)
3. **Redis** - Cache and session storage
4. **MongoDB** - Database for user data and videos

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

## Quick Start

### 1. Environment Setup

Create a `.env` file in the root directory with the following variables:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# MongoDB Configuration
MONGO_URI=mongodb://admin:password@mongo:27017/yt-downloader?authSource=admin
MONGO_USERNAME=admin
MONGO_PASSWORD=password

# Redis Configuration
REDIS_URI=redis://redis:6379/0

# Firebase Configuration (if using)
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json

# Server Configuration
PORT=5000
```

Create a `.env.local` file in the `frontend/` directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 2. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **MongoDB**: localhost:27017
- **Redis**: localhost:6379

## Individual Service Builds

### Backend Only

```bash
# Build backend image
docker build -t yt-downloader-backend .

# Run backend container
docker run -p 5000:5000 --env-file .env yt-downloader-backend
```

### Frontend Only

```bash
# Build frontend image
cd frontend
docker build -t yt-downloader-frontend .

# Run frontend container
docker run -p 3000:3000 yt-downloader-frontend
```

## Docker Files Overview

### Root Dockerfile (Backend)

- **Base Image**: Python 3.14.2-slim
- **Additional**: Node.js 20.x installed
- **Key Steps**:
  1. Installs system dependencies
  2. Installs Python packages from `requirements.txt`
  3. Runs `setup_ffmpeg.py` to configure FFmpeg
  4. Sets up gunicorn for production server

### Frontend Dockerfile

- **Base Image**: Node.js 20-alpine
- **Multi-stage Build**:
  1. **deps** - Install dependencies
  2. **builder** - Build Next.js application
  3. **runner** - Run production server with minimal footprint

### docker-compose.yml

Orchestrates all services with:
- **Networking**: All services on `yt-downloader-network`
- **Volumes**: Persistent storage for MongoDB, Redis, downloads, and logs
- **Dependencies**: Proper service startup order

## Production Deployment

### Using Docker Compose in Production

```bash
# Pull latest images (if using registry)
docker-compose pull

# Start services
docker-compose up -d

# Update services
docker-compose up -d --build --force-recreate
```

### Environment Variables for Production

Ensure you update these in your `.env` file:

- Set `FLASK_ENV=production`
- Use strong `SECRET_KEY`
- Configure proper MongoDB credentials
- Set up Firebase credentials (if using)

### Health Checks

The backend includes a health check endpoint. Docker will automatically monitor:
- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 40 seconds
- Retries: 3

## Volumes and Data Persistence

The following volumes are created:

- `mongo-data` - MongoDB database files
- `redis-data` - Redis persistence
- `./downloads` - Downloaded video files (mapped to host)
- `./logs` - Application logs (mapped to host)

## Troubleshooting

### Backend Issues

```bash
# Check backend logs
docker-compose logs backend

# Verify FFmpeg setup
docker-compose exec backend python setup_ffmpeg.py

# Access backend shell
docker-compose exec backend bash
```

### Frontend Issues

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend (if changes made)
docker-compose up -d --no-deps --build frontend
```

### Database Connection Issues

```bash
# Check MongoDB logs
docker-compose logs mongo

# Check Redis logs
docker-compose logs redis

# Verify network
docker network inspect yt-downloader-network
```

## Customization

### Changing Ports

Edit `docker-compose.yml` to modify exposed ports:

```yaml
services:
  backend:
    ports:
      - "8080:5000"  # Change 8080 to your desired port
  
  frontend:
    ports:
      - "3001:3000"  # Change 3001 to your desired port
```

### Resource Limits

Add resource constraints to services:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Development vs Production

### Development

Use local installation for faster development cycles:

```bash
# Backend
python start_server.py

# Frontend
cd frontend
npm run dev
```

### Production

Use Docker for consistent deployment:

```bash
docker-compose up -d
```

## Security Notes

1. **Never commit** `.env` files to version control
2. **Use strong passwords** for MongoDB and Redis in production
3. **Configure firewall rules** to restrict access to ports
4. **Use HTTPS** in production with reverse proxy (nginx/traefik)
5. **Regularly update** Docker images for security patches

## Monitoring

Consider adding monitoring tools:

```yaml
services:
  # ... existing services ...
  
  prometheus:
    image: prom/prometheus
    # ... configuration ...
  
  grafana:
    image: grafana/grafana
    # ... configuration ...
```

## Backup

### Database Backup

```bash
# Backup MongoDB
docker-compose exec mongo mongodump --out /backup

# Backup Redis
docker-compose exec redis redis-cli SAVE
```

### Restore

```bash
# Restore MongoDB
docker-compose exec mongo mongorestore /backup
```
