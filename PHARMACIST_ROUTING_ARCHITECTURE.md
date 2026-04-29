# Pharmacist Dashboard Routing Architecture

## 🗺️ Visual Overview

### Before (Subdomain-Based)
```
                    ┌─────────────────────────────────────┐
                    │         DNS (178.172.137.7)         │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
          spravka.novamedika.com    pharmacist.spravka.novamedika.com
                    │                               │
                    ▼                               ▼
          ┌─────────────────┐            ┌─────────────────┐
          │   Main Search   │            │   Pharmacist    │
          │      App        │            │   Dashboard     │
          │                 │            │                 │
          └─────────────────┘            └─────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                          ┌─────────────────┐
                          │   Frontend      │
                          │   Container     │
                          └─────────────────┘
```

**Issues**:
- ❌ Two separate hostnames to manage
- ❌ Potential CORS issues between domains
- ❌ More complex SSL certificate management
- ❌ Harder to maintain consistent authentication

---

### After (Path-Based) ✅
```
                    ┌─────────────────────────────────────┐
                    │         DNS (178.172.137.7)         │
                    └─────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │         Traefik Proxy               │
                    │       (Port 443 / HTTPS)            │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
              Path: /* (except /pharmacist)    Path: /pharmacist*
                    │                                │
                    ▼                                ▼
          ┌─────────────────┐            ┌─────────────────┐
          │   Main Search   │            │   Pharmacist    │
          │      App        │            │   Dashboard     │
          │                 │            │   (Same SPA)    │
          └─────────────────┘            └─────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                          ┌─────────────────┐
                          │   Frontend      │
                          │   Container     │
                          │   (Single SPA)  │
                          └─────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  Mode Detection │
                          │  in App.jsx     │
                          └─────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                  isPharmacistMode        !isPharmacistMode
                        │                       │
                        ▼                       ▼
              ┌─────────────────┐    ┌─────────────────┐
              │ Pharmacist      │    │ Main Search     │
              │ Dashboard UI    │    │ Interface       │
              └─────────────────┘    └─────────────────┘
```

**Benefits**:
- ✅ Single hostname (`spravka.novamedika.com`)
- ✅ No CORS issues (same origin)
- ✅ One SSL certificate covers everything
- ✅ Unified authentication and session management
- ✅ Backward compatible with old subdomain

---

## 🔄 Request Flow

### Scenario 1: User Opens Main Site
```
User Browser
     │
     │ GET https://spravka.novamedika.com/
     ▼
Traefik Proxy
     │
     │ Route: Host(`spravka.novamedika.com`) && !PathPrefix(`/pharmacist`)
     ▼
Frontend Container (nginx)
     │
     │ Serves: /usr/share/nginx/html/index.html
     ▼
React App (App.jsx)
     │
     │ Detects: pathname = "/" → isPharmacistMode = false
     ▼
Main Search Interface Renders
```

### Scenario 2: User Opens Pharmacist Dashboard via Path
```
User Browser
     │
     │ GET https://spravka.novamedika.com/pharmacist?token=eyJ...
     ▼
Traefik Proxy
     │
     │ Route: Host(`spravka.novamedika.com`) && PathPrefix(`/pharmacist`)
     ▼
Frontend Container (nginx)
     │
     │ Serves: /usr/share/nginx/html/index.html (SPA routing)
     ▼
React App (App.jsx)
     │
     │ Detects: pathname.startsWith('/pharmacist') → isPharmacistMode = true
     │ Extracts: token from URL query params
     │ Stores: token in localStorage
     ▼
PharmacistDashboard Component Renders
     │
     │ API calls include: Authorization: Bearer <token>
     ▼
Backend API Validates Token & Returns Data
```

### Scenario 3: Telegram Bot WebApp Button
```
Telegram Bot
     │
     │ User clicks "💼 Панель фармацевта"
     ▼
Bot generates JWT token
     │
     │ Creates URL: https://spravka.novamedika.com/pharmacist?token=eyJ...
     ▼
Telegram WebApp opens URL
     │
     │ Loads in Telegram's embedded browser
     ▼
Same flow as Scenario 2
     │
     │ Plus: Telegram.WebApp SDK initializes
     │       CSP allows frame-ancestors 'self' https://t.me
     ▼
Dashboard loads with full functionality
```

---

## 🏗️ Technical Components

### 1. Traefik Configuration
```yaml
# docker-compose.traefik.prod.yml

# Main site router (excludes /pharmacist)
traefik.http.routers.frontend.rule:
  Host(`spravka.novamedika.com`) && !PathPrefix(`/pharmacist`)

# Pharmacist dashboard router (path-based)
traefik.http.routers.pharmacist.rule:
  Host(`spravka.novamedika.com`) && PathPrefix(`/pharmacist`)

# Backward compatibility (subdomain)
traefik.http.routers.pharmacist-subdomain.rule:
  Host(`pharmacist.spravka.novamedika.com`)
```

