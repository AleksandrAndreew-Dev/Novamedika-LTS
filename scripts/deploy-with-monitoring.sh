#!/bin/bash
# ============================================
# Production Deployment Script with Monitoring
# Novamedika2 - OAC Compliance Monitoring Stack
# ============================================

set -e

echo "=========================================="
echo "Novamedika2 Production Deployment"
echo "Including Monitoring Stack (OAC Compliance)"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Stop old monitoring stack if exists
echo -e "${YELLOW}[1/7] Stopping old monitoring stack...${NC}"
if docker-compose -f docker-compose.monitoring.yml ps 2>/dev/null | grep -q "Up"; then
    docker-compose -f docker-compose.monitoring.yml down --remove-orphans
    echo -e "${GREEN}✓ Old monitoring stack stopped${NC}"
else
    echo -e "${GREEN}✓ No old monitoring stack found${NC}"
fi

# Step 2: Clean up old networks
echo -e "${YELLOW}[2/7] Cleaning up old networks...${NC}"
docker network rm novamedika-prod_monitoring-network 2>/dev/null || true
echo -e "${GREEN}✓ Network cleanup completed${NC}"

# Step 3: Pull latest images
echo -e "${YELLOW}[3/7] Pulling latest images...${NC}"
docker-compose -f docker-compose.traefik.prod.yml pull
echo -e "${GREEN}✓ Images pulled successfully${NC}"

# Step 4: Restart production stack
echo -e "${YELLOW}[4/7] Restarting production stack with monitoring...${NC}"
docker-compose -f docker-compose.traefik.prod.yml down
docker-compose -f docker-compose.traefik.prod.yml up -d
echo -e "${GREEN}✓ Production stack restarted${NC}"

# Step 5: Wait for services to be healthy
echo -e "${YELLOW}[5/7] Waiting for services to become healthy...${NC}"
sleep 30

# Step 6: Verify monitoring stack
echo -e "${YELLOW}[6/7] Verifying monitoring stack...${NC}"
echo ""
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(prometheus|grafana|loki|promtail|backend|traefik)" || true
echo ""

# Step 7: Test Prometheus connectivity
echo -e "${YELLOW}[7/7] Testing Prometheus targets...${NC}"
sleep 5

echo "Testing Traefik metrics endpoint..."
if docker exec prometheus wget -qO- --timeout=5 http://traefik:8080/metrics 2>&1 | head -1 | grep -q "# HELP"; then
    echo -e "${GREEN}✓ Traefik metrics accessible${NC}"
else
    echo -e "${RED}✗ Traefik metrics NOT accessible${NC}"
fi

echo "Testing Backend metrics endpoint..."
if docker exec prometheus wget -qO- --timeout=5 http://backend:8000/metrics 2>&1 | head -1 | grep -q "# HELP"; then
    echo -e "${GREEN}✓ Backend metrics accessible${NC}"
else
    echo -e "${YELLOW}⚠ Backend metrics not available (may need prometheus-fastapi-instrumentator)${NC}"
fi

echo ""
echo "Prometheus Targets Health:"
curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -E '(job|health)' | head -10 || echo "Cannot query Prometheus yet"

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment completed!${NC}"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  - Prometheus: http://YOUR_SERVER_IP:9090"
echo "  - Loki:       http://YOUR_SERVER_IP:3100"
echo "  - Grafana:    http://YOUR_SERVER_IP:3000 (if --profile dev used)"
echo ""
echo "To start Grafana (for development):"
echo "  docker-compose -f docker-compose.traefik.prod.yml --profile dev up -d grafana-local"
echo ""
echo "Check logs:"
echo "  docker logs prometheus --tail 50"
echo "  docker logs loki --tail 50"
echo ""
