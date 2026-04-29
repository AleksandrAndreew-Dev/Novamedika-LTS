# Pharmacist Dashboard Path-Based Routing - Deployment Guide

## 📋 Overview

This guide documents the migration from subdomain-based routing (`pharmacist.spravka.novamedika.com`) to path-based routing (`spravka.novamedika.com/pharmacist`) for the pharmacist dashboard.

**Date**: 2026-04-29  
**Status**: ✅ Configuration Updated, Ready for Deployment

---

## 🔍 Current Status Analysis

### Server Logs Review (2026-04-29 10:12:02)

#### ✅ What's Working
1. **All containers healthy**: backend-prod, frontend-prod, traefik-prod, postgres-prod, redis-prod, celery-worker-prod
2. **HTTPS operational**: Both main site and pharmacist subdomain return HTTP 200
3. **CSP headers correct**: Includes `'unsafe-eval'` for Telegram SDK initialization
4. **DNS resolution**: All domains point to 178.172.137.7
5. **Ports open**: 80 (HTTP) and 443 (HTTPS) listening via Traefik
6. **Frontend mode detection**: Already supports path-based routing in `App.jsx`

#### ⚠️ Issues Identified
1. **Bot configuration**: Default URL still uses subdomain format
2. **Traefik routing**: Only configured for subdomain, not path-based
3. **Environment variable**: May need update on production server

---

## 🛠️ Changes Made

### 1. Bot Keyboard Configuration
**File**: `backend/src/bot/handlers/common_handlers/keyboards.py`

**Changes**:
- Updated `generate_pharmacist_webapp_url()` default URL
- Updated `get_pharmacist_inline_keyboard()` default URL
- Changed from: `https://pharmacist.spravka.novamedika.com`
- Changed to: `https://spravka.novamedika.com/pharmacist`

**Impact**: When pharmacists click "💼 Панель фармацевта" in Telegram bot, they'll now be directed to the path-based URL with JWT token.

### 2. Traefik Routing Configuration
**File**: `docker-compose.traefik.prod.yml`

**Changes**:
```yaml
# Main site - excludes /pharmacist path
- "traefik.http.routers.frontend.rule=Host(`spravka.novamedika.com`) && !PathPrefix(`/pharmacist`)"

# Pharmacist dashboard - path-based on same host
- "traefik.http.routers.pharmacist.rule=Host(`spravka.novamedika.com`) && PathPrefix(`/pharmacist`)"

# Backward compatibility - old subdomain still works
- "traefik.http.routers.pharmacist-subdomain.rule=Host(`pharmacist.spravka.novamedika.com`)"
```

**Impact**: 
- Requests to `spravka.novamedika.com/pharmacist*` route to frontend container
- Requests to `pharmacist.spravka.novamedika.com` still work (backward compatible)
- All other paths on `spravka.novamedika.com` serve the main search app

### 3. Frontend Configuration
**No changes needed** - already supports path-based routing:
- `frontend/src/App.jsx`: Detects `/pharmacist` path prefix
- `frontend/nginx.conf`: SPA routing handles all paths correctly

---

## 🚀 Deployment Instructions

### Step 1: Update Environment Variables on Server

SSH to production server and edit `.env`:

```bash
ssh novamedika@your-server
cd /opt/novamedika-prod
nano .env
```

Ensure this line exists:
```bash
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

Save and exit (Ctrl+X, Y, Enter).

### Step 2: Pull Latest Code

```bash
cd /opt/novamedika-prod
git pull origin main
```

Verify the changes:
```bash
git log --oneline -5
# Should show recent commits with keyboard and traefik updates
```

### Step 3: Rebuild Backend Image

The bot code is in the backend image, so rebuild it:

```bash
docker compose -f docker-compose.traefik.prod.yml build backend
```

This will:
- Build new backend image with updated keyboard URLs
- Tag it as `ghcr.io/aleksandrandreew-dev/novamedika-lts/backend:latest`

### Step 4: Deploy Updated Services

```bash
docker compose -f docker-compose.traefik.prod.yml up -d backend traefik
```

This restarts:
- **backend**: New image with updated bot keyboards
- **traefik**: New routing rules for path-based access

### Step 5: Verify Deployment

#### Check Container Status
```bash
docker ps
# All containers should show "healthy" or "Up" status
```

#### Test Path-Based Routing
```bash
# Test pharmacist dashboard via path
curl -I https://spravka.novamedika.com/pharmacist

# Expected: HTTP/2 200 with CSP headers
```

Expected response headers:
```
HTTP/2 200
content-security-policy: default-src 'self'; script-src 'self' https://telegram.org ... 'unsafe-eval' ...
frame-ancestors: 'self' https://t.me https://web.telegram.org
content-type: text/html
```

#### Test Backward Compatibility
```bash
# Old subdomain should still work
curl -I https://pharmacist.spravka.novamedika.com

