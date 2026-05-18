# 📊 Monitoring Stack Guide - Novamedika2

## Overview

This guide covers the complete monitoring stack for Novamedika2, designed to meet **OAC RB Class 3-in** compliance requirements (п.1.5 - monitoring and security event tracking).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Monitoring Stack                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Traefik ──────┐                                    │
│  Backend ──────┼──► Prometheus (9090) ◄── Grafana   │
│  PostgreSQL ───┘         ▲              (3000)      │
│  Redis ──────────────────┘                          │
│  Node (host) ──────────────► Node Exporter (9100)   │
│                                                      │
│  Docker Logs ──► Promtail ──► Loki (3100) ◄──┐     │
│                                              │     │
│                                    Grafana queries Loki │
└─────────────────────────────────────────────────────┘
```

---

## 📍 Service Endpoints

### Production Server (178.172.137.7)

| Service | URL | Purpose | Status |
|---------|-----|---------|--------|
| **Prometheus** | `http://178.172.137.7:9090` | Metrics collection & querying | ✅ Active |
| **Grafana Local** | `http://178.172.137.7:3000` | Visualization (dev profile only) | ⚠️ Dev only |
| **Loki** | `http://178.172.137.7:3100` | Log aggregation | ✅ Active |
| **Loki API** | `http://178.172.137.7:3100/loki/api/v1/query` | Log queries | ✅ Active |
| **Backend Metrics** | `https://api.spravka.novamedika.com/metrics` | FastAPI custom metrics | ✅ Active |
| **Traefik Metrics** | Internal: `traefik:8080/metrics` | HTTP traffic metrics | ✅ Active |

### Recommended Additional Exporters

After deploying the enhanced configuration:

| Exporter | Port | Purpose |
|----------|------|---------|
| **PostgreSQL Exporter** | 9187 | Database performance metrics |
| **Redis Exporter** | 9121 | Cache/memory usage metrics |
| **Node Exporter** | 9100 | Host system metrics (CPU, RAM, disk, network) |

---

## 🔍 Current Metrics Sources

### 1. **Traefik** (`traefik:8080/metrics`)
- HTTP request counts per entrypoint/service
- Request latency distributions
- Error rates (4xx, 5xx)
- Connection counts
- TLS certificate status

**Key Metrics:**
```promql
traefik_entrypoint_requests_total{code=~"5.."}  # 5xx errors
rate(traefik_entrypoint_request_duration_seconds_sum[5m])  # Latency
```

### 2. **Backend** (`backend:8000/metrics`)
- Custom FastAPI application metrics via `/metrics` endpoint
- HTTP request counts with method/endpoint/status labels
- Request latency histograms
- Active request gauge

**Key Metrics:**
```promql
http_requests_total{status=~"5.."}  # Backend errors
rate(http_request_duration_seconds_sum[5m])  # API latency
http_active_requests  # Concurrent requests
```

### 3. **PostgreSQL** (via postgres_exporter - recommended)
- Database size and growth
- Query performance (slow queries)
- Connection pool utilization
- Replication lag (if enabled)
- Table/index statistics

### 4. **Redis** (via redis_exporter - recommended)
- Memory usage and eviction rates
- Hit/miss ratios
- Connected clients
- Command execution times
- Keyspace statistics

### 5. **Node/System** (via node_exporter - recommended)
- CPU utilization per core
- Memory usage (used, cached, buffers)
- Disk I/O and space
- Network throughput
- System load averages

---

## 🛠️ Diagnostic Tools

### Quick Diagnostics Script

Location: `agent/diagnostics.sh`

```bash
# Full diagnostics (all components)
./agent/diagnostics.sh all

# Monitoring stack only
./agent/diagnostics.sh monitoring

# Container status and health checks
./agent/diagnostics.sh status

# All container logs with error filtering
./agent/diagnostics.sh logs

# Specific component
./agent/diagnostics.sh backend
./agent/diagnostics.sh frontend
./agent/diagnostics.sh traefik
./agent/diagnostics.sh db
./agent/diagnostics.sh bot
./agent/diagnostics.sh network
```

**Output:** All diagnostics saved to `agent/server-logs/<timestamp>_*.txt`

### Manual Queries

#### Prometheus Query Examples

Access Prometheus UI: `http://178.172.137.7:9090`

```promql
# High error rate (>5% of requests)
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05

# Backend latency > 1 second
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1

# Traefik 5xx errors in last hour
increase(traefik_entrypoint_requests_total{code=~"5.."}[1h])

# PostgreSQL connections approaching limit
pg_stat_activity_count / current_setting('max_connections')::float > 0.8

# Redis memory usage > 80%
redis_memory_used_bytes / redis_memory_max_bytes > 0.8

# Disk usage > 85%
node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15
```

#### Loki Log Queries

Access via Grafana Explore or Loki API:

```logql
# Backend errors in last hour
{container="backend-prod"} |= "error" |~ "(?i)(fatal|panic|exception)" [1h]

# High latency requests (>2s)
{container="backend-prod"} |= "duration" |~ "\d+s$" [1h]

# Celery task failures
{container="celery-worker-prod"} |= "ERROR" [1h]

# Traefik 5xx responses
{container="traefik-prod"} |= "500" or "502" or "503" [1h]

# Database connection errors
{container="backend-prod"} |= "connection" |= "refused" or "timeout" [1h]
```

---

## 📈 OAC Compliance Requirements

### Monitoring Requirements (п.1.5)

