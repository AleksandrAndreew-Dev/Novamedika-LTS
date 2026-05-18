# 🚀 Deployment Checklist - OAC Compliance Critical Updates

**Date:** 2026-05-05  
**Priority:** 🔴 CRITICAL  
**Estimated Time:** 30 minutes

---

## Pre-Deployment Checks

- [ ] Backup production database
  ```bash
  docker-compose exec postgres pg_dump -U novamedika novamedika_prod | gzip > backup_$(date +%Y%m%d).sql.gz
  ```

- [ ] Verify current system health
  ```bash
  ./agent/diagnostics.sh all
  ```

- [ ] Review changes in git
  ```bash
  git status
  git diff
  ```

---

## Step 1: Environment Configuration

- [ ] Generate ADMIN_API_KEY(s)
  ```bash
  openssl rand -hex 32
  # Save output securely
  ```

- [ ] Update `.env` file on production server
  ```bash
  # Add to .env
  ADMIN_API_KEYS=<your-generated-key-here>
  ```

- [ ] Verify `.env` file permissions
  ```bash
  chmod 600 .env
  ```

---

## Step 2: Deploy Monitoring Stack

- [ ] Pull latest images
  ```bash
  docker-compose -f docker-compose.monitoring.yml pull
  ```

- [ ] Restart monitoring services
  ```bash
  docker-compose -f docker-compose.monitoring.yml up -d
  ```

- [ ] Verify Prometheus is running
  ```bash
  docker-compose -f docker-compose.monitoring.yml ps prometheus
  # Should show "Up" status
  ```

- [ ] Check Prometheus targets
  ```bash
  curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'
  # All should show "health": "up"
  ```

---

## Step 3: Deploy Traefik with Metrics

- [ ] Pull latest Traefik image
  ```bash
  docker-compose -f docker-compose.traefik.prod.yml pull
  ```

- [ ] Restart Traefik
  ```bash
  docker-compose -f docker-compose.traefik.prod.yml up -d
  ```

- [ ] Verify metrics endpoint
  ```bash
  curl http://localhost:8080/metrics | grep traefik_entrypoint_requests_total
  # Should return metric data
  ```

- [ ] Check Traefik logs for errors
  ```bash
  docker-compose -f docker-compose.traefik.prod.yml logs --tail=50
  ```

---

## Step 4: Deploy Backend with Audit Middleware

- [ ] Pull latest backend image (or rebuild)
  ```bash
  docker-compose -f docker-compose.backend.prod.yml build --no-cache
  ```

- [ ] Apply database migrations
  ```bash
  docker-compose -f docker-compose.backend.prod.yml run --rm backend python -m alembic upgrade head
  ```

- [ ] Verify migration applied
  ```bash
  docker-compose -f docker-compose.backend.prod.yml run --rm backend python -m alembic current
  # Should show: 6cfa51de7ac5 (head)
  ```

- [ ] Restart backend
  ```bash
  docker-compose -f docker-compose.backend.prod.yml up -d
  ```

- [ ] Check backend logs
  ```bash
  docker-compose -f docker-compose.backend.prod.yml logs -f backend
  # Look for: "Audit logging middleware enabled"
  ```

- [ ] Verify audit_logs table exists
  ```bash
  docker-compose exec postgres psql -U novamedika -d novamedika_prod -c "\dt audit_logs"
  # Should show table structure
  ```

---

## Step 5: Import Grafana Dashboard

- [ ] Access Grafana
  ```
  http://<server-ip>:3000
  Login: admin / <your-password>
  ```

- [ ] Import dashboard
  1. Go to Dashboards → Import
  2. Upload `dashboards/oac-security-monitoring.json`
  3. Select Loki and Prometheus datasources
  4. Click "Import"

- [ ] Verify dashboard panels
  - [ ] "Ошибки по контейнерам (ERROR)" - shows data
  - [ ] "Запросы по entrypoints (req/s)" - shows data
  - [ ] "HTTP ошибки (4xx/5xx)" - shows data
  - [ ] "P95 Latency" - shows data
  - [ ] "Неудачные аутентификации" - shows data

---

## Step 6: Functional Testing

### Test 1: Audit Logging

- [ ] Make test request to audited endpoint
  ```bash
  # Get valid JWT token first (login as user)
  TOKEN=$(curl -X POST http://localhost:8000/api/pharmacist/login \
    -H "Content-Type: application/json" \
    -d '{"phone":"+1234567890","password":"test"}' | jq -r '.access_token')
  
  # Make request to audited endpoint
  curl -H "Authorization: Bearer $TOKEN" \
       http://localhost:8000/api/users/me
  ```

- [ ] Check audit log entry
  ```bash
  curl -H "X-API-Key: <your-admin-key>" \
       http://localhost:8000/api/admin/audit-logs?page=1&page_size=5 | jq
  ```
  
  Expected: Should see entry with:
  - `"action": "read"`
  - `"resource_type": "user"`
  - `"success": true`

### Test 2: Admin Endpoint Security

- [ ] Test without API key (should fail)
  ```bash
  curl http://localhost:8000/api/admin/audit-logs
  # Should return: 401 Unauthorized
  ```

- [ ] Test with invalid API key (should fail)
  ```bash
  curl -H "X-API-Key: wrong-key" \
       http://localhost:8000/api/admin/audit-logs
  # Should return: 401 Unauthorized
  ```