# Expected: HTTP/2 200
```

#### Test Main Site Still Works
```bash
# Main search page should work (not affected by /pharmacist path)
curl -I https://spravka.novamedika.com/

# Expected: HTTP/2 200
```

### Step 6: Test Telegram WebApp Integration

1. **Open Telegram bot** (@your_bot_username)
2. **Click "/start"** or any command that shows pharmacist keyboard
3. **Click "💼 Панель фармацевта" button**
4. **Verify**:
   - WebApp opens at `https://spravka.novamedika.com/pharmacist?token=eyJ...`
   - URL contains JWT token in query parameters
   - Dashboard loads without errors
   - Browser console shows no CORS or CSP violations

5. **Check browser console** (F12):
   ```javascript
   // Should see Telegram WebApp initialized
   console.log(window.Telegram.WebApp.initData);
   
   // Should have token in localStorage after login
   console.log(localStorage.getItem('pharmacist_token'));
   ```

### Step 7: Monitor Logs

```bash
# Watch Traefik access logs
docker logs -f traefik-prod | grep pharmacist

# Watch backend logs for bot activity
docker logs -f backend-prod | grep -i webhook

# Watch frontend for any errors
docker logs -f frontend-prod
```

Look for:
- ✅ `200` status codes for `/pharmacist` requests
- ✅ No `404` errors on pharmacist routes
- ✅ Successful WebSocket connections
- ✅ No CSP violations in browser console

---

## 🧪 Testing Checklist

After deployment, verify all scenarios:

### Direct Access
- [ ] `https://spravka.novamedika.com/pharmacist` → Loads dashboard
- [ ] `https://spravka.novamedika.com/pharmacist?token=xxx` → Auto-authenticates
- [ ] `https://pharmacist.spravka.novamedika.com` → Still works (backward compat)

### Telegram Bot Integration
- [ ] Pharmacist sees "💼 Панель фармацевта" button
- [ ] Button opens WebApp at correct URL with token
- [ ] WebApp initializes without errors
- [ ] User data displays correctly (first_name, etc.)
- [ ] API calls succeed (check Network tab)

### Functionality
- [ ] Dashboard loads questions list
- [ ] Can switch online/offline status
- [ ] Can answer user questions
- [ ] Statistics display correctly
- [ ] History view works

### Security Headers
- [ ] CSP includes `'unsafe-eval'` for Telegram SDK
- [ ] CSP allows `frame-ancestors 'self' https://t.me https://web.telegram.org`
- [ ] HSTS header present
- [ ] X-Frame-Options set to SAMEORIGIN

### Performance
- [ ] Page load time < 2 seconds
- [ ] No excessive API retries
- [ ] WebSocket connection stable

---

## 🔧 Troubleshooting

### Issue: 404 on /pharmacist path

**Symptoms**: 
```bash
curl -I https://spravka.novamedika.com/pharmacist
# Returns: HTTP/2 404
```

**Solution**:
1. Check Traefik routing rules:
   ```bash
   docker inspect traefik-prod | grep -A 5 pharmacist
   ```

2. Verify Traefik labels in docker-compose:
   ```bash
   cat docker-compose.traefik.prod.yml | grep -A 3 "pharmacist.rule"
   ```

3. Restart Traefik:
   ```bash
   docker compose -f docker-compose.traefik.prod.yml restart traefik
   ```

4. Check Traefik logs:
   ```bash
   docker logs traefik-prod 2>&1 | grep -i "pharmacist\|route\|router"
   ```

### Issue: Frontend shows main search instead of dashboard

**Symptoms**: Opening `/pharmacist` shows drug search interface

**Solution**:
1. Check frontend mode detection:
   ```javascript
   // In browser console
   console.log(window.location.pathname); // Should start with /pharmacist
   console.log(localStorage.getItem('app_mode')); // Should be 'pharmacist'
   ```

2. Clear localStorage and reload:
   ```javascript
   localStorage.removeItem('app_mode');
   location.reload();
   ```

3. Verify App.jsx logic:
   ```bash
   docker exec frontend-prod cat /usr/share/nginx/html/index.html | grep -i pharmacist
   ```

### Issue: JWT Token Not Working

**Symptoms**: 
- WebApp opens but shows "Unauthorized"
- API calls return 401/403

**Solution**:
1. Check token in URL:
   ```javascript
   const params = new URLSearchParams(window.location.search);
   console.log(params.get('token')); // Should exist
   ```

