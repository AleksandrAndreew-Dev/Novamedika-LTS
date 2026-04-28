# 🚀 Production Deployment Quick Reference

## ⚠️ CRITICAL: Correct `produp` Alias

Your alias **MUST include Traefik** to avoid service outages:

```bash
# ✅ CORRECT - includes ALL services (Traefik + apps)
alias produp='docker compose -f docker-compose.traefik.prod.yml pull && docker compose -f docker-compose.traefik.prod.yml up -d'

# ❌ WRONG - excludes Traefik, causes "connection timed out"
alias produp='docker compose -f docker-compose.traefik.prod.yml pull frontend backend celery_worker && ...'
```

### Setup on Server

```bash
# 1. Remove old alias
unalias produp 2>/dev/null

# 2. Add correct alias
echo "alias produp='docker compose -f docker-compose.traefik.prod.yml pull && docker compose -f docker-compose.traefik.prod.yml up -d'" >> ~/.bashrc

# 3. Reload
source ~/.bashrc

# 4. Verify
alias produp
```

---

## 📋 Deployment Workflow

### Before Deployment

```bash
# Run diagnostics to check current state
./agent/diagnostics.sh all

# Check logs for errors
./agent/diagnostics.sh logs
```

### Deploy

```bash
cd /opt/novamedika-prod

# Option 1: Using alias (recommended)
produp

# Option 2: Using npm scripts
npm run prod:up

# Option 3: Manual Docker Compose
docker compose -f docker-compose.traefik.prod.yml pull
docker compose -f docker-compose.traefik.prod.yml up -d
```

### After Deployment

```bash
# Wait for services to stabilize
sleep 120

# Verify all containers are healthy
docker ps

# Test HTTPS connectivity
curl -I https://spravka.novamedika.com
curl -I https://pharmacist.spravka.novamedika.com
curl -I https://api.spravka.novamedika.com/health

# Check ports are open
ss -tlnp | grep -E ':(80|443)'

# Run full diagnostics
./agent/diagnostics.sh all
```

---

## 🔍 Troubleshooting

### Problem: "Connection Timed Out"

**Symptoms:**
- Browser shows "The server is taking too long to respond"
- `curl` fails with "Failed to connect to port 443"

**Cause:** Traefik container is not running

**Solution:**
```bash
# Start all services including Traefik
docker compose -f docker-compose.traefik.prod.yml up -d

# Verify Traefik is running
docker ps | grep traefik

# Check ports
ss -tlnp | grep -E ':(80|443)'
```

### Problem: Orphan Container Warnings

**Symptoms:**
```
WARN Found orphan containers ([pharmacist-webapp-prod]) for this project
```

**Cause:** Old containers from previous architecture

**Solution:**
```bash
docker compose -f docker-compose.traefik.prod.yml down --remove-orphans
produp
```

### Problem: Service Not Updating

**Symptoms:**
- New code not reflected after deployment
- Old version still showing

**Solution:**
```bash
# Force pull latest images
docker compose -f docker-compose.traefik.prod.yml pull

# Force recreate all containers
docker compose -f docker-compose.traefik.prod.yml up -d --force-recreate

# Verify image versions
docker inspect frontend-prod --format="{{.Config.Image}}"
docker inspect backend-prod --format="{{.Config.Image}}"
```

---

## 📊 Architecture Overview

### Single Frontend Image Architecture

```
Internet
    ↓
Traefik (ports 80/443)
    ↓
    ├─ spravka.novamedika.com → frontend-prod (main site)
    └─ pharmacist.spravka.novamedika.com → frontend-prod (pharmacist dashboard)

Backend Services:
    ├─ backend-prod (FastAPI + Telegram Bot)
    ├─ celery-worker-prod (background tasks)
    ├─ postgres-prod (database)
    └─ redis-prod (cache & queue)
```

**Key Points:**
- One frontend container serves BOTH websites
- Traefik routes based on HTTP Host header
- All services must run together
- Never restart app containers without Traefik

---

## 🛠️ Useful Commands

### Diagnostics

```bash
# Full system check
./agent/diagnostics.sh all

# Specific components
./agent/diagnostics.sh status    # Container health
./agent/diagnostics.sh logs      # All logs
./agent/diagnostics.sh frontend  # Both websites
./agent/diagnostics.sh backend   # API + Bot
./agent/diagnostics.sh db        # Database
./agent/diagnostics.sh network   # Connectivity
```

### Container Management

```bash
# View all containers
docker ps

# View logs
docker compose -f docker-compose.traefik.prod.yml logs -f [service]

# Restart specific service
docker compose -f docker-compose.traefik.prod.yml restart backend

# Stop all services
docker compose -f docker-compose.traefik.prod.yml down

# Clean up orphans
docker compose -f docker-compose.traefik.prod.yml down --remove-orphans
```

### Monitoring

```bash
# Resource usage
docker stats

# Real-time logs
docker compose -f docker-compose.traefik.prod.yml logs -f --tail=50

# Health checks
docker inspect --format="{{.State.Health.Status}}" frontend-prod
```

---

## 📝 Important Notes

1. **Always include Traefik** in any restart/pull operation
2. **Wait 2 minutes** after deployment before testing (services need time to initialize)
3. **Run diagnostics** before and after deployments to catch issues early
4. **Check logs** if something isn't working (`./agent/diagnostics.sh logs`)
5. **Never use selective restarts** that exclude infrastructure services

---

## 🔗 Related Documentation

- [AUTOMATED_DEPLOYMENT.md](AUTOMATED_DEPLOYMENT.md) - CI/CD workflow details
- [DIAGNOSTICS_GUIDE.md](DIAGNOSTICS_GUIDE.md) - Comprehensive diagnostics guide
- [PHARMACIST_WEBAPP_DEPLOYMENT.md](PHARMACIST_WEBAPP_DEPLOYMENT.md) - Pharmacist dashboard specifics
- [SIMPLIFIED_SINGLE_FRONTEND_IMAGE.md](SIMPLIFIED_SINGLE_FRONTEND_IMAGE.md) - Architecture explanation