- [ ] Test with valid API key (should succeed)
  ```bash
  curl -H "X-API-Key: <your-valid-key>" \
       http://localhost:8000/api/admin/audit-logs
  # Should return: 200 OK with data
  ```

### Test 3: Statistics Endpoint

- [ ] Get audit statistics
  ```bash
  curl -H "X-API-Key: <your-admin-key>" \
       http://localhost:8000/api/admin/audit-logs/stats?days=7 | jq
  ```
  
  Expected: JSON with total_events, by_action, by_resource, top_users

### Test 4: Prometheus Metrics

- [ ] Query Prometheus directly
  ```bash
  curl -G http://localhost:9090/api/v1/query \
    --data-urlencode 'query=traefik_entrypoint_requests_total' | jq
  ```
  
  Expected: Should return metric values

- [ ] Check Grafana datasource connectivity
  1. Go to Configuration → Data Sources
  2. Click "Prometheus" → "Save & Test"
  3. Should show "Data source is working"

---

## Step 7: Monitoring & Alerts Setup

- [ ] Set up basic Grafana alerts (optional but recommended)
  
  **Alert 1: High Error Rate**
  ```
  Query: sum(rate(traefik_entrypoint_requests_total{code=~"5.*"}[5m])) / sum(rate(traefik_entrypoint_requests_total[5m])) > 0.05
  Condition: > 5% for 5 minutes
  Notification: Email/Slack
  ```

  **Alert 2: Failed Authentication Spike**
  ```
  Query: sum(rate({job="docker-containers"} |= "Authentication failed" [5m])) > 10
  Condition: > 10 events per minute for 5 minutes
  Notification: Email/Slack
  ```

  **Alert 3: Disk Usage High**
  ```
  Query: (node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes > 0.8
  Condition: > 80% for 10 minutes
  Notification: Email/Slack
  ```

---

## Step 8: Documentation Update

- [ ] Update team wiki with new endpoints
  - `/api/admin/audit-logs` - View audit logs
  - `/api/admin/audit-logs/stats` - View statistics

- [ ] Document ADMIN_API_KEY rotation procedure
  ```markdown
  ## Rotating ADMIN_API_KEY
  
  1. Generate new key: `openssl rand -hex 32`
  2. Add new key to .env (comma-separated): `ADMIN_API_KEYS=old-key,new-key`
  3. Restart backend: `docker-compose restart backend`
  4. Update all automation scripts with new key
  5. After 24 hours, remove old key from .env
  6. Restart backend again
  ```

- [ ] Create runbook for security incident response
  ```markdown
  ## Responding to Security Incident
  
  1. Check audit logs: `curl -H "X-API-Key: KEY" http://localhost:8000/api/admin/audit-logs?action=delete`
  2. Check failed auth attempts in Grafana
  3. Check Fail2ban logs: `docker-compose exec fail2ban fail2ban-client status`
  4. Block suspicious IPs if needed
  5. Document incident in security log
  ```

---

## Post-Deployment Verification

- [ ] Monitor for 24 hours
  - Check backend logs for audit middleware errors
  - Verify audit_logs table is growing (not empty)
  - Confirm Prometheus is collecting metrics
  - Ensure Grafana dashboard shows live data

- [ ] Performance impact assessment
  ```bash
  # Check database size growth
  docker-compose exec postgres psql -U novamedika -d novamedika_prod -c \
    "SELECT pg_size_pretty(pg_total_relation_size('audit_logs'));"
  
  # Check backend response times
  curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
  ```

- [ ] Backup verification
  ```bash
  # Run manual backup
  ./scripts/backup.sh
  
  # Verify backup includes audit_logs
  ls -lh /backups/
  ```

---

## Rollback Plan (if issues occur)

### Scenario 1: Backend crashes after deployment

```bash
# 1. Check logs
docker-compose logs backend | tail -100

# 2. If migration issue, rollback migration
docker-compose run --rm backend python -m alembic downgrade -1

# 3. Restart backend
docker-compose up -d backend
```

### Scenario 2: Audit middleware causing performance issues

```bash
# 1. Temporarily disable middleware (comment out in main.py)
# 2. Rebuild and restart
docker-compose build backend
docker-compose up -d backend

# 3. Investigate root cause
# 4. Re-enable when fixed
```

### Scenario 3: Prometheus not collecting data

```bash
# 1. Check Prometheus config
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml

# 2. Check target status
curl http://localhost:9090/api/v1/targets | jq

# 3. Restart Prometheus
docker-compose restart prometheus

# 4. Check Traefik metrics endpoint
curl http://traefik:8080/metrics | head -20
```

---

## Success Criteria

✅ All checks passed:
- [ ] Traefik metrics endpoint returns data
- [ ] Prometheus shows all targets UP
- [ ] Grafana dashboard displays real-time data
- [ ] Audit logs are being created on API requests
- [ ] Admin endpoints require valid API key
- [ ] No errors in backend logs related to audit middleware
- [ ] Database migration applied successfully
- [ ] Performance impact < 5% increase in response time

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DevOps Engineer | | | |
| Security Officer | | | |
| Project Manager | | | |

---

**Notes:**
- Keep this checklist for future reference
- Update based on lessons learned during deployment
- Store completed checklists in project documentation
