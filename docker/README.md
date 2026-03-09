# Docker Configuration

This directory contains all Docker-related files for the Real-Time Voice Assistant application.

## Files

### Dockerfile
Production-ready Docker image configuration.
- Based on `python:3.11-slim`
- Includes only production dependencies
- Optimized for size and security
- Includes health checks

### Dockerfile.dev
Development Docker image with additional tools.
- Includes development dependencies
- Supports hot-reload with volume mounts
- Includes testing tools

### docker-compose.yml
Production Docker Compose configuration.
- Single service setup
- Environment variable configuration
- Volume mounts for recordings
- Health checks and restart policies

### docker-compose.dev.yml
Development Docker Compose configuration.
- Source code volume mounts for hot-reload
- Debug logging enabled
- Recording enabled by default
- Additional development tools

## Quick Start

### Production Deployment

1. **Set up environment variables:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your API keys
   ```

2. **Build and run:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Check status:**
   ```bash
   docker-compose ps
   docker-compose logs -f voice-assistant
   ```

4. **Access services:**
   - WebSocket: `ws://localhost:8000`
   - Metrics Dashboard: `http://localhost:8001/dashboard`
   - Health Check: `http://localhost:8001/health`

### Development Setup

1. **Set up environment variables:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your API keys
   ```

2. **Build and run development container:**
   ```bash
   cd docker
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **View logs:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f
   ```

4. **Run tests inside container:**
   ```bash
   docker-compose -f docker-compose.dev.yml exec voice-assistant-dev pytest
   ```

## Building Images

### Production Image
```bash
cd docker
docker build -f Dockerfile -t voice-assistant:latest ..
```

### Development Image
```bash
cd docker
docker build -f Dockerfile.dev -t voice-assistant:dev ..
```

## Environment Variables

All environment variables can be configured in `.env` file or passed directly to Docker Compose.

### Required Variables
```bash
WHISPER_API_KEY=your_whisper_key
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
```

### Optional Configuration
See `docker-compose.yml` for full list of configurable environment variables including:
- API timeouts
- Server ports
- Pipeline configuration
- Resilience settings
- Observability options

## Docker Compose Commands

### Start services
```bash
docker-compose up -d                    # Production
docker-compose -f docker-compose.dev.yml up -d  # Development
```

### Stop services
```bash
docker-compose down                     # Production
docker-compose -f docker-compose.dev.yml down   # Development
```

### View logs
```bash
docker-compose logs -f                  # Production
docker-compose -f docker-compose.dev.yml logs -f  # Development
```

### Restart services
```bash
docker-compose restart                  # Production
docker-compose -f docker-compose.dev.yml restart  # Development
```

### Rebuild images
```bash
docker-compose up -d --build            # Production
docker-compose -f docker-compose.dev.yml up -d --build  # Development
```

### Execute commands in container
```bash
# Production
docker-compose exec voice-assistant python -m pytest

# Development
docker-compose -f docker-compose.dev.yml exec voice-assistant-dev bash
```

## Health Checks

The containers include built-in health checks:

```bash
# Check health status
docker-compose ps

# View health check logs
docker inspect --format='{{json .State.Health}}' realtime-voice-assistant | jq
```

Health check endpoint: `http://localhost:8001/health/live`

## Volumes

### Production
- `../recordings:/app/recordings` - Session recordings

### Development
- `../src:/app/src` - Source code (hot-reload)
- `../config:/app/config` - Configuration files
- `../tests:/app/tests` - Test files
- `../recordings:/app/recordings` - Session recordings
- `../logs:/app/logs` - Application logs

## Networking

Both configurations create a bridge network `voice-assistant-network` for service communication.

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs voice-assistant

# Check if ports are already in use
netstat -an | grep 8000
netstat -an | grep 8001
```

### Health check failing
```bash
# Check health endpoint directly
curl http://localhost:8001/health/live

# View detailed health status
curl http://localhost:8001/health
```

### Permission issues with volumes
```bash
# Fix permissions on host
chmod -R 755 ../recordings ../logs
```

### Rebuild from scratch
```bash
# Remove containers, volumes, and images
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Production Considerations

### Security
- Use secrets management for API keys (Docker Secrets, Kubernetes Secrets)
- Run container as non-root user
- Scan images for vulnerabilities
- Keep base images updated

### Performance
- Adjust resource limits in docker-compose.yml:
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
  ```

### Monitoring
- Integrate with Prometheus for metrics
- Use centralized logging (ELK, Splunk)
- Set up alerting for health check failures

### Scaling
For horizontal scaling, use Docker Swarm or Kubernetes:
```bash
# Docker Swarm example
docker service create --replicas 3 \
  --name voice-assistant \
  --publish 8000:8000 \
  --publish 8001:8001 \
  voice-assistant:latest
```

## Related Documentation

- [Main README](../README.md)
- [Setup Guide](../docs/SETUP_GUIDE.md)
- [Configuration Guide](../docs/configuration.md)
- [Architecture Documentation](../docs/architecture.md)
