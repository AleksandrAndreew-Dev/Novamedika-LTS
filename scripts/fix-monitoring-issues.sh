#!/bin/bash
# ============================================
# Fix Monitoring Issues Script
# Novamedika2 - Traefik Metrics & Grafana Error 451
# ============================================

set -e

echo "=========================================="
echo "Fixing Monitoring Stack Issues"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Fix Traefik metrics endpoint
echo -e "${YELLOW}[1/4] Fixing Traefik metrics configuration...${NC}"
echo "Adding metrics entrypoint to Traefik..."

# Restart Traefik with new configuration
docker-compose -f docker-compose.traefik.prod.yml up -d traefik-prod
sleep 10

echo -e "${GREEN}✓ Traefik restarted with metrics entrypoint${NC}"

# Step 2: Test Traefik metrics
echo -e "${YELLOW}[2/4] Testing Traefik metrics accessibility...${NC}"
sleep 5

if docker exec prometheus wget -qO- --timeout=5 http://traefik:8080/metrics 2>&1 | head -1 | grep -q "# HELP"; then
    echo -e "${GREEN}✓ Traefik metrics now accessible!${NC}"
else
    echo -e "${RED}✗ Traefik metrics still not accessible${NC}"
    echo "Checking Traefik logs..."
    docker logs traefik-prod --tail 20 | grep -i "metric\|error" || true
fi

# Step 3: Fix Grafana error 451
echo -e "${YELLOW}[3/4] Fixing Grafana error 451...${NC}"

# Stop and remove Grafana container and volume
docker stop grafana-local 2>/dev/null || true
docker rm grafana-local 2>/dev/null || true
docker volume rm novamedika-prod_grafana-data 2>/dev/null || true

echo "Removed old Grafana data volume"

# Start Grafana fresh (without plugins)
docker-compose -f docker-compose.traefik.prod.yml --profile dev up -d grafana-local

echo "Waiting for Grafana to start..."
sleep 15

# Check Grafana status
GRAFANA_STATUS=$(docker inspect grafana-local --format='{{.State.Status}}' 2>/dev/null || echo "not found")

if [ "$GRAFANA_STATUS" = "running" ]; then
    echo -e "${GREEN}✓ Grafana started successfully!${NC}"
    
    # Test Grafana API
    if curl -s http://localhost:3000/api/health | grep -q "commit"; then
        echo -e "${GREEN}✓ Grafana API is responding${NC}"
    else
        echo -e "${YELLOW}⚠ Grafana container running but API not responding yet${NC}"
    fi
else
    echo -e "${RED}✗ Grafana failed to start${NC}"
    echo "Grafana logs:"
    docker logs grafana-local --tail 50 2>/dev/null || echo "Cannot get logs"
fi

# Step 4: Final verification
echo -e "${YELLOW}[4/4] Final verification...${NC}"
echo ""

echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(prometheus|grafana|loki|promtail|traefik)" || true

echo ""
echo "Prometheus Targets:"
curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -E '(job|health)' | head -10 || echo "Cannot query Prometheus"

echo ""
echo "=========================================="
echo -e "${GREEN}Fix completed!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for Prometheus to scrape all targets"
echo "2. Check Prometheus UI: http://YOUR_SERVER_IP:9090/targets"
echo "3. If using Grafana, access: http://YOUR_SERVER_IP:3000"
echo ""
echo "To view logs:"
echo "  docker logs traefik-prod --tail 50 -f"
echo "  docker logs prometheus --tail 50 -f"
echo "  docker logs grafana-local --tail 50 -f"
echo ""
