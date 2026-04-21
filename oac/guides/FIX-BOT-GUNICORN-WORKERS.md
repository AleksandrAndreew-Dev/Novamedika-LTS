# Исправление работы Telegram Bot с Gunicorn Workers

**Дата:** 21 апреля 2026 г.  
**Проблема:** Бот не работает из-за многопроцессорной архитектуры Gunicorn  
**Решение:** Каждый worker теперь имеет свою копию бота

---

## 🚀 Быстрое исправление (3 минуты)

### Шаг 1: Пересобрать и перезапустить backend

```bash
# На сервере выполнить:
cd /path/to/Novamedika2

# Пересобрать backend с новыми изменениями
docker-compose -f docker-compose.traefik.prod.yml build backend-prod

# Перезапустить backend
docker-compose -f docker-compose.traefik.prod.yml up -d backend-prod

# Подождать 30 секунд для инициализации
sleep 30

# Проверить логи
docker-compose -f docker-compose.traefik.prod.yml logs --tail=50 backend-prod
```

**Ожидаемый результат в логах:**
```
INFO:main:Worker PID 10: Initializing bot instance
INFO:bot.core:Bot initialized successfully with RedisStorage
INFO:main:Worker PID 10: Bot initialized successfully
INFO:main:Worker PID 10: Webhook set successfully: https://api.spravka.novamedika.com/webhook/
INFO:main:Worker PID 10: Bot ready to handle webhooks

INFO:main:Worker PID 11: Initializing bot instance
INFO:bot.core:Bot initialized successfully with RedisStorage
INFO:main:Worker PID 11: Bot initialized successfully
INFO:main:Worker PID 11: Webhook already configured by another worker
INFO:main:Worker PID 11: Bot ready to handle webhooks

INFO:main:Worker PID 12: Initializing bot instance
INFO:bot.core:Bot initialized successfully with RedisStorage
INFO:main:Worker PID 12: Bot initialized successfully
INFO:main:Worker PID 12: Webhook already configured by another worker
INFO:main:Worker PID 12: Bot ready to handle webhooks
```

### Шаг 2: Протестировать бота

1. Открыть Telegram
2. Найти бота NovaMedika2
3. Отправить `/start` или любой вопрос
4. **Ожидаемый результат:** Бот отвечает! 🎉

### Шаг 3: Проверить что ошибок 503 больше нет

```bash
# Проверить логи на ошибки webhook
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep "503"

# Должно быть пусто или только старые ошибки до перезапуска
```

---

## 🔍 Что было исправлено

### Проблема:

```python
# СТАРЫЙ КОД (НЕ РАБОТАЛ):
if not os.path.exists(init_lock_file):
    should_init = True  # Только первый worker
else:
    should_init = False  # Остальные workers пропускают

if should_init:
    bot, dp = await bot_manager.initialize()  # ❌ Только worker 10
# Workers 11 и 12 имеют bot_manager.bot = None
```

**Почему не работало:**
- Gunicorn создает 3 отдельных процесса (workers) через `fork()`
- После fork каждый worker имеет **свою копию памяти**
- Worker 10 инициализировал бота в своей памяти
- Workers 11 и 12 имели `bot_manager.bot = None` в своей памяти
- Webhook от Telegram мог попасть на любой worker
- Если попадал на worker 11 или 12 → ошибка 503

### Решение:

```python
# НОВЫЙ КОД (РАБОТАЕТ):
worker_pid = os.getpid()
logger.info(f"Worker PID {worker_pid}: Initializing bot instance")

# Каждый worker инициализирует СВОЮ копию бота
bot, dp = await bot_manager.initialize()  # ✅ Все workers

if bot and dp:
    logger.info(f"Worker PID {worker_pid}: Bot initialized successfully")
    
    # Register middleware...
    # Include routers...
    
    # Webhook устанавливается только один раз (первым worker)
    webhook_lock_file = "/tmp/webhook_lock"
    if not os.path.exists(webhook_lock_file):
        try:
            fd = os.open(webhook_lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            await bot.set_webhook(...)  # Только первый worker
        except FileExistsError:
            pass  # Другой worker уже установил
```

**Почему работает:**
- ✅ Каждый worker имеет своего бота и dispatcher
- ✅ Webhook может обработать любой worker
- ✅ Redis Storage общий для всех (сохраняет FSM состояния)
- ✅ Нет потери сообщений

---

## 📊 Архитектура после исправления