✅ **Implemented:**
- Real-time metric collection (15s intervals)
- Multi-source monitoring (Traefik, Backend, DB, Cache)
- Centralized log aggregation (Loki + Promtail)
- Metric retention: **395 days** (exceeds 1-year requirement)
- Visualization dashboards (Grafana)
- Health check endpoints for all services

✅ **Alerting Rules** (recommended to add):

Create `config/alert_rules.yml`:

```yaml
groups:
  - name: novamedika_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over 5 minutes"

      # Backend latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "95th percentile latency is {{ $value }}s"

      # Disk space
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critically low"
          description: "{{ $labels.mountpoint }} has {{ $value | humanizePercentage }} free"

      # PostgreSQL connections
      - alert: PostgresConnectionsHigh
        expr: pg_stat_activity_count / current_setting('max_connections')::float > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connection pool nearly exhausted"

      # Redis memory
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage high"

      # Container down
      - alert: ContainerDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.instance }} is down"
```

Update `prometheus.yml`:
```yaml
rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

---

## 🚀 Deployment Instructions

### Adding New Exporters

1. **Update docker-compose.traefik.prod.yml**:
   The exporters have been added to the compose file (postgres_exporter, redis_exporter, node_exporter)

2. **Update prometheus.yml**:
   Scrape configs added for all three exporters

3. **Deploy changes**:
   ```bash
   cd /opt/novamedika-prod
   docker-compose -f docker-compose.traefik.prod.yml up -d
   ```

4. **Verify targets**:
   Visit `http://178.172.137.7:9090/targets` - should show 5 UP targets

### Grafana Dashboard Setup

1. **Access Grafana**: `http://178.172.137.7:3000`
   - Default credentials: admin / `${GRAFANA_PASSWORD}` (from .env)

2. **Add Data Sources** (auto-provisioned):
   - Prometheus: `http://prometheus:9090`
   - Loki: `http://loki:3100`

3. **Import Dashboards**:
   - Traefik: Use official dashboard ID `4475` from Grafana.com
   - PostgreSQL: Import ID `9628`
   - Redis: Import ID `763`
   - Node Exporter: Import ID `1860`
   - Custom Novamedika: See `dashboards/oac-security-monitoring.json`

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Loki returns 404 at root URL**
- **Expected behavior** - Loki doesn't serve UI at `/`
- Use `/loki/api/v1/query` for API access
- Access logs via Grafana Explore panel

#### 2. **Prometheus target DOWN**
```bash
# Check container health
docker ps --filter name=prometheus

# Check Prometheus logs
docker logs prometheus --tail=100

# Verify network connectivity
docker exec prometheus wget -qO- http://backend:8000/metrics | head -5
```

#### 3. **Missing metrics**
```bash
# Check if exporter is running
docker ps | grep exporter

# Test exporter endpoint
curl http://localhost:9187/metrics  # PostgreSQL
curl http://localhost:9121/metrics  # Redis
curl http://localhost:9100/metrics  # Node

# Check Prometheus scrape errors
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health=="down")'
```

#### 4. **High disk usage from metrics/logs**
```bash
# Check volume sizes
du -sh /var/lib/docker/volumes/novamedika-prod_*-data/_data

# Reduce retention (if needed)
# Edit prometheus.yml: storage.tsdb.retention.time=180d
docker restart prometheus

# Clean old Loki chunks
docker exec loki rm -rf /loki/chunks/*
docker restart loki
```

#### 5. **Grafana initialization failure (451 error)**
See memory: `Grafana初始化失败处理方案`
- Clear grafana-data volume
- Remove references to unconfigured datasources (e.g., Tempo)
- Restart Grafana container

---

## 📊 Key Performance Indicators (KPIs)

### Application Health
- **API Availability**: > 99.5% uptime
- **Error Rate**: < 1% of total requests
- **P95 Latency**: < 2 seconds
- **Active Users**: Monitor concurrent sessions

### Infrastructure Health
- **CPU Usage**: < 70% average
- **Memory Usage**: < 80% per container
- **Disk Usage**: < 85% (alert at 80%)
- **Database Connections**: < 80% of max_connections

### Security Monitoring
- **Failed Login Attempts**: Alert on > 10/min from single IP
- **Rate Limit Triggers**: Monitor 429 responses
- **TLS Certificate Expiry**: Alert 30 days before expiration
- **Unauthorized Access**: Track 403 responses

---

## 📝 Maintenance Tasks

### Weekly
```bash
# Run full diagnostics
./agent/diagnostics.sh all

# Check disk usage
df -h /var/lib/docker

# Review error logs
cat agent/server-logs/*_errors-only.txt | tail -50
```

### Monthly
```bash
# Clean Docker resources
docker system prune -af --volumes

# Review metric retention
curl http://localhost:9090/api/v1/status/tsdb

# Backup Grafana dashboards
docker cp grafana-local:/var/lib/grafana/dashboards ./backup/grafana-$(date +%Y%m%d)
```

### Quarterly
- Review and update alert thresholds
- Audit access logs for anomalies
- Test backup/restore procedures
- Update monitoring stack versions

---

## 📚 Additional Resources

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/
- **Loki LogQL**: https://grafana.com/docs/loki/latest/logql/
- **OAC Compliance Docs**: `oac/docs/07-ib-monitoring-reglament.md`
- **Project Monitoring Config**: `config/prometheus.yml`, `config/loki-config.yaml`

---

**Last Updated**: May 18, 2026  
**Maintainer**: DevOps Team  
**Compliance**: OAC RB Class 3-in (п.1.5)
