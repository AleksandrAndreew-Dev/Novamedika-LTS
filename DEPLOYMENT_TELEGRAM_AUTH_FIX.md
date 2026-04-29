# Telegram WebApp Authentication Fix - Deployment Guide

## ✅ Implementation Complete

The fix for Telegram WebApp authentication has been successfully implemented using **Solution A** (native `initData` approach).

---

## 📝 Changes Summary

### 1. Backend Changes

#### File: `backend/src/routers/pharmacist_auth.py`

**Added**: New endpoint `/api/pharmacist/login/telegram/`
- Accepts `initData` from Telegram SDK
- Validates signature using bot token via `aiogram.utils.web_app.safe_parse_webapp_init_data()`
- Finds pharmacist by `telegram_id`
- Issues JWT access and refresh tokens
- Returns standard token response

**Key Features**:
```python
@router.post("/login/telegram/")
async def telegram_webapp_login(request: TelegramLoginRequest, db: AsyncSession):
    # Validate initData signature
    validated_data = safe_parse_webapp_init_data(token=bot_token, init_data=request.initData)
    
    # Find pharmacist by telegram_id
    # Generate JWT tokens
    # Return tokens to frontend
```

---

#### File: `backend/src/bot/handlers/common_handlers/keyboards.py`

**Changed**: Removed JWT token generation from WebApp URL

**Before**:
```python
def generate_pharmacist_webapp_url(telegram_id, pharmacist_uuid):
    token = create_access_token(...)
    return f"{base_url}?token={token}"  # ❌ Query params stripped by Telegram
```

**After**:
```python
def get_pharmacist_webapp_url():
    return "https://spravka.novamedika.com/pharmacist"  # ✅ Clean URL
```

**Impact**: Bot now opens WebApp with clean URL, Telegram adds `initData` in hash fragment automatically.

---

### 2. Frontend Changes

#### File: `frontend/src/pharmacist/components/auth/AuthProvider.jsx`

**Added**: New `loginWithTelegram()` function
- Checks for Telegram SDK availability
- Extracts `initData` from `window.Telegram.WebApp`
- Sends to backend `/api/pharmacist/login/telegram` endpoint
- Receives and stores JWT tokens
- Fetches user profile

**Authentication Flow**:
```javascript
const loginWithTelegram = async () => {
  const initData = window.Telegram.WebApp.initData;
  
  const response = await fetch('/api/pharmacist/login/telegram', {
    method: 'POST',
    body: JSON.stringify({ initData })
  });
  
  const { access_token, refresh_token } = await response.json();
  // Store tokens and fetch profile
};
```

**Legacy Support**: Old `loginWithToken()` method kept for backwards compatibility (query param fallback).

---

#### File: `frontend/src/pharmacist/PharmacistContent.jsx`

**Changed**: Updated authentication logic to prioritize Telegram SDK

**New Flow**:
1. Check if in Telegram WebApp (`window.Telegram?.WebApp?.initData`)
2. If yes → Use `loginWithTelegram()` (NEW)
3. If no → Try query param token (LEGACY fallback)
4. If no token → Check localStorage (existing behavior)

```javascript
if (window.Telegram?.WebApp?.initData) {
  await loginWithTelegram();  // ✅ Primary method
} else {
  const token = urlParams.get('token');
  if (token) await loginWithToken(token);  // ⚠️ Fallback
}
```

---

## 🚀 Deployment Steps

### Step 1: Update Environment Variables (If Needed)

Ensure `.env` file has:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

**Note**: `TELEGRAM_BOT_TOKEN` is required for validating `initData` signature.

---

### Step 2: Deploy to Production Server

```bash
# SSH to server
ssh novamedika@your-server-ip
cd /opt/novamedika-prod

# Backup current state
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
git stash  # If you have uncommitted changes

# Pull latest code
git pull origin main

# Verify TELEGRAM_BOT_TOKEN is set
grep TELEGRAM_BOT_TOKEN .env
```

---

### Step 3: Rebuild Backend Image

```bash
# Rebuild backend (includes new endpoint and updated keyboards)
docker compose -f docker-compose.traefik.prod.yml build backend

# This may take 2-5 minutes
```

---

### Step 4: Deploy Services

