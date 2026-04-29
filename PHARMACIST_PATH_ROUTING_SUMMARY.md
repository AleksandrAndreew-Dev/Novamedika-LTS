# Pharmacist Dashboard - Path-Based Routing Summary

## 🎯 Objective
Migrate pharmacist dashboard from subdomain (`pharmacist.spravka.novamedika.com`) to path-based routing (`spravka.novamedika.com/pharmacist`).

---

## ✅ What Was Done

### 1. Code Changes

#### Backend (Bot Configuration)
**File**: `backend/src/bot/handlers/common_handlers/keyboards.py`

Changed default URLs in two functions:
- `generate_pharmacist_webapp_url()` 
- `get_pharmacist_inline_keyboard()`

**Before**:
```python
base_url = os.getenv("PHARMACIST_DASHBOARD_URL", "https://pharmacist.spravka.novamedika.com")
```

**After**:
```python
base_url = os.getenv("PHARMACIST_DASHBOARD_URL", "https://spravka.novamedika.com/pharmacist")
```

#### Infrastructure (Traefik Routing)
**File**: `docker-compose.traefik.prod.yml`

Added path-based routing rules:
```yaml
# Main site excludes /pharmacist path
- "traefik.http.routers.frontend.rule=Host(`spravka.novamedika.com`) && !PathPrefix(`/pharmacist`)"

# Pharmacist dashboard on same host with /pharmacist path
- "traefik.http.routers.pharmacist.rule=Host(`spravka.novamedika.com`) && PathPrefix(`/pharmacist`)"

# Backward compatibility - old subdomain still works
- "traefik.http.routers.pharmacist-subdomain.rule=Host(`pharmacist.spravka.novamedika.com`)"
```

### 2. Frontend
**No changes needed** - already supports path-based routing via:
- `frontend/src/App.jsx`: Detects `/pharmacist` pathname
- `frontend/nginx.conf`: SPA routing handles all paths

---

## 🚀 Deployment Steps

### On Production Server:

```bash
# 1. SSH to server
ssh novamedika@your-server
cd /opt/novamedika-prod

# 2. Update .env file
echo "PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist" >> .env

# 3. Pull latest code
git pull origin main

# 4. Rebuild backend (contains bot code)
docker compose -f docker-compose.traefik.prod.yml build backend

# 5. Deploy updated services
docker compose -f docker-compose.traefik.prod.yml up -d backend traefik

# 6. Verify
docker ps  # All containers should be healthy
curl -I https://spravka.novamedika.com/pharmacist  # Should return 200
```

---

## 🧪 Testing

### Manual Tests:
```bash
# Test path-based routing
curl -I https://spravka.novamedika.com/pharmacist
# Expected: HTTP/2 200

# Test backward compatibility
curl -I https://pharmacist.spravka.novamedika.com
# Expected: HTTP/2 200

# Test main site unaffected
curl -I https://spravka.novamedika.com/
# Expected: HTTP/2 200
```

### Telegram Bot Test:
1. Open bot in Telegram
2. Click "💼 Панель фармацевта" button
3. Verify WebApp opens at: `https://spravka.novamedika.com/pharmacist?token=...`
4. Check dashboard loads without errors
5. Verify API calls work (check browser console Network tab)

---

## 🔍 Verification Checklist

- [ ] `.env` has `PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist`
- [ ] Backend image rebuilt with new keyboard URLs
- [ ] Traefik restarted with new routing rules
- [ ] `curl -I https://spravka.novamedika.com/pharmacist` returns 200
- [ ] `curl -I https://pharmacist.spravka.novamedika.com` returns 200 (backward compat)
- [ ] Telegram bot button opens correct URL with token
- [ ] Dashboard loads and authenticates via JWT
- [ ] No CSP violations in browser console
- [ ] WebSocket connection established
- [ ] All container health checks pass

---

## 📊 Benefits

✅ **Simplified DNS management** - Single domain instead of multiple subdomains  
✅ **Reduced CORS complexity** - Same origin for main app and dashboard  
✅ **Easier SSL/TLS management** - One certificate covers all paths  
✅ **Better monitoring** - Unified logs and analytics  
✅ **Backward compatible** - Old subdomain links still work  

---

## 🐛 Troubleshooting Quick Fixes

### 404 on /pharmacist
```bash
docker compose -f docker-compose.traefik.prod.yml restart traefik
docker logs traefik-prod | grep pharmacist
```

### Wrong page loads
```bash
# Clear browser cache and localStorage
localStorage.clear();
location.reload();
```

### Token not working
```bash
# Check backend logs
docker logs backend-prod | grep -i token
# Verify auth endpoint
curl -H "Authorization: Bearer TOKEN" https://api.spravka.novamedika.com/api/pharmacist/me
```

### CSP errors
```bash
# Check headers
curl -I https://spravka.novamedika.com/pharmacist | grep content-security-policy
# Ensure 'unsafe-eval' is present for Telegram SDK
```

---

## 📝 Rollback (if needed)

```bash
cd /opt/novamedika-prod

# Restore previous config
cp docker-compose.traefik.prod.yml.backup docker-compose.traefik.prod.yml

# Restart services
docker compose -f docker-compose.traefik.prod.yml up -d traefik backend

# Or revert git
git reset --hard HEAD~1
docker compose -f docker-compose.traefik.prod.yml build backend
docker compose -f docker-compose.traefik.prod.yml up -d
```

---

## 📞 Support Resources

- **Full deployment guide**: See `QUICK_FIX_PHARMACIST_WEBAPP.md`
- **Server logs**: Check `agent/server-logs/` directory
- **Telegram docs**: See `agent/tg-docs/webapp.md`
- **Memory spec**: Search for "Pharmacist Dashboard Path-Based Routing Configuration"

---

**Status**: ✅ Ready for Deployment  
**Date**: 2026-04-29  
**Estimated Downtime**: < 2 minutes (during service restart)