### 2. Frontend Mode Detection
```javascript
// frontend/src/App.jsx

const hostname = window.location.hostname;
const pathname = window.location.pathname;

// Check multiple conditions for pharmacist mode
const isPharmacistSubdomain = hostname.startsWith('pharmacist.');
const isPharmacistPath = pathname.startsWith('/pharmacist');
const hasAuthToken = new URLSearchParams(window.location.search).has('token');
const savedMode = localStorage.getItem('app_mode') === 'pharmacist';

const isPharmacistMode = 
  isPharmacistSubdomain || 
  isPharmacistPath || 
  hasAuthToken || 
  savedMode;

// Render appropriate component
if (isPharmacistMode) {
  return <PharmacistDashboard />;
} else {
  return <Search />;
}
```

### 3. Nginx SPA Routing
```nginx
# frontend/nginx.conf

server {
    listen 80;
    root /usr/share/nginx/html;
    
    # All paths serve index.html (SPA pattern)
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Security headers for Telegram WebApp
    add_header Content-Security-Policy 
        "default-src 'self'; 
         script-src 'self' https://telegram.org 'unsafe-inline' 'unsafe-eval'; 
         frame-ancestors 'self' https://t.me https://web.telegram.org";
}
```

### 4. Bot Keyboard Generation
```python
# backend/src/bot/handlers/common_handlers/keyboards.py

def generate_pharmacist_webapp_url(telegram_id: int, pharmacist_uuid: str):
    # Create JWT token
    token_data = {
        "sub": pharmacist_uuid,
        "telegram_id": telegram_id,
        "role": "pharmacist",
    }
    access_token = create_access_token(data=token_data)
    
    # Build URL with path-based routing
    base_url = os.getenv(
        "PHARMACIST_DASHBOARD_URL", 
        "https://spravka.novamedika.com/pharmacist"
    )
    
    return f"{base_url}?token={access_token}"
```

---

## 🔐 Security Considerations

### CSP Headers (Critical for Telegram WebApp)
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://telegram.org 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline';
  connect-src 'self' https://api.spravka.novamedika.com wss://api.spravka.novamedika.com;
  frame-ancestors 'self' https://t.me https://web.telegram.org;
```

**Why these are needed**:
- `'unsafe-eval'`: Telegram SDK uses eval() during initialization
- `frame-ancestors`: Allows embedding in Telegram's WebView
- `connect-src`: Permits API and WebSocket connections

### JWT Authentication Flow
```
1. Bot generates JWT with pharmacist UUID + Telegram ID
2. URL includes token as query parameter
3. Frontend extracts token and stores in localStorage
4. All API requests include: Authorization: Bearer <token>
5. Backend validates token and returns pharmacist data
6. Token expires after 24 hours (configurable)
```

### Session Persistence
```javascript
// First visit (with token in URL)
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
if (token) {
  localStorage.setItem('pharmacist_token', token);
  localStorage.setItem('app_mode', 'pharmacist');
}

// Subsequent visits (token from localStorage)
const savedToken = localStorage.getItem('pharmacist_token');
const savedMode = localStorage.getItem('app_mode');
if (savedMode === 'pharmacist' && savedToken) {
  // Auto-authenticate without URL token
}
```

---

## 📊 Monitoring Points

### Traefik Metrics
```bash
# Check routing decisions
docker logs traefik-prod | grep -E "pharmacist|frontend"

# Expected patterns:
# - "Router frontend matched" for main site
# - "Router pharmacist matched" for /pharmacist path
```

### Application Metrics
```bash
# Backend API calls
docker logs backend-prod | grep "/api/pharmacist"

# Frontend errors
docker logs frontend-prod | grep -i error

# WebSocket connections
docker logs backend-prod | grep "ws/pharmacist"
```

### Browser Console Checks
```javascript
// Verify correct mode detection
console.log({
  hostname: window.location.hostname,
  pathname: window.location.pathname,
  isPharmacistMode: /* check App.jsx logic */,
  hasToken: !!localStorage.getItem('pharmacist_token'),
});

// Monitor API calls
// Open Network tab → Filter by "pharmacist" → Check status codes
```

---

## 🎯 Success Metrics

After deployment, track:

1. **Routing Accuracy**
   - % of `/pharmacist` requests returning 200 (target: >99%)
   - % of main site requests unaffected (target: 100%)

2. **Authentication Success**
   - % of WebApp openings with valid tokens (target: >95%)
   - Average time to authenticate (target: <500ms)

3. **User Experience**
   - Page load time for dashboard (target: <2s)
   - WebSocket connection success rate (target: >98%)
   - CSP violation count (target: 0)

4. **Backward Compatibility**
   - Old subdomain still functional (target: 100% uptime)
   - Redirect analytics (how many users still use old URL)

---

**Architecture Version**: 2.0 (Path-Based)  
**Last Updated**: 2026-04-29  
**Maintained By**: DevOps Team
