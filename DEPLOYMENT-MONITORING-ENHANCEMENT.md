# 🚀 Monitoring Stack Enhancement - Deployment Checklist

**Date**: May 18, 2026  
**Purpose**: Deploy PostgreSQL, Redis, and Node exporters for comprehensive OAC-compliant monitoring

---

## ✅ Pre-Deployment Checklist

### 1. Backup Current State
```bash
ssh aleksandr@178.172.137.7

cd /opt/novamedika-prod

# Backup current Prometheus config
cp config/prometheus.yml config/prometheus.yml.backup.$(date +%Y%m%d)

# Backup current docker-compose
cp docker-compose.traefik.prod.yml docker-compose.traefik.prod.yml.backup.$(date +%Y%m%d)

# Verify backups exist
ls -la config/*.backup.* docker-compose.*.backup.*
```

### 2. Check Server Resources
```bash
# Ensure sufficient disk space (need ~500MB for new containers + data)
df -h /var/lib/docker

# Check available memory
free -h

# Current container resource usage
docker stats --no-stream
```

**Minimum Requirements**:
- Disk: ≥2GB free space
- Memory: ≥500MB available RAM
- CPU: ≥0.5 cores available

---

## 📦 Deployment Steps

### Step 1: Pull Latest Code
```bash
cd /opt/novamedika-prod
git pull origin main
```

**Expected Output**: 
```
Updating <commit-hash>..<new-commit-hash>
Fast-forward
 config/prometheus.yml                    | XX ++--
 docker-compose.traefik.prod.yml          | XX ++--
 agent/diagnostics.sh                     | XX ++--
 oac/guides/MONITORING-STACK-GUIDE.md     | XX ++ (new file)
 oac/audits/MONITORING-STATUS-REPORT...   | XX ++ (new file)
```

### Step 2: Review Changes
```bash
# Check what changed in compose file
git diff HEAD~1 docker-compose.traefik.prod.yml

# Check prometheus config changes
git diff HEAD~1 config/prometheus.yml
```

**Verify**:
- ✅ postgres_exporter service added
- ✅ redis_exporter service added
- ✅ node_exporter service added
- ✅ New scrape jobs in prometheus.yml

### Step 3: Deploy Updated Configuration
```bash
# Deploy with zero-downtime (rolling update)
docker-compose -f docker-compose.traefik.prod.yml up -d

# This will:
# - Create 3 new exporter containers
# - Restart Prometheus with new config
# - Keep all other services running
```

**Expected Output**:
```
Creating postgres-exporter ... done
Creating redis-exporter    ... done
Creating node-exporter     ... done
Recreating prometheus      ... done
```

### Step 4: Verify Container Status
```bash
# Check all containers are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Specifically check new exporters
docker ps | grep exporter
```

**Expected Result**:
```
postgres-exporter    Up X minutes    0.0.0.0:9187->9187/tcp
redis-exporter       Up X minutes    0.0.0.0:9121->9121/tcp
node-exporter        Up X minutes    0.0.0.0:9100->9100/tcp
prometheus           Up X minutes    0.0.0.0:9090->9090/tcp
```

### Step 5: Verify Prometheus Targets
```bash
# Wait 30 seconds for first scrape, then check
sleep 30

# Query Prometheus API
curl -s http://localhost:9090/api/v1/targets | \
  python3 -m json.tool | \
  grep -A3 '"job"'

# Or use jq if available
curl -s http://localhost:9090/api/v1/targets | \
  jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}'
```

**Expected Result**: All 5 targets should show `"health": "up"`
```json
{
  "job": "traefik",
  "health": "up"
}
{
  "job": "backend",
  "health": "up"
}
{
  "job": "postgres",
  "health": "up"
}
{
  "job": "redis",
  "health": "up"
}
{
  "job": "node",
  "health": "up"
}
```

### Step 6: Test Exporter Endpoints
```bash
# PostgreSQL metrics
curl -s http://localhost:9187/metrics | head -5
# Should return: # HELP pg_up ...

# Redis metrics
curl -s http://localhost:9121/metrics | head -5
# Should return: # HELP redis_up ...

# Node metrics
curl -s http://localhost:9100/metrics | head -5
# Should return: # HELP node_cpu_seconds_total ...
```

### Step 7: Run Enhanced Diagnostics
```bash
# Run monitoring-specific diagnostics
./agent/diagnostics.sh monitoring

# Review output
cat agent/server-logs/*_monitoring.txt | tail -50
```

**Check For**:
- ✅ All exporters showing as running
- ✅ Prometheus targets all UP
- ✅ No errors in Promtail logs
- ✅ Reasonable disk usage for monitoring volumes

### Step 8: Query New Metrics
```bash
# Access Prometheus UI: http://178.172.137.7:9090

# Test queries in Prometheus expression browser:

# 1. PostgreSQL connections
pg_stat_activity_count

# 2. Redis memory usage
redis_memory_used_bytes

# 3. Node CPU idle percentage
rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100

# 4. Disk usage percentage
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```

---

## 🔍 Post-Deployment Verification

### Health Check Matrix

