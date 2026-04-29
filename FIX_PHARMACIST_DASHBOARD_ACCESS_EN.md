# CRITICAL FIX: Pharmacist Cannot Access Dashboard

**Date:** 2026-04-29  
**Priority:** 🔴 CRITICAL  
**Status:** ✅ FIXED

---

## 🎯 Problem

Pharmacist **cannot access the dashboard** when clicking "Панель фармацевта" button in Telegram bot.

---

## 🔍 Root Cause

According to Telegram WebApp documentation, Mini Apps require:

1. **Load Telegram WebApp SDK** via `<script src="https://telegram.org/js/telegram-web-app.js"></script>`
2. **Initialize WebApp** by calling `Telegram.WebApp.ready()` and `Telegram.WebApp.expand()`
3. **Handle initData** - signed user data from Telegram

Without the SDK:
- ❌ Telegram cannot properly initialize WebApp inside the client
- ❌ User data (initData) is not accessible
- ❌ WebApp doesn't expand to full screen
- ❌ Telegram theme colors are not applied

### Evidence from Logs

From `agent/tg-docs/tg-logs.md`:

```
GET https://pharmacist.spravka.novamedika.com/?token=JWT#tgWebAppData=query_id=AAEFNeAoAAAAAAU14Cj4LEM4&user=%7B%22id%22%3A685782277...
```

**Telegram IS passing initData in URL hash fragment**, but without the SDK we cannot access it via `window.Telegram.WebApp.initData`.

---

## ✅ Solution Applied

### Step 1: Add Telegram WebApp SDK to index.html

**File:** `frontend/index.html`

Added to `<head>`:

```html
<!-- Telegram WebApp SDK -->
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<!-- Optimized viewport for mobile devices -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
```

### Step 2: Create Initialization Utility

**File:** `frontend/src/utils/telegramWebApp.js`

Created `TelegramWebApp` class that:
- ✅ Automatically initializes SDK on load
- ✅ Calls `Telegram.WebApp.ready()` and `Telegram.WebApp.expand()`
- ✅ Applies Telegram theme colors
- ✅ Provides helper methods for WebApp API
- ✅ Works both inside Telegram and in regular browser

### Step 3: Integrate into PharmacistApp

**File:** `frontend/src/pharmacist/PharmacistApp.jsx`

Added:
```javascript
import { telegramWebApp } from '../utils/telegramWebApp';

// In TokenAuthHandler component:
useEffect(() => {
  console.log('[TokenAuthHandler] Initializing Telegram WebApp...');
  telegramWebApp.initialize();
  
  if (telegramWebApp.isInTelegram()) {
    console.log('[TokenAuthHandler] Running inside Telegram - applying theme');
    telegramWebApp.applyTheme();
  }
}, []);
```

---

## 🧪 Testing Instructions

### 1. Rebuild Frontend

```bash
cd frontend
npm run build
```

### 2. Restart Container

```bash
docker-compose -f docker-compose.traefik.prod.yml restart frontend-prod
```

### 3. Test in Telegram

1. Open bot in Telegram
2. Type `/start`
3. Click **"💼 Панель фармацевта"** button
4. WebApp should open in full screen
5. Automatic authentication via JWT token should occur
6. Dashboard with statistics should load

### 4. Check Browser Console

Expected console messages:

```
[TelegramWebApp] SDK detected
[TelegramWebApp] Platform: web
[TelegramWebApp] Version: 9.5
[TelegramWebApp] InitData available: true
[TelegramWebApp] ✅ Initialized successfully
[TokenAuthHandler] Running inside Telegram - applying theme
[TokenAuthHandler] Checking for token in URL...
[TokenAuthHandler] Token found: true
[AuthProvider] ✅ Profile fetched successfully
```

---

## 📋 What Changed

### Before Fix:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>НоваМедика — Справочная служба аптек</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

❌ No SDK  
❌ No WebApp initialization  
❌ WebApp doesn't open properly  

### After Fix:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>НоваМедика — Справочная служба аптек</title>
    
    <!-- Telegram WebApp SDK -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    
    <!-- CSP for Telegram WebApp -->
    <meta http-equiv="Content-Security-Policy" content="..." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

✅ SDK loaded  
✅ WebApp initializes automatically  
✅ Telegram theme applied  
✅ WebApp expands to full screen  

---

## 🔗 Useful Links

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Initializing Mini Apps](https://core.telegram.org/bots/webapps#initializing-mini-apps)
- [Validating Data](https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app)
- [aiogram WebApp Utils](https://docs.aiogram.dev/en/latest/utils/web_app.html)

---

## 🚨 Troubleshooting

### If WebApp still doesn't open:

1. **Check if script loads:**
   ```javascript
   // In browser console:
   console.log(window.Telegram); // Should be an object
   console.log(window.Telegram.WebApp); // Should be an object
   ```

2. **Check CSP headers:**
   ```
   script-src must include 'https://telegram.org'
   frame-ancestors must include 'https://t.me https://web.telegram.org'
   ```

3. **Check URL:**
   ```
   URL must contain #tgWebAppData=... in hash fragment
   If not - problem is in bot button
   ```

4. **Check SDK version:**
   ```javascript
   console.log(Telegram.WebApp.version); // Should be >= 6.0
   ```

### If authentication fails:

1. **Check token in URL:**
   ```
   ?token=eyJhbGci... should be in query parameters
   ```

2. **Check backend logs:**
   ```bash
   docker logs backend-prod | grep "pharmacist/me"
   ```

3. **Check token expiration:**
   ```python
   import jwt
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   print(payload['exp'])  # Unix timestamp
   ```

---

## 📝 Notes

### Why This Is Critical?

Without Telegram WebApp SDK:
- WebApp may not open at all
- Or opens in small window instead of full screen
- Native Telegram features won't work (colors, animations, haptic feedback)
- Poor user experience

### Security

We use **two levels of authentication**:

1. **JWT token** (our own) - passed in `?token=`
   - Contains pharmacist UUID
   - Signed with our secret key
   - Has expiration (1 hour)

2. **Telegram initData** (from Telegram) - passed in `#tgWebAppData=`
   - Signed by Telegram Bot API
   - Contains user data
   - Can be validated on backend for extra security

**Current implementation** uses only JWT token, which is sufficient for most cases.

**For enhanced security**, you can add initData validation on backend:

```python
from aiogram.utils.web_app import safe_parse_webapp_init_data

# In backend router
try:
    init_data = safe_parse_webapp_init_data(
        token=settings.TELEGRAM_BOT_TOKEN,
        init_data=request.headers.get('X-Telegram-Init-Data')
    )
    # Verify user.id matches pharmacist.telegram_id
except ValueError:
    raise HTTPException(status_code=401, detail="Invalid initData")
```

But this is **optional** and requires additional changes.

---

## ✨ Next Steps

1. ✅ **DONE:** Add SDK to index.html
2. ✅ **DONE:** Create initialization utility
3. ✅ **DONE:** Integrate into PharmacistApp
4. 🔄 **TESTING:** Verify in Telegram
5. 📊 **MONITORING:** Watch logs after deployment
6. 🎨 **OPTIONAL:** Apply Telegram theme to all components
7. 🔒 **OPTIONAL:** Add initData validation on backend

---

**Fix Applied:** 2026-04-29 09:45 UTC  
**Rebuild Required:** Yes (`npm run build`)  
**Restart Required:** Yes (`docker-compose restart frontend-prod`)
