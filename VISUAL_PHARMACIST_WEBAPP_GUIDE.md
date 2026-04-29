# 📊 Visual Guide: Pharmacist Dashboard Telegram Integration

## Current vs Simplified Architecture

### ❌ CURRENT (Complex - Subdomain-based)

```
┌─────────────────────────────────────────────────────────────┐
│                    DNS Configuration                         │
├─────────────────────────────────────────────────────────────┤
│  spravka.novamedika.com        → Frontend (Search)          │
│  pharmacist.spravka.novamedika.com → Frontend (Dashboard)   │
│  api.spravka.novamedika.com    → Backend API                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Traefik Routing                            │
├─────────────────────────────────────────────────────────────┤
│  Host(spravka...)         → frontend container              │
│  Host(pharmacist...)      → frontend container              │
│  Host(api...)             → backend container               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Problems                                    │
├─────────────────────────────────────────────────────────────┤
│  ❌ Multiple DNS records needed                             │
│  ❌ CORS between subdomains possible                        │
│  ❌ SSL certificate management complex                      │
│  ❌ Two different URLs for same app                         │
└─────────────────────────────────────────────────────────────┘
```

### ✅ SIMPLIFIED (Path-based)

```
┌─────────────────────────────────────────────────────────────┐
│                    DNS Configuration                         │
├─────────────────────────────────────────────────────────────┤
│  spravka.novamedika.com        → Frontend (Both modes)      │
│  api.spravka.novamedika.com    → Backend API                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Traefik Routing                            │
├─────────────────────────────────────────────────────────────┤
│  Host(spravka...)/*           → frontend container          │
│  Host(spravka...)/pharmacist  → frontend container          │
│  Host(api...)                 → backend container           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Benefits                                    │
├─────────────────────────────────────────────────────────────┤
│  ✅ Single DNS record                                        │
│  ✅ No CORS issues (same origin)                            │
│  ✅ Simple SSL management                                   │
│  ✅ One URL, two modes                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow Diagram

```
┌──────────────┐
│  Telegram    │
│     Bot      │
└──────┬───────┘
       │
       │ 1. User clicks "💼 Панель фармацевта"
       ↓
┌──────────────────────────────────────────┐
│  Backend (keyboards.py)                  │
│  generate_pharmacist_webapp_url()        │
├──────────────────────────────────────────┤
│  • Create JWT token with:                │
│    - sub: pharmacist_uuid                │
│    - telegram_id: user_id                │
│    - role: "pharmacist"                  │
│  • Build URL:                            │
│    https://spravka.novamedika.com/       │
│    /pharmacist?token=xxx                 │
└──────────────┬───────────────────────────┘
               │
               │ 2. Opens WebApp with URL + token
               ↓
┌──────────────────────────────────────────┐
│  Telegram WebApp (WebView)               │
│  Loads: spravka.novamedika.com/pharma..  │
└──────────────┬───────────────────────────┘
               │
               │ 3. Browser loads page
               ↓
┌──────────────────────────────────────────┐
│  Frontend (App.jsx)                      │
├──────────────────────────────────────────┤
│  • Detect mode by path:                  │
│    pathname.startsWith('/pharmacist')    │
│  • Check URL params:                     │
│    has 'token' parameter?                │
│  • If yes → Show PharmacistDashboard     │
└──────────────┬───────────────────────────┘
               │
               │ 4. Extract token from URL
               ↓
┌──────────────────────────────────────────┐
│  Frontend (useAuth hook)                 │
├──────────────────────────────────────────┤
│  • Parse token from URL                  │
│  • Validate token format                 │
│  • Store in localStorage:                │
│    access_token = xxx                    │
│  • Call Telegram.WebApp.ready()          │
│  • Call Telegram.WebApp.expand()         │
└──────────────┬───────────────────────────┘
               │
               │ 5. Make API requests with token
               ↓
┌──────────────────────────────────────────┐
│  Backend API (/api/pharmacist/me)        │
├──────────────────────────────────────────┤
│  • Extract token from Authorization hdr  │
│  • Validate JWT signature                │
│  • Check expiration                      │
│  • Return pharmacist data:               │
│    { uuid, name, pharmacy, is_online }   │
└──────────────┬───────────────────────────┘
               │
               │ 6. Return data
               ↓
┌──────────────────────────────────────────┐
│  Frontend (PharmacistDashboard)          │
├──────────────────────────────────────────┤
│  • Display dashboard UI                  │
│  • Show tabs:                            │
│    - 📊 Statistics                       │
│    - 💬 Consultations                    │
│    - 👤 Profile                          │
│  • WebSocket connection for real-time    │
└──────────────────────────────────────────┘
```

---

## Code Flow: How Token is Generated

### Step 1: Keyboard Generation (backend/src/bot/handlers/common_handlers/keyboards.py)

```python
def generate_pharmacist_webapp_url(telegram_id: int, pharmacist_uuid: str):
    # Create JWT payload
    token_data = {
        "sub": pharmacist_uuid,        # Subject = pharmacist UUID
        "telegram_id": telegram_id,     # Telegram user ID
        "role": "pharmacist",           # Role identifier
        "type": "access",               # Token type
    }
    
    # Generate JWT token (expires in 24h by default)
    access_token = create_access_token(data=token_data)
    
    # Get base URL from environment
    base_url = os.getenv(
        "PHARMACIST_DASHBOARD_URL", 
        "https://spravka.novamedika.com/pharmacist"
    )
    
    # Append token as query parameter
    return f"{base_url}?token={access_token}"