```bash
# Restart backend and traefik
docker compose -f docker-compose.traefik.prod.yml up -d backend traefik

# Wait for health checks
sleep 30

# Verify all containers healthy
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected output:
```
NAMES                STATUS
backend-prod         Up 30 seconds (healthy)
traefik-prod         Up 30 seconds
frontend-prod        Up 5 minutes (healthy)
postgres-prod        Up 1 hour (healthy)
redis-prod           Up 1 hour (healthy)
celery-worker-prod   Up 1 hour (healthy)
```

---

### Step 5: Verify Backend Endpoint

```bash
# Test new endpoint exists
curl -X POST https://api.spravka.novamedika.com/api/pharmacist/login/telegram \
  -H "Content-Type: application/json" \
  -d '{"initData": "test"}'

# Expected: 401 Invalid signature (because we sent fake data)
# This confirms endpoint is active
```

---

### Step 6: Test Full Flow

#### Option A: Use Diagnostic Page (Recommended First)

1. Open browser and navigate to:
   ```
   https://spravka.novamedika.com/telegram-diagnostic.html
   ```

2. Click button to open from Telegram bot (or manually test from Telegram)

3. Verify output shows:
   - ✅ In Telegram: Yes
   - ✅ Hash Fragment: Present
   - ✅ initData Available: Yes
   - ✅ User Data: Present

---

#### Option B: Test Real WebApp Flow

1. **Open Telegram bot** (@your_bot_username)

2. **Send `/start`** command

3. **Click "💼 Панель фармацевта"** button

4. **Verify**:
   - WebApp opens without errors
   - Dashboard loads automatically
   - User name and info displayed
   - No authentication error messages
   - Browser console shows: `[AuthProvider] ✅ Telegram login successful`

5. **Check Network Tab**:
   - POST to `/api/pharmacist/login/telegram` returns 200
   - GET to `/api/pharmacist/me` returns 200
   - WebSocket connection established

---

### Step 7: Monitor Logs

```bash
# Watch backend logs for authentication attempts
docker logs -f backend-prod | grep -i "telegram.*login\|pharmacist.*auth"

# Expected patterns:
# "Telegram login attempt: telegram_id=XXX"
# "✅ Telegram login successful for pharmacist UUID=..."
```

```bash
# Watch frontend logs
docker logs -f frontend-prod

# Should show normal SPA serving, no errors
```

---

## 🧪 Testing Checklist

After deployment, verify ALL of the following:

### Basic Functionality
- [ ] WebApp opens from Telegram bot button
- [ ] No "Not in Telegram" error message
- [ ] Dashboard loads within 2 seconds
- [ ] User name displays correctly
- [ ] Statistics panel shows data
- [ ] Questions list loads (if any)

### Authentication
- [ ] Browser console: `[AuthProvider] ✅ Telegram login successful`
- [ ] Browser console: No authentication errors
- [ ] Network tab: POST `/api/pharmacist/login/telegram` returns 200
- [ ] Network tab: GET `/api/pharmacist/me` returns 200
- [ ] localStorage contains `pharmacist_access_token`
- [ ] localStorage contains `pharmacist_refresh_token`

### API Calls
- [ ] All API requests include `Authorization: Bearer <token>` header
- [ ] No 401 Unauthorized responses
- [ ] No 403 Forbidden responses
- [ ] WebSocket connection established (`wss://api.spravka.novamedika.com/...`)

### User Experience
- [ ] Can switch online/offline status
- [ ] Can view questions
- [ ] Can answer questions (if applicable)
- [ ] Logout works correctly
- [ ] Re-login after logout works

### Edge Cases
- [ ] Opening WebApp multiple times works
- [ ] Token refresh works (wait or simulate expiry)
- [ ] Closing and reopening WebApp maintains session (from localStorage)
- [ ] Works on mobile Telegram app
- [ ] Works on desktop Telegram app

---

## 🔍 Troubleshooting

### Issue: "Not in Telegram WebApp environment"

**Cause**: User opened URL directly in browser instead of from bot

**Solution**: 
- Instruct user to click "Панель фармацевта" button in bot
- Or add fallback message with instructions

---

### Issue: "Invalid Telegram initData signature"

**Cause**: `TELEGRAM_BOT_TOKEN` not configured or incorrect

**Solution**:
```bash
# Check env variable
docker exec backend-prod env | grep TELEGRAM_BOT_TOKEN

# If missing, add to .env and restart
echo "TELEGRAM_BOT_TOKEN=your_token" >> .env
docker compose -f docker-compose.traefik.prod.yml up -d backend
```

