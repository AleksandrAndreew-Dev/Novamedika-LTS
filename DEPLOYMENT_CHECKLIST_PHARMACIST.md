# Pharmacist Dashboard Path-Based Routing - Deployment Checklist

## 📋 Pre-Deployment Preparation

### Code Review
- [x] Backend bot keyboards updated (`keyboards.py`)
- [x] Traefik routing configuration updated (`docker-compose.traefik.prod.yml`)
- [x] Frontend already supports path-based routing (no changes needed)
- [x] All files validated with `get_problems` - no syntax errors
- [x] Documentation created (3 markdown files)

### Server Preparation
- [ ] SSH access to production server confirmed
- [ ] Current `.env` file backed up
- [ ] Current `docker-compose.traefik.prod.yml` backed up
- [ ] Git repository accessible from server
- [ ] Docker credentials valid (for pulling from ghcr.io)

---

## 🚀 Deployment Steps

### Step 1: Connect to Server
```bash
ssh novamedika@your-server-ip
cd /opt/novamedika-prod
```

**Verify**:
- [ ] Current directory is `/opt/novamedika-prod`
- [ ] User has sudo/docker permissions
- [ ] `.env` file exists

---

### Step 2: Backup Current Configuration
```bash
# Backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Backup docker-compose
cp docker-compose.traefik.prod.yml docker-compose.traefik.prod.yml.backup.$(date +%Y%m%d_%H%M%S)
```

**Verify**:
- [ ] Backup files created with timestamps
- [ ] Can restore from backup if needed

---

### Step 3: Update Environment Variables
```bash
# Edit .env file
nano .env
```

Find and update (or add if missing):
```bash
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

Save: `Ctrl+X`, then `Y`, then `Enter`

**Verify**:
```bash
grep PHARMACIST_DASHBOARD_URL .env
```
Expected output:
```
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

- [ ] Variable set correctly
- [ ] No extra spaces or quotes

---

### Step 4: Pull Latest Code
```bash
git pull origin main
```

**Verify**:
```bash
git log --oneline -3
```
Should show recent commits including:
- Bot keyboard URL updates
- Traefik routing changes

- [ ] Git pull successful
- [ ] Latest commits present
- [ ] No merge conflicts

---

### Step 5: Rebuild Backend Image
```bash
docker compose -f docker-compose.traefik.prod.yml build backend
```

This may take 2-5 minutes.

**Expected output**:
```
Step X/Y : ...
Successfully built <image-id>
Successfully tagged ghcr.io/aleksandrandreew-dev/novamedika-lts/backend:latest
```

**Verify**:
- [ ] Build completed without errors
- [ ] New image tagged correctly
- [ ] No Python import errors in output

---

### Step 6: Deploy Updated Services
```bash
docker compose -f docker-compose.traefik.prod.yml up -d backend traefik
```

**Expected output**:
```
Recreating backend-prod ... done
Recreating traefik-prod ... done
```

**Verify**:
```bash
docker ps
```

All containers should show:
- `backend-prod`: Up X seconds (healthy)
- `traefik-prod`: Up X seconds
- `frontend-prod`: Up X minutes (healthy)
- Other containers: healthy

- [ ] Services restarted successfully
- [ ] No containers in "Restarting" state
- [ ] Health checks passing

---

### Step 7: Wait for Health Checks
```bash
# Wait 30-60 seconds for services to fully initialize
sleep 60

# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Expected**:
```
NAMES                STATUS
backend-prod         Up 1 minute (healthy)
traefik-prod         Up 1 minute
frontend-prod        Up 5 minutes (healthy)
postgres-prod        Up 10 minutes (healthy)
redis-prod           Up 10 minutes (healthy)
celery-worker-prod   Up 10 minutes (healthy)
```

- [ ] All containers healthy
- [ ] No restarting loops
- [ ] Backend health check passes

---

## ✅ Post-Deployment Verification

### Test 1: Path-Based Routing
```bash
curl -I https://spravka.novamedika.com/pharmacist
```

**Expected Response**:
```
HTTP/2 200
content-type: text/html
content-security-policy: default-src 'self'; script-src 'self' ... 'unsafe-eval' ...
frame-ancestors: 'self' https://t.me https://web.telegram.org
```

- [ ] HTTP status 200
- [ ] CSP headers present
- [ ] `'unsafe-eval'` in script-src
- [ ] `https://t.me` in frame-ancestors