```

### Step 2: Button Creation

```python
InlineKeyboardButton(
    text="💼 Панель фармацевта",
    web_app=WebAppInfo(url=generate_pharmacist_webapp_url(telegram_id, uuid))
)
```

**Result:** When user clicks button, Telegram opens:
```
https://spravka.novamedika.com/pharmacist?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Code Flow: How Token is Consumed

### Step 1: Mode Detection (frontend/src/App.jsx)

```javascript
// Check if this is pharmacist mode
const isPharmacistPath = window.location.pathname.startsWith('/pharmacist');
const urlParams = new URLSearchParams(window.location.search);
const hasAuthToken = urlParams.has('token');

const isPharmacistMode = isPharmacistPath || hasAuthToken;

if (isPharmacistMode) {
  return <PharmacistDashboard />;  // Show dashboard
} else {
  return <Search />;  // Show drug search
}
```

### Step 2: Token Extraction (frontend/src/pharmacist/hooks/useAuth.js)

```javascript
useEffect(() => {
  // Check URL for token
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (token) {
    // Save to localStorage
    localStorage.setItem('access_token', token);
    
    // Remove token from URL (clean URL)
    window.history.replaceState({}, '', window.location.pathname);
  }
}, []);
```

### Step 3: API Requests

```javascript
// All API calls automatically include token from localStorage
const response = await fetch('/api/pharmacist/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});
```

---

## Environment Variables Comparison

### OLD (Subdomain-based)

```bash
# .env on server
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
CORS_ORIGINS=https://spravka.novamedika.com,https://pharmacist.spravka.novamedika.com
```

### NEW (Path-based) - RECOMMENDED

```bash
# .env on server
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
CORS_ORIGINS=https://spravka.novamedika.com
```

**Changes needed:**
- ✅ Only `.env` file (one line)
- ✅ Restart backend container
- ✅ No code changes required!

---

## Testing Checklist

### Manual Testing

```
□ Open browser: https://spravka.novamedika.com/pharmacist
  → Should show login page or dashboard
  
□ Open Telegram bot @Novamedika_bot
  → Click "💼 Панель фармацевта"
  → WebApp should open inside Telegram
  
□ Check DevTools Console
  → No CORS errors
  → No 404 errors
  
□ Check Network tab
  → GET /api/pharmacist/me returns 200 OK
  → Authorization header contains Bearer token
  
□ Check Application → Local Storage
  → access_token key exists
  
□ Test functionality
  → Can view statistics
  → Can see consultations
  → Can update profile
```

### Automated Testing

```bash
# Test CSP headers
curl -I https://spravka.novamedika.com/pharmacist | grep frame-ancestors

# Expected output:
# content-security-policy: ... frame-ancestors 'self' https://t.me https://web.telegram.org; ...

# Test API endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.spravka.novamedika.com/api/pharmacist/me

# Expected output:
# {"uuid":"...","name":"...","is_online":true,...}

# Check logs
docker logs backend-prod --tail 50 | grep -E "(pharmacist|200|error)"
```

---

## Troubleshooting Decision Tree

```
WebApp not opening?
│
├─→ Check URL in browser first
│   ├─→ Works? → Problem is Telegram-specific
│   └─→ Doesn't work? → Check Traefik routing
│
├─→ Check CSP headers
│   ├─→ Missing frame-ancestors? → Fix Traefik config
│   └─→ Correct? → Continue
│
├─→ Check browser console
│   ├─→ CORS error? → Check CORS_ORIGINS in .env
│   ├─→ 404 error? → Check Traefik routes
│   └─→ No errors? → Continue
│
├─→ Check Network tab
│   ├─→ API returns 401? → Token expired or invalid
│   ├─→ API returns 403? → Wrong permissions
│   └─→ API returns 200? → Frontend issue
│
└─→ Check localStorage
    ├─→ No access_token? → Token not extracted from URL
    └─→ Has access_token? → Token might be expired
```

---

## Quick Reference Commands

```bash
# SSH to server
ssh user@server

# Navigate to project
cd /opt/novamedika-prod

# Edit .env
nano .env

# Restart backend
docker compose -f docker-compose.traefik.prod.yml restart backend

# Check logs
docker logs backend-prod -f --tail 50

# Check container status
docker compose -f docker-compose.traefik.prod.yml ps

# Test CSP headers
curl -I https://spravka.novamedika.com/pharmacist

# Test API
curl https://api.spravka.novamedika.com/health

# View Traefik dashboard (if enabled)
open http://localhost:8080
```

---

## Summary

**To make pharmacist dashboard open reliably through Telegram:**

1. **Change ONE line** in `.env`:
   ```
   PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
   ```

2. **Restart backend**:
   ```bash
   docker compose restart backend
   ```

3. **Test in Telegram**:
   - Open bot
   - Click button
   - WebApp opens ✅

**That's it!** No code changes needed. The frontend already supports path-based routing.
