# Telegram WebApp Authentication - Root Cause Analysis

## 🔴 CRITICAL ISSUE IDENTIFIED

**Problem**: Pharmacist dashboard cannot authenticate when opened from Telegram bot  
**Root Cause**: **Telegram WebApp uses URL hash fragments, NOT query parameters**

---

## 📊 Log Analysis Evidence

### Frontend Logs (2026-04-29 10:28:49)

```nginx
# Request WITH token in query param (from direct browser access)
GET /pharmacist?token=eyJhbG...S0fW8kK6HljEMWzdX_-WwtCla3Rylf0Htrtox2aXFUg HTTP/1.1" 200

# Request WITHOUT token (from Telegram WebApp)
GET /pharmacist HTTP/1.1" 200
GET /assets/index-FTmF9hnI.js HTTP/1.1" 200
GET /assets/index-DV3UHmUP.css HTTP/1.1" 200
```

**Key Observation**: When accessed from `https://web.telegram.org/`, the token is **NOT present** in the URL!

### Backend Logs

```
GET /api/pharmacist/me HTTP/1.1" 200  ← Successful when token exists
OPTIONS /api/pharmacist/me HTTP/1.1" 200
```

No 401/403 errors logged → Frontend never attempts authentication because it can't find the token.

---

## 🔍 How Telegram WebApp Actually Works

### The Misconception

**What we thought happens:**
```
Bot generates URL: https://spravka.novamedika.com/pharmacist?token=eyJ...
User clicks button → Telegram opens URL with token
Frontend extracts token from query params → Authentication works ✅
```

**What actually happens:**
```
Bot generates URL: https://spravka.novamedika.com/pharmacist?token=eyJ...
User clicks button → Telegram STRIPS query params for security
Telegram adds hash fragment: #tgWebAppData=query_id%3DXXX%26user%3D...
Frontend looks for query param → Finds NOTHING ❌
Authentication fails silently
```

### Official Telegram Behavior

