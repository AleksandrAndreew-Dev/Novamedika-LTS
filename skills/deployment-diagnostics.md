# Skill: Deployment & Diagnostics

## When to use this skill:
- Before committing code (pre-deployment check)
- After deployment (verification)
- When services are not working
- Performance issues
- Container crashes or restarts

## Pre-Deployment Checklist:

### 1. Code Validation
```bash
# Backend - check for syntax errors
cd backend
uv run python -m py_compile src/main.py

# Frontend - check build
cd frontend
npm run build
```

### 2. Run Full Diagnostics
```bash
bash agent/diagnostics.sh all
```

### 3. Check Critical Components
```bash
# Container status
bash agent/diagnostics.sh status

# Look for errors only
cat agent/server-logs/*_errors-only.txt | tail -50
```

### 4. Verify Database Migrations
```bash
# If models changed, ensure migration exists
ls backend/alembic/versions/ | tail -5

# Check migration status
cd backend
uv run alembic current
```

### 5. Environment Variables
```bash
# Check .env file exists and is complete
cat .env | grep -v "^#" | grep -v "^$"

# Compare with example
diff <(grep "^[A-Z]" .env.example | cut -d= -f1 | sort) \
     <(grep "^[A-Z]" .env | cut -d= -f1 | sort)
```

## Post-Deployment Verification:

### 1. Service Health
```bash
# All containers running?
bash agent/diagnostics.sh status

# Check logs for errors
bash agent/diagnostics.sh logs
```

### 2. API Endpoints
```bash
# Test main endpoint
curl -k https://api.yourdomain.com/health

# Test authentication
curl -k https://api.yourdomain.com/api/auth/test
```

### 3. Frontend Access
```bash
# Check frontend loads
bash agent/diagnostics.sh frontend

# Verify HTTPS
curl -k https://yourdomain.com | head -20
```

### 4. Telegram Bot
```bash
# Bot diagnostics
bash agent/diagnostics.sh bot

# Check webhook status
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 5. Database Connection
```bash
# DB connectivity
bash agent/diagnostics.sh db

# Check table sizes
bash agent/diagnostics.sh db | grep -i "table"
```

## Troubleshooting Common Issues:

### Issue: Backend not starting
```bash
# Check logs
bash agent/diagnostics.sh backend

# Common causes:
# 1. Missing environment variables
cat .env | grep -E "DATABASE_URL|SECRET_KEY|REDIS_URL"

# 2. Database connection failed
bash agent/diagnostics.sh db

# 3. Port conflicts
docker ps | grep backend
```

### Issue: Frontend shows white screen
```bash
# Check build errors
bash agent/diagnostics.sh frontend

# Check API connectivity
bash agent/diagnostics.sh frontend | grep -i "api"

# Clear browser cache and reload
```

### Issue: Telegram bot not responding
```bash
# Full bot diagnostics
bash agent/diagnostics.sh bot

# Check FSM states
bash agent/diagnostics.sh bot | grep -i "state"

# Check webhook
bash agent/diagnostics.sh bot | grep -i "webhook"

# Restart bot container
npm run prod:restart-backend
```

### Issue: Database connection refused
```bash
# Check PostgreSQL status
bash agent/diagnostics.sh db

# Check network
bash agent/diagnostics.sh network

# Restart database
docker-compose -f docker-compose.traefik.prod.yml restart db
```

### Issue: High memory/CPU usage
```bash
# Check resource usage
docker stats --no-stream

# Check logs for loops/errors
bash agent/diagnostics.sh logs | grep -i "error\|exception" | tail -20

# Consider restarting
npm run prod:restart
```

## Emergency Procedures:

### Rollback Deployment
```bash
# 1. Stop current deployment
npm run prod:down

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Redeploy
npm run prod:up
```

### Emergency Restart
```bash
# Restart all services
npm run prod:restart

# Or specific service
npm run prod:restart-backend
npm run prod:restart-frontend
```

### Clear Cache & Rebuild
```bash
# Stop services
npm run prod:down

# Remove old images
docker system prune -a

# Rebuild from scratch
npm run prod:build
npm run prod:up
```

## Monitoring Stack:

### Access Grafana
```
URL: https://grafana.yourdomain.com
Default credentials: admin/admin (change in production!)
```

### Key Dashboards:
- System resources (CPU, RAM, Disk)
- Application metrics (requests, errors, latency)
- Database performance
- Traefik traffic analysis

### Alert Conditions:
- Container restarts > 3 times in 1 hour
- Error rate > 5% of requests
- Response time > 2 seconds
- Disk usage > 80%
- Memory usage > 90%

## Quick Reference Commands:

```bash
# Status check
npm run prod:ps

# View logs (live)
npm run prod:logs

# Restart specific service
docker-compose -f docker-compose.traefik.prod.yml restart backend

# View resource usage
docker stats

# Check disk space
df -h

# Clean up old logs/images
docker system prune -f
```

## Resources:
- `agent/diagnostics.sh` - Main diagnostic tool
- `.ai-rules.md` - Always follow AI agent rules
- `EMERGENCY-ACTION-PLAN.md` - Emergency procedures
- `DEPLOYMENT-MONITORING-ENHANCEMENT.md` - Monitoring setup
