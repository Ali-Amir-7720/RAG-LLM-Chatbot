# Docker Compose Quick Start Guide

## Prerequisites
- Docker Desktop installed and running
- Docker Compose v2+

## Quick Start

### 1. Copy environment variables
```bash
cp docker/.env.example .env
# Edit .env with your actual values
```

### 2. Build and start containers
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 3. Check status
```bash
docker-compose -f docker/docker-compose.yml ps
```

### 4. View logs
```bash
docker-compose -f docker/docker-compose.yml logs -f
```

## Accessing Services

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Database:** localhost:5432

## Useful Commands

### Stop all services
```bash
docker-compose -f docker/docker-compose.yml down
```

### Remove all data (including database)
```bash
docker-compose -f docker/docker-compose.yml down -v
```

### Restart a service
```bash
docker-compose -f docker/docker-compose.yml restart backend
```

### View database logs
```bash
docker-compose -f docker/docker-compose.yml logs postgres
```

### Connect to database
```bash
docker exec -it rag_llm_db psql -U postgres -d fieldforce
```

### Rebuild images (after code changes)
```bash
docker-compose -f docker/docker-compose.yml build --no-cache
docker-compose -f docker/docker-compose.yml up -d
```

## Troubleshooting

### Port already in use
If ports 5173, 8000, or 5432 are already in use, edit `docker-compose.yml` and change the port mappings.

### Database connection errors
Check that `DATABASE_URL` in `.env` matches the docker-compose configuration.

### Frontend can't reach API
Ensure `VITE_API_BASE_URL` points to the correct backend URL.