---

### Issue: "Фармацевт не найден"

**Cause**: User's Telegram ID not linked to pharmacist account in database

**Solution**:
```sql
-- Check if user exists
SELECT u.telegram_id, p.uuid, u.first_name 
FROM users u
LEFT JOIN pharmacists p ON u.uuid = p.user_id
WHERE u.telegram_id = <user_telegram_id>;

-- If missing, create pharmacist record
INSERT INTO pharmacists (uuid, user_id, pharmacy_info, is_active, is_online)
VALUES (gen_random_uuid(), 
        (SELECT uuid FROM users WHERE telegram_id = <id>),
        '{"name": "Test Pharmacy"}', true, false);
```

---

### Issue: WebApp opens but shows loading spinner forever

**Cause**: Frontend JavaScript error or API connectivity issue

**Solution**:
```bash
# Check browser console for errors
# Open DevTools → Console tab

# Check backend logs
docker logs backend-prod --tail=100 | grep -i error

# Check network connectivity
curl -I https://api.spravka.novamedika.com/health
```

---

### Issue: Token validation fails repeatedly

**Cause**: Clock skew between server and Telegram

**Solution**:
```bash
# Check server time
date -u

# Compare with Telegram auth_date in initData
# Should be within 86400 seconds (24 hours)

# If needed, adjust server time
sudo ntpdate pool.ntp.org
```

---

## 📊 Monitoring & Metrics

### Key Metrics to Track

1. **Authentication Success Rate**
   ```bash
   # Count successful logins per hour
   docker logs backend-prod | grep "Telegram login successful" | wc -l
   ```

2. **Error Rate**
   ```bash
   # Count failed attempts
   docker logs backend-prod | grep "Telegram.*login.*failed" | wc -l
   ```

3. **Average Login Time**
   - Monitor via browser Performance API
   - Target: < 1 second

4. **User Retention**
   - Track how often users reopen WebApp
   - Monitor localStorage token usage

---

## 🎯 Rollback Plan

If issues occur, rollback quickly:

```bash
cd /opt/novamedika-prod

# Restore previous code version
git reset --hard HEAD~1

# Rebuild backend
docker compose -f docker-compose.traefik.prod.yml build backend

# Redeploy
docker compose -f docker-compose.traefik.prod.yml up -d backend

# Verify old behavior restored
curl -I https://spravka.novamedika.com/pharmacist?token=test
```

---

## ✅ Success Criteria

Deployment is **SUCCESSFUL** when:

- [x] Code changes committed and pushed
- [ ] Backend rebuilt with new endpoint
- [ ] Services deployed without errors
- [ ] All containers healthy
- [ ] Diagnostic page shows initData present
- [ ] WebApp opens from bot without errors
- [ ] Authentication succeeds automatically
- [ ] Dashboard displays user data
- [ ] No console errors
- [ ] API calls work with JWT tokens
- [ ] WebSocket connects
- [ ] All functionality tested
- [ ] Mobile and desktop Telegram apps work

---

## 📞 Post-Deployment Support

### First 24 Hours
- Monitor logs every 2 hours
- Check error rates
- Collect user feedback
- Watch for unusual patterns

### First Week
- Daily log review
- Track authentication success rate
- Monitor performance metrics
- Document any issues

### Ongoing
- Weekly security updates
- Monthly dependency updates
- Quarterly penetration testing (per ОАЦ requirements)

---

## 📚 Related Documentation

- **Root Cause Analysis**: [`TELEGRAM_WEBAPP_AUTH_ANALYSIS.md`](./TELEGRAM_WEBAPP_AUTH_ANALYSIS.md)
- **Immediate Action Plan**: [`IMMEDIATE_ACTION_TELEGRAM_AUTH.md`](./IMMEDIATE_ACTION_TELEGRAM_AUTH.md)
- **Diagnostic Tool**: `frontend/public/telegram-diagnostic.html`
- **Official Telegram Docs**: https://core.telegram.org/bots/webapps
- **Memory**: Search for "Telegram WebApp Hash Fragment Authentication Issue"

---

**Implementation Date**: 2026-04-29  
**Version**: 1.0  
**Status**: ✅ Ready for Deployment  
**Estimated Downtime**: < 2 minutes (during service restart)
