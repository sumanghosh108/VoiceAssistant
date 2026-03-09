# Docker Quick Start Guide

Get the Real-Time Voice Assistant running with Docker in minutes.

## Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- API keys for Whisper, Gemini, and ElevenLabs

## 1. Setup Environment

```bash
# Copy environment template
cp ../.env.example ../.env

# Edit with your API keys
nano ../.env  # or use your preferred editor
```

Required variables:
```bash
WHISPER_API_KEY=your_whisper_api_key
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

## 2. Choose Your Setup

### Option A: Production (Recommended for deployment)

```bash
cd docker

# Build and start
make up

# View logs
make logs

# Check health
curl http://localhost:8001/health
```

### Option B: Development (Recommended for coding)

```bash
cd docker

# Build and start with hot-reload
make up-dev

# View logs
make logs-dev

# Run tests
make test

# Open shell
make shell
```

## 3. Verify It's Running

```bash
# Check container status
docker ps

# Test health endpoint
curl http://localhost:8001/health/live

# View metrics
curl http://localhost:8001/metrics

# Open dashboard in browser
open http://localhost:8001/dashboard
```

## 4. Connect a Client

The WebSocket server is available at:
```
ws://localhost:8000
```

See `../examples/voice_client.py` for a reference client implementation.

## 5. Stop Services

```bash
# Production
make down

# Development
make down-dev
```

## Common Commands

### Production
```bash
make build       # Build image
make up          # Start containers
make down        # Stop containers
make logs        # View logs
make restart     # Restart containers
```

### Development
```bash
make build-dev   # Build dev image
make up-dev      # Start dev containers
make down-dev    # Stop dev containers
make logs-dev    # View dev logs
make shell       # Open shell
make test        # Run tests
```

### Maintenance
```bash
make clean       # Remove all containers and volumes
make health      # Check container health
```

## Troubleshooting

### Ports already in use
```bash
# Check what's using the ports
netstat -an | grep 8000
netstat -an | grep 8001

# Stop conflicting services or change ports in docker-compose.yml
```

### Container won't start
```bash
# View detailed logs
docker-compose logs voice-assistant

# Check environment variables
docker-compose config
```

### Permission denied on volumes
```bash
# Fix permissions
chmod -R 755 ../recordings ../logs
```

### Need to rebuild from scratch
```bash
make clean
make build
make up
```

## Next Steps

- Read the [full Docker documentation](README.md)
- Check the [configuration guide](../docs/configuration.md)
- Explore the [API documentation](../docs/api.md)
- Review [architecture documentation](../docs/architecture.md)

## Support

For issues and questions:
1. Check the [troubleshooting guide](../docs/troubleshooting.md)
2. Review container logs: `make logs` or `make logs-dev`
3. Check health status: `curl http://localhost:8001/health`
