# Skill: Telegram Bot Debugger

## When to use this skill:
- Bot not responding to messages
- Webhook errors
- FSM state issues
- Authentication problems in bot
- Bot crashes or stops

## Quick Diagnostic Flow:

### Step 1: Run Bot Diagnostics
```bash
bash agent/diagnostics.sh bot
```

This will check:
- Bot process status
- Webhook configuration
- FSM states
- Redis connection
- Error logs

### Step 2: Analyze Output

Look for these common issues:

#### Issue A: Bot process not running
```
# Check if bot is in container
docker ps | grep backend

# Check Gunicorn workers
docker exec -it <backend_container> ps aux | grep gunicorn

# Restart backend
npm run prod:restart-backend
```

#### Issue B: Webhook not set
```
# Check webhook status
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | jq

# Expected output should show:
# - url: your webhook URL
# - has_custom_certificate: false/true
# - pending_update_count: 0 (or low number)
```

#### Issue C: Redis connection failed
```bash
# Check Redis status
bash agent/diagnostics.sh db | grep -i redis

# Test Redis connection
docker exec -it <redis_container> redis-cli ping
# Should return: PONG
```

#### Issue D: FSM state corruption
```bash
# Check Redis keys
docker exec -it <redis_container> redis-cli keys "fsm:*"

# Clear stuck states (careful!)
docker exec -it <redis_container> redis-cli keys "fsm:*" | xargs docker exec -i <redis_container> redis-cli del
```

## Common Bot Issues & Solutions:

### 1. Bot doesn't start after deployment

**Symptoms:**
- No response to /start command
- Container shows as running but bot inactive

**Solution:**
```bash
# 1. Check backend logs
bash agent/diagnostics.sh backend | grep -i "bot\|aiogram"

# 2. Verify bot token in .env
cat .env | grep TELEGRAM_BOT_TOKEN

# 3. Check Gunicorn workers (common issue!)
# See: oac/guides/FIX-BOT-GUNICORN-WORKERS.md

# 4. Restart with proper worker count
docker-compose -f docker-compose.traefik.prod.yml up -d --scale backend=1
```

### 2. Webhook errors

**Symptoms:**
- Telegram returns webhook errors
- Bot receives updates intermittently

**Solution:**
```bash
# 1. Check webhook URL is correct
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# 2. Verify Traefik routing
cat traefic/traefik.yml | grep -A 10 "bot"

# 3. Check SSL certificate
bash agent/diagnostics.sh network | grep -i "certificate"

# 4. Re-set webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://yourdomain.com/api/bot/webhook"
```

### 3. Authentication issues in bot

**Symptoms:**
- User can't login through bot
- JWT token not generated
- Session not persisted

**Solution:**
```bash
# 1. Check auth logs
bash agent/diagnostics.sh backend | grep -i "auth\|login"

# 2. Verify JWT secret
cat .env | grep SECRET_KEY

# 3. Check database user creation
bash agent/diagnostics.sh db | grep -i "user"

# 4. Test auth endpoint manually
curl -X POST https://api.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

### 4. Message handling errors

**Symptoms:**
- Bot crashes on specific messages
- Unhandled exceptions in logs

**Solution:**
```bash
# 1. Find error in logs
bash agent/diagnostics.sh backend | grep -i "exception\|error" | tail -20

# 2. Check message handlers
grep -r "message.handler" backend/src/bot/

# 3. Verify handler registration
cat backend/src/bot/handlers/*.py | grep -A 5 "@router"

# 4. Check for missing dependencies
cd backend
uv sync
```

### 5. State machine stuck

**Symptoms:**
- User stuck in conversation flow
- Bot doesn't progress to next step
- Timeout errors

**Solution:**
```bash
# 1. Check current FSM states
docker exec -it <redis_container> redis-cli keys "fsm:*"

# 2. View specific user state
docker exec -it <redis_container> redis-cli get "fsm:user_id:<USER_ID>"

# 3. Clear user state (if stuck)
docker exec -it <redis_container> redis-cli del "fsm:user_id:<USER_ID>"

# 4. Check state definitions
cat backend/src/bot/states/*.py
```

## Bot Architecture Overview:

```
User Message → Telegram API → Webhook → FastAPI → aiogram Dispatcher
                                           ↓
                                    Handler Router
                                           ↓
                                    FSM State Machine
                                           ↓
                                    Business Logic
                                           ↓
                                    Response → Telegram API → User
```

### Key Components:
- `backend/src/bot/__init__.py` - Bot initialization
- `backend/src/bot/handlers/` - Message handlers
- `backend/src/bot/states/` - FSM state definitions
- `backend/src/bot/middlewares/` - Request/response middlewares
- `backend/src/bot/utils/` - Helper functions

## Testing Bot Manually:

### 1. Test Webhook Endpoint
```bash
curl -X POST https://api.yourdomain.com/api/bot/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 1,
    "message": {
      "message_id": 1,
      "from": {"id": 123, "first_name": "Test"},
      "chat": {"id": 123},
      "text": "/start"
    }
  }'
```

### 2. Check Bot Token Validity
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | jq
# Should return bot info
```

### 3. Monitor Real-time Logs
```bash
docker logs -f <backend_container> | grep -i "bot\|aiogram"
```

## Performance Optimization:

### 1. Gunicorn Workers
```yaml
# In docker-compose.traefik.prod.yml
backend:
  environment:
    - WORKERS=2  # Adjust based on server capacity
```

### 2. Redis Connection Pool
```python
# In backend/src/db/redis.py
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    max_connections=10,
    decode_responses=True
)
```

### 3. Rate Limiting
```python
# Add rate limiting middleware
@router.message_handler()
async def handle_message(message: types.Message):
    # Check rate limit
    if await is_rate_limited(message.from_user.id):
        return
    # Process message
```

## Emergency Procedures:

### Bot Completely Down
```bash
# 1. Stop backend
docker-compose -f docker-compose.traefik.prod.yml stop backend

# 2. Clear Redis cache
docker exec -it <redis_container> redis-cli flushdb

# 3. Restart backend
docker-compose -f docker-compose.traefik.prod.yml up -d backend

# 4. Verify webhook
bash agent/diagnostics.sh bot
```

### Mass User Complaints
```bash
# 1. Check error rate
bash agent/diagnostics.sh logs | grep -i "error" | wc -l

# 2. Identify common error
bash agent/diagnostics.sh logs | grep -i "error" | sort | uniq -c | sort -rn | head -10

# 3. Rollback if needed
git checkout <previous-stable-commit>
npm run prod:up
```

## Resources:
- `oac/guides/FIX-BOT-GUNICORN-WORKERS.md` - Worker configuration
- `oac/guides/FIX-BOT-WITHOUT-ENCRYPTION.md` - Bot without encryption
- `backend/src/bot/` - Bot source code
- `.ai-rules.md` - AI agent rules (always follow!)