---

### Test 2: Backward Compatibility (Subdomain)
```bash
curl -I https://pharmacist.spravka.novamedika.com
```

**Expected Response**:
```
HTTP/2 200
content-type: text/html
```

- [ ] Subdomain still works
- [ ] Returns HTML content
- [ ] No redirect loops

---

### Test 3: Main Site Unaffected
```bash
curl -I https://spravka.novamedika.com/
```

**Expected Response**:
```
HTTP/2 200
content-type: text/html
```

- [ ] Main site returns 200
- [ ] Not redirected to /pharmacist
- [ ] Same CSP headers

---

### Test 4: API Endpoints
```bash
# Test health endpoint
curl https://api.spravka.novamedika.com/health

# Expected: {"status":"ok"}

# Test pharmacist auth endpoint (without token - should return 401)
curl https://api.spravka.novamedika.com/api/pharmacist/me

# Expected: {"detail":"Not authenticated"} or similar 401 response
```

- [ ] API health check works
- [ ] Auth endpoint requires token (security check)
- [ ] No 500 errors

---

### Test 5: Telegram Bot Integration

**Manual Testing Required**:

1. **Open Telegram** on mobile or desktop
2. **Navigate to bot** (@your_bot_username)
3. **Send `/start`** command
4. **Verify keyboard appears** with pharmacist buttons
5. **Click "💼 Панель фармацевта"** button
6. **WebApp should open** at:
   ```
   https://spravka.novamedika.com/pharmacist?token=eyJhbG...
   ```

**In WebApp Browser Console** (if testing on desktop):
```javascript
// Check URL
console.log(window.location.href);
// Should contain: spravka.novamedika.com/pharmacist?token=...

// Check Telegram SDK
console.log(window.Telegram.WebApp.initData);
// Should have user data

// Check localStorage after login
console.log(localStorage.getItem('pharmacist_token'));
// Should have JWT token

// Check mode detection
console.log(localStorage.getItem('app_mode'));
// Should be: 'pharmacist'
```

**Verify**:
- [ ] Button appears in bot keyboard
- [ ] WebApp opens without errors
- [ ] URL contains `/pharmacist` path
- [ ] URL contains `?token=` parameter
- [ ] Dashboard loads (not search interface)
- [ ] User data displays correctly
- [ ] No console errors
- [ ] API calls succeed (check Network tab)

---

### Test 6: Functionality Tests

**In Pharmacist Dashboard**:

- [ ] Can view questions list
- [ ] Can switch online/offline status
- [ ] Can answer user questions
- [ ] Statistics display correctly
- [ ] History view works
- [ ] Logout/login works
- [ ] Real-time updates via WebSocket

**Check WebSocket**:
```javascript
// In browser console
const ws = new WebSocket('wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist');
ws.onopen = () => console.log('WebSocket connected');
ws.onerror = (e) => console.error('WebSocket error', e);
```

- [ ] WebSocket connects successfully
- [ ] No connection errors
- [ ] Receives real-time updates

---

### Test 7: Error Handling

**Simulate errors**:

1. **Invalid token**:
   ```bash
   curl -H "Authorization: Bearer invalid_token" \
        https://api.spravka.novamedika.com/api/pharmacist/me
   # Should return 401, not 500
   ```

2. **Expired token** (wait 24 hours or manually expire):
   - Dashboard should redirect to login
   - Should not crash

3. **Network interruption**:
   - Disconnect/reconnect internet
   - Dashboard should handle gracefully
   - Should attempt reconnection

**Verify**:
- [ ] Invalid tokens return 401
- [ ] Expired tokens handled gracefully
- [ ] Network errors don't crash app
- [ ] User-friendly error messages

---

## 📊 Monitoring Setup

### Log Monitoring
```bash
# Tail backend logs
docker logs -f backend-prod | grep -i "pharmacist\|auth\|token"

# Tail Traefik logs
docker logs -f traefik-prod | grep -i "pharmacist\|route"

# Tail frontend logs
docker logs -f frontend-prod
```

**Watch for**:
- [ ] No repeated 404 errors
- [ ] No authentication failures (after initial setup)
- [ ] No CSP violations
- [ ] No WebSocket disconnections

---

