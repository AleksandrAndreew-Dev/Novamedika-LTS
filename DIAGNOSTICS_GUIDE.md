# 📊 Диагностика Pharmacist WebApp

## ✅ Обновленный скрипт диагностики

Скрипт [`agent/diagnostics.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\agent\diagnostics.sh) расширен для полной диагностики Pharmacist WebApp.

---

## 🎯 Что добавлено

### 1. **Новая функция `run_pharmacist()`**

Проверяет все аспекты Pharmacist WebApp:

```bash
✅ Статус контейнера и health check
✅ Логи (последние 200 строк)
✅ Использование ресурсов (RAM, CPU)
✅ HTTPS доступность
✅ Traefik routing логи
✅ Переменные окружения
✅ CORS конфигурация
✅ API endpoints тестирование
✅ WebSocket endpoint проверка
```

### 2. **Обновленные функции**

#### `run_logs()` - теперь включает pharmacist_webapp:
```bash
for container in backend frontend pharmacist_webapp celery_worker traefik postgres redis; do
    docker compose logs $container --tail=1000
done
```

#### `run_env()` - показывает образ pharmacist-webapp-prod:
```bash
for c in backend-prod frontend-prod pharmacist-webapp-prod celery-worker-prod ...; do
    docker inspect $c --format="{{.Config.Image}}"
done
```

#### `run_db()` - проверяет таблицу qa_dialog_messages:
```sql
SELECT 'qa_dialog_messages', count(*) FROM qa_dialog_messages
```

#### `run_network()` - проверяет DNS pharmacist.spravka.novamedika.com:
```bash
host pharmacist.spravka.novamedika.com
```

---

## 🚀 Использование

### Полная диагностика (включая Pharmacist WebApp)

```bash
./agent/diagnostics.sh all
```

или просто:
```bash
./agent/diagnostics.sh
```

### Только Pharmacist WebApp диагностика

```bash
./agent/diagnostics.sh pharmacist
```

### Другие режимы

```bash
./agent/diagnostics.sh status      # Статус всех контейнеров
./agent/diagnostics.sh logs        # Логи всех сервисов
./agent/diagnostics.sh backend     # Логи backend
./agent/diagnostics.sh frontend    # Логи frontend
./agent/diagnostics.sh bot         # Диагностика бота
./agent/diagnostics.sh db          # БД и Redis
./agent/diagnostics.sh network     # Сеть и DNS
./agent/diagnostics.sh env         # Конфигурация
```

---

## 📋 Вывод диагностики Pharmacist WebApp

Пример вывода команды `./agent/diagnostics.sh pharmacist`:

```
💊 Диагностика Pharmacist WebApp...

=== Pharmacist WebApp Container Status ===
running (healthy)

=== Pharmacist WebApp Logs (last 200 lines) ===
pharmacist-webapp-prod  | 192.168.1.1 - - [28/Apr/2026:09:30:00 +0000] "GET / HTTP/1.1" 200 1234
pharmacist-webapp-prod  | 192.168.1.1 - - [28/Apr/2026:09:30:01 +0000] "GET /assets/index.js HTTP/1.1" 200 45678

=== Pharmacist WebApp Memory Usage ===
NAME                       MEM USAGE / LIMIT     CPU %
pharmacist-webapp-prod     12.5MiB / 64MiB       0.05%

=== Pharmacist WebApp HTTPS Test ===
HTTP/2 200 
content-type: text/html
server: nginx/1.25.4

=== Traefik Routes for Pharmacist ===
traefik-prod  | time="2026-04-28T09:30:00Z" level=info msg="Router created: pharmacist-webapp@docker"

=== Pharmacist Dashboard URL Config ===
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
VITE_WS_URL_PHARMACIST=wss://api.spravka.novamedika.com/ws/pharmacist

=== CORS Origins ===
CORS_ORIGINS=["https://spravka.novamedika.com","https://pharmacist.spravka.novamedika.com","http://localhost:5173"]

=== Pharmacist API Endpoints Test ===
Testing: GET /api/pharmacist/questions/unread-count
HTTP Status: 401  # Ожидается - требуется аутентификация

=== Pharmacist WebSocket Endpoint ===
WebSocket URL: wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
(Manual test required - use browser console or wscat)

✅ Pharmacist WebApp: agent/server-logs/20260428_093000_pharmacist-webapp.txt
```

---

## 🔍 Troubleshooting через диагностику

### Проблема 1: Контейнер не запускается

```bash
./agent/diagnostics.sh pharmacist
```

**Что смотреть:**
- Container Status: должен быть `running (healthy)`
- Если `restarting` - смотрите логи
- Если `exited` - проверьте `docker logs pharmacist-webapp-prod`

### Проблема 2: HTTPS не работает

**Что смотреть в диагностике:**
```
=== Pharmacist WebApp HTTPS Test ===
curl: (7) Failed to connect to pharmacist.spravka.novamedika.com port 443
```

**Решение:**
1. Проверьте DNS: `./agent/diagnostics.sh network`
2. Проверьте Traefik: `docker logs traefik-prod | grep pharmacist`
3. Проверьте SSL сертификат: `ls -la /opt/novamedika-prod/letsencrypt/`

### Проблема 3: API endpoints недоступны

**Что смотреть:**
```
=== Pharmacist API Endpoints Test ===
HTTP Status: 502  # Bad Gateway
```

**Решение:**
1. Проверьте backend: `./agent/diagnostics.sh backend`
2. Убедитесь, что роутер зарегистрирован в main.py
3. Проверьте CORS настройки

### Проблема 4: WebSocket не подключается

**Что смотреть:**
```
=== Pharmacist WebSocket Endpoint ===
WebSocket URL: wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
```

**Тест вручную:**
```bash
# Установите wscat
npm install -g wscat

# Тест
wscat -c wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
```

---

## 📊 Автоматизация мониторинга

### Cron job для ежедневной диагностики

```bash
# Откройте crontab
crontab -e

# Добавьте ежедневную диагностику в 6:00 AM
0 6 * * * /opt/novamedika-prod/agent/diagnostics.sh all >> /var/log/novamedika-diagnostics.log 2>&1
```

### Alert при проблемах

```bash
#!/bin/bash
# alert-check.sh

./agent/diagnostics.sh pharmacist > /tmp/pharmacist-check.txt 2>&1

if grep -q "unhealthy" /tmp/pharmacist-check.txt; then
    echo "⚠️ Pharmacist WebApp unhealthy!" | mail -s "Alert: Novamedika" admin@example.com
fi

if grep -q "Failed to connect" /tmp/pharmacist-check.txt; then
    echo "⚠️ Pharmacist WebApp HTTPS failed!" | mail -s "Alert: Novamedika" admin@example.com
fi
```

---

## 📁 Структура выходных файлов

После запуска `./agent/diagnostics.sh all`:

```
agent/server-logs/
├── 20260428_093000_status.txt           # Статус контейнеров
├── 20260428_093000_all-logs.txt         # Все логи
├── 20260428_093000_errors-only.txt      # Только ошибки
├── 20260428_093000_env-info.txt         # Конфигурация
├── 20260428_093000_db-redis.txt         # БД и Redis
├── 20260428_093000_bot-diagnostics.txt  # Бот диагностика
├── 20260428_093000_pharmacist-webapp.txt # ← НОВОЕ: Pharmacist WebApp
└── 20260428_093000_network.txt          # Сеть
```

---

## 🎯 Quick Commands

```bash
# Быстрая проверка Pharmacist WebApp
./agent/diagnostics.sh pharmacist | grep -E "Status|HTTPS|Memory"

# Проверить только ошибки
./agent/diagnostics.sh all && cat agent/server-logs/*_errors-only.txt

# Мониторинг в реальном времени
watch -n 30 './agent/diagnostics.sh pharmacist'

# Сохранить диагностику с комментарием
./agent/diagnostics.sh pharmacist > diagnostic-$(date +%Y%m%d)-issue-description.txt
```

---

## ✅ Чеклист перед деплоем

Перед каждым деплоем Pharmacist WebApp запустите:

```bash
# 1. Проверьте текущее состояние
./agent/diagnostics.sh pharmacist

# 2. Задеплойте новую версию
produp

# 3. Подождите 2 минуты
sleep 120

# 4. Проверьте после деплоя
./agent/diagnostics.sh pharmacist

# 5. Сравните результаты
diff <(cat agent/server-logs/*_pharmacist-webapp.txt | head -50) \
     <(./agent/diagnostics.sh pharmacist 2>&1 | head -50)
```

---

## 🎉 Готово!

Теперь у вас есть полная диагностика Pharmacist WebApp:

✅ **Автоматическая проверка** всех компонентов  
✅ **Логи и метрики** в одном месте  
✅ **Быстрое выявление проблем**  
✅ **История диагностик** для анализа трендов  
✅ **Интеграция с CI/CD** (можно запускать после деплоя)  

**Используйте `./agent/diagnostics.sh pharmacist` для быстрой проверки!** 🚀