| Component | Check Command | Expected Result |
|-----------|---------------|-----------------|
| **PostgreSQL Exporter** | `curl http://localhost:9187/metrics \| grep pg_up` | `pg_up 1` |
| **Redis Exporter** | `curl http://localhost:9121/metrics \| grep redis_up` | `redis_up 1` |
| **Node Exporter** | `curl http://localhost:9100/metrics \| grep node_boot_time` | Returns timestamp |
| **Prometheus** | `curl http://localhost:9090/-/healthy` | `Prometheus is Healthy` |
| **All Targets** | `curl http://localhost:9090/api/v1/targets \| jq '.data.activeTargets[].health' \| sort \| uniq -c` | `5 up` |

### Grafana Dashboard Setup (Optional)

If using local Grafana (`http://178.172.137.7:3000`):

1. **Login**: admin / `${GRAFANA_PASSWORD}`
2. **Verify Datasources**: Configuration → Data Sources
   - ✅ Prometheus (http://prometheus:9090)
   - ✅ Loki (http://loki:3100)
3. **Import Dashboards**:
   - **Traefik**: Dashboard ID `4475` from grafana.com
   - **PostgreSQL**: Dashboard ID `9628`
   - **Redis**: Dashboard ID `763`
   - **Node Exporter Full**: Dashboard ID `1860`
   - **Custom Novamedika**: Upload `dashboards/oac-security-monitoring.json`

---

## ⚠️ Rollback Procedure

If issues occur after deployment:

### Quick Rollback
```bash
cd /opt/novamedika-prod

# Restore previous configuration
cp config/prometheus.yml.backup.YYYYMMDD config/prometheus.yml
cp docker-compose.traefik.prod.yml.backup.YYYYMMDD docker-compose.traefik.prod.yml

# Redeploy with old config
docker-compose -f docker-compose.traefik.prod.yml up -d

# Verify rollback
docker ps | grep exporter  # Should show no exporters
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'  # Should be 2
```

### Partial Rollback (Keep exporters, revert Prometheus config)
```bash
# Only revert Prometheus config
cp config/prometheus.yml.backup.YYYYMMDD config/prometheus.yml

# Restart Prometheus only
docker-compose -f docker-compose.traefik.prod.yml restart prometheus

# Remove exporter containers
docker-compose -f docker-compose.traefik.prod.yml down postgres_exporter redis_exporter node_exporter
```

---

## 📊 Success Criteria

Deployment is successful when ALL of the following are true:

- ✅ 5 Prometheus targets are UP (traefik, backend, postgres, redis, node)
- ✅ All 3 exporter containers are running and healthy
- ✅ Exporter endpoints return valid metrics (HTTP 200)
- ✅ No new errors in container logs
- ✅ Disk usage increase < 1GB after 24 hours
- ✅ Diagnostic script shows all components healthy
- ✅ Can query PostgreSQL, Redis, and Node metrics in Prometheus

---

## 🐛 Troubleshooting

### Issue: Exporter containers won't start

**Check logs**:
```bash
docker logs postgres-exporter
docker logs redis-exporter
docker logs node-exporter
```

**Common causes**:
- Port already in use: `sudo lsof -i :9187` (check for conflicts)
- Environment variables missing: Verify `.env` has `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
- Network issues: `docker network inspect novamedika-prod_traefik-public`

### Issue: Prometheus shows targets as DOWN

**Check connectivity**:
```bash
docker exec prometheus wget -qO- http://postgres_exporter:9187/metrics | head -3
docker exec prometheus wget -qO- http://redis_exporter:9121/metrics | head -3
docker exec prometheus wget -qO- http://node_exporter:9100/metrics | head -3
```

**Fix**: Restart Prometheus
```bash
docker-compose -f docker-compose.traefik.prod.yml restart prometheus
```

### Issue: High memory usage after deployment

**Check resource usage**:
```bash
docker stats --no-stream | grep -E "NAME|exporter|prometheus"
```

**Reduce limits** (if needed):
Edit `docker-compose.traefik.prod.yml` and reduce memory limits for exporters, then redeploy.

---

## 📝 Post-Deployment Tasks

### Immediate (Day 1)
- [ ] Verify all 5 targets are UP in Prometheus
- [ ] Test querying new metrics
- [ ] Run full diagnostics: `./agent/diagnostics.sh all`
- [ ] Document any issues encountered

### Week 1
- [ ] Monitor disk usage growth from new metrics
- [ ] Review metric cardinality (avoid high-cardinality labels)
- [ ] Set up basic alert rules (see MONITORING-STACK-GUIDE.md)
- [ ] Import Grafana dashboards for new exporters

### Month 1
- [ ] Tune alert thresholds based on baseline data
- [ ] Review and optimize retention policies
- [ ] Conduct failover test (restart monitoring stack)
- [ ] Update OAC compliance documentation

---

## 📞 Support

- **Documentation**: `oac/guides/MONITORING-STACK-GUIDE.md`
- **Status Report**: `oac/audits/MONITORING-STATUS-REPORT-2026-05-18.md`
- **Diagnostics**: `agent/diagnostics.sh monitoring`
- **Logs**: `agent/server-logs/<timestamp>_monitoring.txt`

---

**Prepared by**: AI Assistant (Lingma)  
**Reviewed by**: [Your Name]  
**Approved by**: [DevOps Lead]  
**Deployment Date**: _______________  
**Deployed by**: _______________