### Resource Monitoring
```bash
# Check resource usage
docker stats --no-stream

# Check disk space
df -h /var/lib/docker

# Check memory
free -h
```

**Expected**:
- Backend: < 500MB memory
- Frontend: < 100MB memory
- Traefik: < 50MB memory
- Disk usage: < 80% capacity

- [ ] Resources within limits
- [ ] No memory leaks
- [ ] Sufficient disk space

---

## 🔍 Troubleshooting During Deployment

### If Backend Fails to Start
```bash
# Check logs
docker logs backend-prod

# Common issues:
# - Database connection failed
# - Missing environment variables
# - Python import errors

# Fix and restart
docker compose -f docker-compose.traefik.prod.yml up -d backend
```

### If Traefik Routing Doesn't Work
```bash
# Inspect Traefik configuration
docker inspect traefik-prod | grep -A 10 "pharmacist"

# Check Traefik dashboard (if enabled)
# https://traefik.spravka.novamedika.com/dashboard/

# Restart Traefik
docker compose -f docker-compose.traefik.prod.yml restart traefik
```

### If Frontend Shows Wrong Page
```bash
# Clear browser cache
# Hard reload: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# Clear localStorage
localStorage.clear();
location.reload();

# Check nginx config
docker exec frontend-prod cat /etc/nginx/conf.d/default.conf
```

### If Token Authentication Fails
```bash
# Check token generation in bot
docker logs backend-prod | grep -i "generate.*webapp\|token"

# Verify token extraction in frontend
# Open browser console → Network tab → Check API requests
# Look for Authorization header

# Test token manually
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.spravka.novamedika.com/api/pharmacist/me
```

---

## 🎯 Success Criteria

Deployment is **SUCCESSFUL** when ALL of the following are true:

- [x] Code changes committed and pushed
- [ ] Environment variable updated on server
- [ ] Backend image rebuilt successfully
- [ ] Services deployed without errors
- [ ] All containers healthy
- [ ] `curl -I https://spravka.novamedika.com/pharmacist` returns 200
- [ ] `curl -I https://pharmacist.spravka.novamedika.com` returns 200
- [ ] `curl -I https://spravka.novamedika.com/` returns 200
- [ ] Telegram bot button opens correct URL with token
- [ ] Dashboard loads and authenticates
- [ ] API calls work with JWT token
- [ ] WebSocket connection established
- [ ] No errors in browser console
- [ ] No errors in container logs
- [ ] All functionality tested
- [ ] Performance acceptable (< 2s load time)

---

## 📝 Rollback Plan (If Needed)

### Quick Rollback (< 5 minutes)
```bash
cd /opt/novamedika-prod

# Restore previous docker-compose
ls -la docker-compose.traefik.prod.yml.backup.*
# Pick the most recent backup
cp docker-compose.traefik.prod.yml.backup.YYYYMMDD_HHMMSS docker-compose.traefik.prod.yml

# Restart services
docker compose -f docker-compose.traefik.prod.yml up -d traefik backend

# Verify rollback
curl -I https://pharmacist.spravka.novamedika.com
```

### Full Rollback
```bash
# Revert git changes
git reset --hard HEAD~1

# Rebuild backend
docker compose -f docker-compose.traefik.prod.yml build backend

# Redeploy
docker compose -f docker-compose.traefik.prod.yml up -d

# Restore .env if changed
cp .env.backup.YYYYMMDD_HHMMSS .env
docker compose -f docker-compose.traefik.prod.yml up -d backend
```

---

## 📞 Post-Deployment Support

### Monitor for 24 Hours
- [ ] Check logs every 4 hours
- [ ] Monitor error rates
- [ ] Track user feedback
- [ ] Watch for unusual traffic patterns

### Collect Metrics
- [ ] Number of WebApp openings
- [ ] Authentication success rate
- [ ] Average page load time
- [ ] WebSocket connection stability

### Document Issues
If any problems occur:
1. Document the issue
2. Note the solution
3. Update this checklist
4. Share with team

---

## ✅ Sign-Off

**Deployed By**: _________________  
**Date**: _________________  
**Time Started**: _________________  
**Time Completed**: _________________  

**Verification Completed By**: _________________  
**Date**: _________________  

**Notes**:
_________________________________________________
_________________________________________________
_________________________________________________

---

**Checklist Version**: 1.0  
**Last Updated**: 2026-04-29  
**Next Review**: After first month of operation