According to [Telegram WebApps documentation](https://core.telegram.org/bots/webapps):

1. **Query parameters are stripped** when opening WebApp (security feature)
2. **Hash fragment is used** to pass authentication data: `#tgWebAppData=...`
3. **SDK provides parsed data** via `window.Telegram.WebApp.initData`

Example URL from Telegram:
```
https://example.com/app#tgWebAppData=query_id%3DAAH5mgz...%26user%3D%257B%2522id%2522%253A...
```

NOT:
```
https://example.com/app?token=xxx
```

---

## 🐛 Current Implementation Problems

### 1. Bot Keyboard Generates Wrong URL Format

**File**: `backend/src/bot/handlers/common_handlers/keyboards.py`

```python
def generate_pharmacist_webapp_url(telegram_id: int, pharmacist_uuid: str):
    # Creates JWT token
    access_token = create_access_token(data=token_data)
    
    # Builds URL with query parameter
    base_url = os.getenv("PHARMACIST_DASHBOARD_URL", 
                         "https://spravka.novamedika.com/pharmacist")
    
    params = {"token": access_token}  # ← WRONG! Query params get stripped
    query_string = urlencode(params)
    
    return f"{base_url}?{query_string}"  # Returns: /pharmacist?token=xxx
```

**Problem**: Telegram strips `?token=xxx` when opening WebApp!

### 2. Frontend Looks in Wrong Place

**File**: `frontend/src/pharmacist/PharmacistContent.jsx`

```javascript
// Extracts token from query parameters
const urlParams = new URLSearchParams(window.location.search);  // ← WRONG!
const token = urlParams.get('token');  // Returns null in Telegram WebApp

console.log('[PharmacistContent] Token found:', !!token);  // false
```

**Problem**: `window.location.search` is empty in Telegram WebApp!

### 3. No Fallback to Telegram SDK

The code doesn't use `window.Telegram.WebApp.initData` at all, which is the **correct way** to get authentication data from Telegram.

---

## ✅ Solutions

### Solution A: Use Telegram's Native initData (RECOMMENDED)

This is the **proper** way according to Telegram's official documentation.

#### Step 1: Update Bot Keyboard

Remove JWT token generation, just open WebApp:

```python
def get_pharmacist_inline_keyboard():
    webapp_url = os.getenv("PHARMACIST_DASHBOARD_URL", 
                           "https://spravka.novamedika.com/pharmacist")
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            # ... other buttons ...
            [
                InlineKeyboardButton(
                    text="💼 Панель фармацевта",
                    web_app=WebAppInfo(url=webapp_url),  # No token needed
                )
            ],
        ],
    )
```

#### Step 2: Update Frontend to Use Telegram SDK

**File**: `frontend/src/pharmacist/components/auth/AuthProvider.jsx`

```javascript
const loginWithTelegram = async () => {
  try {
    setIsLoading(true);
    
    // Get initData from Telegram SDK
    if (!window.Telegram?.WebApp?.initData) {
      throw new Error('Not in Telegram WebApp environment');
    }
    
    const initData = window.Telegram.WebApp.initData;
    console.log('[AuthProvider] Sending initData to backend for validation...');
    
    // Send initData to backend for signature validation
    const response = await fetch('/api/pharmacist/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData }),
    });
    
    if (!response.ok) {
      throw new Error('Backend validation failed');
    }
    
    const data = await response.json();
    
    // Backend returns JWT token after validating initData
    authService.setAccessToken(data.access_token);
    
    // Get profile
    const profile = await authService.getProfile();
    setPharmacist(profile);
    setIsAuthenticated(true);
    
  } catch (err) {
    console.error('[AuthProvider] Telegram login failed:', err);
    setError(err.message);
  } finally {
    setIsLoading(false);
  }
};
```

#### Step 3: Add Backend Endpoint for initData Validation

**File**: `backend/src/routers/pharmacist_auth.py`

```python
from aiogram.utils.web_app import safe_parse_webapp_init_data
from pydantic import BaseModel

class TelegramLoginRequest(BaseModel):
    initData: str

@router.post("/login")
async def telegram_login(request: TelegramLoginRequest, db: AsyncSession):
    """Validate Telegram initData and issue JWT token"""
    
    try:
        # Validate signature using bot token
        validated_data = safe_parse_webapp_init_data(
            token=os.getenv("TELEGRAM_BOT_TOKEN"),
            init_data=request.initData
        )
        
        # Extract user info
        telegram_id = validated_data.user.id
        first_name = validated_data.user.first_name
        last_name = validated_data.user.last_name
        username = validated_data.user.username
        
        logger.info(f"Telegram login attempt: telegram_id={telegram_id}")
        
        # Find pharmacist by telegram_id
        result = await db.execute(
            select(Pharmacist).where(Pharmacist.telegram_id == telegram_id)
        )
        pharmacist = result.scalar_one_or_none()
        
        if not pharmacist:
            raise HTTPException(
                status_code=404,
                detail=f"Pharmacist not found for telegram_id={telegram_id}"
            )
        
        if not pharmacist.is_active:
            raise HTTPException(
                status_code=403,
                detail="Pharmacist account is deactivated"
            )
        
        # Generate JWT token
        token_data = {
            "sub": str(pharmacist.uuid),
            "telegram_id": telegram_id,
            "role": "pharmacist",
            "type": "access",
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        # Store refresh token
        await store_refresh_token(db, pharmacist.uuid, refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
        
    except ValueError as e:
        logger.error(f"Invalid initData signature: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram initData signature"
        )
```

---

### Solution B: Hybrid Approach (Quick Fix)

If you want to keep JWT tokens but make it work with Telegram:

#### Option B1: Use localStorage

1. **Before opening WebApp**, bot sends message with token
2. User clicks link that stores token in localStorage
3. Then opens WebApp (which reads from localStorage)

**Complexity**: Requires extra step, poor UX

#### Option B2: Use start_param

Pass token via deep link `start_param`:

```python
# Bot sends deep link
deep_link = f"https://t.me/your_bot?start=pharmacist_{pharmacist_uuid}"

# Frontend extracts start_param from initData
const startParam = window.Telegram.WebApp.initDataUnsafe?.start_param;
// Parse: "pharmacist_ec7d4a63-..."
```

**Complexity**: Moderate, requires URL encoding

---

### Solution C: PostMessage Communication

Use `Telegram.WebApp.sendData()` to send token back to bot, then bot re-opens with proper auth.

**Complexity**: High, requires multiple round-trips

---

## 🎯 Recommended Implementation Plan

### Phase 1: Quick Diagnosis (Today)

1. **Verify the issue**:
   ```javascript
   // Add to frontend console
   console.log('Query params:', window.location.search);
   console.log('Hash:', window.location.hash);
   console.log('Telegram SDK available:', !!window.Telegram?.WebApp);
   console.log('initData:', window.Telegram?.WebApp?.initData);
   console.log('initDataUnsafe:', window.Telegram?.WebApp?.initDataUnsafe);
   ```

2. **Check logs** when opening from Telegram:
   - Expected: Hash contains `#tgWebAppData=...`
   - Expected: Query params are empty
   - Expected: `initData` string is present

### Phase 2: Implement Solution A (This Week)

1. **Backend changes**:
   - Add `/api/pharmacist/login` endpoint
   - Import `safe_parse_webapp_init_data` from aiogram
   - Validate initData signature
   - Return JWT token

2. **Frontend changes**:
   - Remove query param extraction
   - Use `window.Telegram.WebApp.initData`
   - Send initData to new login endpoint
   - Store returned JWT token

3. **Bot changes**:
   - Remove JWT token from WebApp URL
   - Just use plain URL: `https://spravka.novamedika.com/pharmacist`

### Phase 3: Testing & Deployment

1. Test with real Telegram WebApp
2. Verify authentication flow
3. Check error handling
4. Deploy to production

---

## 📝 Code Changes Summary

### Files to Modify

1. **backend/src/bot/handlers/common_handlers/keyboards.py**
   - Remove `generate_pharmacist_webapp_url()` function
   - Simplify keyboard to use plain URL

2. **backend/src/routers/pharmacist_auth.py**
   - Add `POST /login` endpoint
   - Validate Telegram initData
   - Issue JWT tokens

3. **frontend/src/pharmacist/components/auth/AuthProvider.jsx**
   - Replace `loginWithToken()` with `loginWithTelegram()`
   - Use `window.Telegram.WebApp.initData`
   - Call new `/api/pharmacist/login` endpoint

4. **frontend/src/pharmacist/PharmacistContent.jsx**
   - Remove query param extraction logic
   - Trigger Telegram login on mount

---

## 🔧 Immediate Debugging Steps

To confirm this is the issue, add this to your frontend temporarily:

```javascript
// In PharmacistContent.jsx useEffect
useEffect(() => {
  console.log('=== TELEGRAM WEBAPP DEBUG ===');
  console.log('URL:', window.location.href);
  console.log('Search (query params):', window.location.search);
  console.log('Hash:', window.location.hash);
  console.log('Telegram SDK:', !!window.Telegram?.WebApp);
  
  if (window.Telegram?.WebApp) {
    console.log('initData (raw):', window.Telegram.WebApp.initData?.substring(0, 100) + '...');
    console.log('initDataUnsafe:', window.Telegram.WebApp.initDataUnsafe);
    console.log('User:', window.Telegram.WebApp.initDataUnsafe?.user);
    console.log('Start param:', window.Telegram.WebApp.initDataUnsafe?.start_param);
  }
  
  console.log('============================');
}, []);
```

Open the WebApp from Telegram and check browser console. You'll see:
- `search`: Empty `""`
- `hash`: Contains `#tgWebAppData=...`
- `initData`: Long string with auth data
- `initDataUnsafe.user`: User object with id, name, etc.

---

## 📚 References

- [Telegram WebApps Documentation](https://core.telegram.org/bots/webapps)
- [Initializing Mini Apps](https://core.telegram.org/bots/webapps#initializing-mini-apps)
- [Validating Data](https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app)
- [aiogram WebApp Utils](https://docs.aiogram.dev/en/latest/utils/web_app.html)
- [Mini Apps Deep Linking](https://core.telegram.org/bots/webapps#sharing-mini-apps)

---

**Status**: 🔴 Critical Issue Identified  
**Impact**: 100% of Telegram WebApp users cannot authenticate  
**Solution Complexity**: Medium (requires backend + frontend changes)  
**Estimated Fix Time**: 2-4 hours  
**Priority**: HIGH - Blocks all pharmacist WebApp usage