```
Telegram Server
       │
       ▼ (webhook POST)
   Traefik Proxy
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
  Worker PID 10  Worker PID 11  Worker PID 12
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Bot #1   │  │ Bot #2   │  │ Bot #3   │  ← Каждый worker имеет своего бота
  │ DP #1    │  │ DP #2    │  │ DP #3    │
  │ Routes   │  │ Routes   │  │ Routes   │
  └──────────┘  └──────────┘  └──────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
                      ▼
              Redis Server (DB 1)
              ┌─────────────────┐
              │  FSM Storage    │  ← Общий storage для всех workers
              │  (user states)  │
              └─────────────────┘
```

---

## ⚠️ Важные замечания

### Производительность:
- 3 workers × 1 bot instance = 3 bot instances total
- Каждый bot instance использует ~50-100 MB памяти
- Общая память backend: ~450 MB (в пределах лимита 1024 MB)

### Масштабируемость:
- Можно увеличить количество workers до 4-5 (если нужно больше throughput)
- Изменить в Dockerfile: `-w 3` → `-w 5`
- Но следить за потреблением памяти

### Webhook:
- Устанавливается только один раз (первым worker)
- При shutdown НЕ удаляется (чтобы избежать downtime)
- Если нужно удалить webhook вручную:
  ```bash
  curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
  ```

### Redis Storage:
- Общий для всех workers
- Сохраняет состояния диалогов (FSM)
- Работает корректно при переключении между workers

---

## 🆘 Troubleshooting

### Если бот все еще не работает:

```bash
# 1. Проверить что все workers запустились
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep "Worker PID"

# Должно быть 3 строки:
# Worker PID 10: Initializing bot instance
# Worker PID 11: Initializing bot instance
# Worker PID 12: Initializing bot instance

# 2. Проверить что боты инициализировались
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep "Bot initialized"

# Должно быть 3 строки "Bot initialized successfully"

# 3. Проверить webhook
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep "Webhook"

# Должно быть:
# Worker PID 10: Webhook set successfully
# Worker PID 11: Webhook already configured by another worker
# Worker PID 12: Webhook already configured by another worker

# 4. Проверить статус webhook в Telegram
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo" | jq
```

### Если видны ошибки инициализации:

```bash
# Проверить переменные окружения
docker-compose -f docker-compose.traefik.prod.yml exec backend-prod env | grep TELEGRAM

# Должны быть:
# TELEGRAM_BOT_TOKEN=<ваш токен>
# TELEGRAM_WEBHOOK_URL=https://api.spravka.novamedika.com/webhook/
# TELEGRAM_WEBHOOK_SECRET=<секрет если есть>

# Проверить подключение к Redis
docker-compose -f docker-compose.traefik.prod.yml exec backend-prod python -c "
from redis.asyncio import Redis
import asyncio
async def test():
    r = Redis(host='redis', port=6379, db=1, password='<REDIS_PASSWORD>')
    await r.ping()
    print('Redis OK')
asyncio.run(test())
"
```

---

## 📈 Мониторинг после исправления

### Через 1 час проверить:

```bash
# 1. Статус всех сервисов
docker-compose -f docker-compose.traefik.prod.yml ps

# 2. Количество обработанных webhook
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep "Webhook:" | wc -l

# 3. Ошибки (должно быть мало или ноль)
docker-compose -f docker-compose.traefik.prod.yml logs backend-prod | grep -i "error\|exception" | tail -20

# 4. Потребление ресурсов
docker stats --no-stream backend-prod
```

### Метрики успеха:
- ✅ Все 3 workers healthy
- ✅ Нет ошибок 503 в логах
- ✅ Бот отвечает на сообщения
- ✅ Пользователи могут задавать вопросы
- ✅ FSM состояния сохраняются корректно

---

## 💡 Технические детали

### Почему Gunicorn использует несколько workers?

**Преимущества:**
- Параллельная обработка запросов
- Лучшая утилизация CPU (3 workers на 1.5 CPU)
- Изоляция ошибок (краш одного worker не влияет на другие)

**Недостатки:**
- Больше потребление памяти
- Сложнее управление состоянием (нужен общий storage типа Redis)

### Почему нельзя использовать один worker?

Можно, но:
- ❌ Меньше throughput (последовательная обработка)
- ❌ Хуже использование CPU
- ❌ Один краш = весь backend down

**Рекомендация:** Оставить 3 workers для production.

---

**Статус:** ✅ Исправление готово к развертыванию  
**Время на исправление:** ~3 минуты  
**Влияние на пользователей:** Минимальное (перезапуск backend ~30 секунд)  
**Ожидаемый результат:** Бот работает стабильно на всех workers