2. Verify token extraction in frontend:
   ```bash
   # Check if frontend code extracts token
   docker exec frontend-prod cat /usr/share/nginx/html/assets/index-*.js | grep -o "token" | head -5
   ```

3. Check backend auth endpoint:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://api.spravka.novamedika.com/api/pharmacist/me
   ```

4. Verify bot generates tokens correctly:
   ```bash
   docker logs backend-prod | grep -i "generate.*token\|webapp.*url"
   ```

### Issue: CSP Violations

**Symptoms**: Browser console shows CSP errors

**Solution**:
1. Check current CSP headers:
   ```bash
   curl -I https://spravka.novamedika.com/pharmacist | grep -i content-security-policy
   ```

2. Verify required directives:
   - `script-src` must include `'unsafe-eval'` (for Telegram SDK)
   - `frame-ancestors` must include `https://t.me https://web.telegram.org`
   - `connect-src` must include API domain

3. Update Traefik CSP middleware if needed:
   ```yaml
   # In docker-compose.traefik.prod.yml
   - "traefik.http.middlewares.security-headers.headers.contentsecuritypolicy=default-src 'self'; script-src 'self' https://telegram.org https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval'; ..."
   ```

4. Restart Traefik:
   ```bash
   docker compose -f docker-compose.traefik.prod.yml restart traefik
   ```

### Issue: WebSocket Connection Fails

**Symptoms**: 
- Dashboard loads but real-time updates don't work
- Console shows WebSocket errors

**Solution**:
1. Check WebSocket URL:
   ```javascript
   console.log(import.meta.env.VITE_WS_URL_PHARMACIST);
   // Should be: wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
   ```

2. Verify CSP allows WebSocket:
   ```bash
   curl -I https://spravka.novamedika.com/pharmacist | grep connect-src
   # Should include: wss://api.spravka.novamedika.com
   ```

3. Test WebSocket manually:
   ```bash
   # Install wscat: npm install -g wscat
   wscat -c wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
   ```

---

## 📊 Monitoring & Maintenance

### Daily Checks
```bash
# Container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Resource usage
docker stats --no-stream

# Error logs
docker logs --tail 50 backend-prod 2>&1 | grep -i error
docker logs --tail 50 traefik-prod 2>&1 | grep -i error
```

### Weekly Checks
```bash
# SSL certificate expiry
echo | openssl s_client -connect spravka.novamedika.com:443 2>/dev/null | openssl x509 -noout -dates

# Disk usage
df -h /var/lib/docker

# Traefik route inspection
docker exec traefik-prod traefik healthcheck
```

### Monthly Tasks
1. Review Traefik access logs for unusual patterns
2. Check Let's Encrypt certificate renewal (auto-renews at 30 days before expiry)
3. Update Docker images if newer versions available
4. Review bot analytics for WebApp usage statistics

---

## 🔄 Rollback Plan

If issues occur after deployment:

### Quick Rollback (5 minutes)
```bash
cd /opt/novamedika-prod

# Restore previous docker-compose
cp docker-compose.traefik.prod.yml.backup docker-compose.traefik.prod.yml

# Restart services
docker compose -f docker-compose.traefik.prod.yml up -d traefik backend

# Verify
curl -I https://pharmacist.spravka.novamedika.com
```

### Full Rollback (if needed)
```bash
# Revert git changes
git reset --hard HEAD~1

# Rebuild and redeploy
docker compose -f docker-compose.traefik.prod.yml build backend
docker compose -f docker-compose.traefik.prod.yml up -d
```

---

## 📝 Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-04-29 | 1.0 | Initial path-based routing implementation | Dev Team |
| - | - | Updated bot keyboards to use path-based URL | - |
| - | - | Configured Traefik for /pharmacist path routing | - |
| - | - | Maintained backward compatibility with subdomain | - |

---

## 📞 Support

If you encounter issues:

1. **Check this guide** - Most issues have troubleshooting steps above
2. **Review server logs** - Use commands in Monitoring section
3. **Test endpoints manually** - Use curl commands provided
4. **Contact team** - Share:
   - Error messages from browser console
   - Relevant log excerpts
   - Steps to reproduce

---

## ✅ Success Criteria

Deployment is successful when:

- [x] Configuration files updated (bot keyboards, Traefik)
- [ ] Environment variables set on production server
- [ ] Images rebuilt and deployed
- [ ] Path-based routing returns HTTP 200
- [ ] Subdomain routing still works (backward compat)
- [ ] Telegram WebApp opens at correct URL
- [ ] JWT authentication works
- [ ] All functionality tested
- [ ] No errors in logs
- [ ] Performance acceptable (< 2s load time)

---

**Last Updated**: 2026-04-29  
**Next Review**: 2026-05-29
