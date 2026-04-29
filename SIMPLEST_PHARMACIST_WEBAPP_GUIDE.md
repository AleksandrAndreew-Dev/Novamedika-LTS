# 🚀 Как ПРОСТО открыть Pharmacist Dashboard через Telegram

## 📊 Анализ текущей ситуации

### Что работает сейчас ✅
1. **Backend API** - `/api/pharmacist/me` возвращает 200 OK
2. **CSP Headers** - Правильно настроены для Telegram WebApp
3. **Frontend** - Поддерживает оба режима (subdomain и path)
4. **JWT Authentication** - Токены генерируются и передаются корректно

### Проблема ⚠️
Текущая конфигурация использует **отдельный subdomain**:
- `https://pharmacist.spravka.novamedika.com` 

Это создает лишнюю сложность:
- ❌ Нужна отдельная DNS запись
- ❌ Возможны CORS проблемы между поддоменами
- ❌ Сложнее управление SSL сертификатами
- ❌ Два разных URL для одного приложения

---

## 💡 РЕШЕНИЕ: Использовать Path-based подход (ПРОЩЕ!)

### Новая архитектура
```
https://spravka.novamedika.com/          → Поиск лекарств (для всех)
https://spravka.novamedika.com/pharmacist → Dashboard фармацевта (только для авторизованных)
```

### Преимущества
✅ **Один домен** - проще SSL/TLS  
✅ **Нет CORS проблем** - same-origin policy  
✅ **Меньше DNS записей** - одна точка входа  
✅ **Проще деплой** - один Docker образ  
✅ **Frontend уже готов** - App.jsx проверяет путь `/pharmacist`  

---

## 🔧 Пошаговая инструкция

### Шаг 1: Обновить .env на сервере

```bash
ssh user@server
cd /opt/novamedika-prod
nano .env
```

Изменить строку:
```diff
- PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
+ PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

Сохранить (Ctrl+O, Enter, Ctrl+X)

### Шаг 2: Обновить код бота (опционально)

Файл: `backend/src/bot/handlers/common_handlers/keyboards.py`

Проверить что функция `generate_pharmacist_webapp_url()` использует правильную переменную окружения:

```python
base_url = os.getenv(
    "PHARMACIST_DASHBOARD_URL", 
    "https://spravka.novamedika.com/pharmacist"  # Default changed
)
```

**Важно:** Если `.env` правильно настроен, код менять не нужно - он уже читает из переменной!

### Шаг 3: Запушить изменения

```bash
git add .
git commit -m "fix: use path-based pharmacist dashboard URL for simpler Telegram WebApp integration"
git push origin main
```

### Шаг 4: Перезапустить production

```bash
ssh user@server
cd /opt/novamedika-prod

# Pull новые образы
docker compose -f docker-compose.traefik.prod.yml pull

# Перезапустить backend (чтобы перечитал .env)
docker compose -f docker-compose.traefik.prod.yml restart backend

# Проверить статус
docker compose -f docker-compose.traefik.prod.yml ps
```

---

## ✅ Проверка работы

### 1. В браузере (desktop/mobile)

Откройте: `https://spravka.novamedika.com/pharmacist`

**Ожидаемый результат:**
- Если НЕ авторизован → Страница входа
- Если авторизован → Dashboard с вкладками (Статистика, Консультации, Профиль)

### 2. В Telegram Bot

1. Откройте бота [@Novamedika_bot](https://t.me/Novamedika_bot)
2. Нажмите кнопку **"💼 Панель фармацевта"**
3. Должен открыться Telegram WebApp

**Ожидаемый результат:**
- WebApp открывается внутри Telegram
- JWT токен автоматически передается в URL (`?token=xxx`)
- Frontend извлекает токен и сохраняет в localStorage
- API запросы работают (проверьте Network tab в DevTools)

### 3. Проверка логов

```bash
# Backend логи
docker logs backend-prod --tail 50

# Frontend логи
docker logs frontend-prod --tail 50

# Traefik access logs
docker logs traefik --tail 50
```

**Что искать:**
- ✅ `GET /api/pharmacist/me HTTP/1.1" 200` - успешные API вызовы
- ❌ Нет CORS ошибок
- ❌ Нет 404 ошибок на `/pharmacist`

---

## 🔍 Troubleshooting

### Проблема: WebApp не открывается в Telegram

**Решение 1:** Проверить CSP headers
```bash
curl -I https://spravka.novamedika.com/pharmacist
```

Должны увидеть:
```
content-security-policy: ... frame-ancestors 'self' https://t.me https://web.telegram.org; ...
```

**Решение 2:** Проверить Traefik routing
```bash
docker exec traefik traefik healthcheck
```

**Решение 3:** Проверить browser console
1. Откройте WebApp в Telegram
2. На desktop: Ctrl+Shift+I (DevTools)
3. Проверьте Console и Network tabs на ошибки

### Проблема: 404 ошибка на /pharmacist

**Причина:** Traefik не маршрутизирует путь на frontend

**Решение:** Проверить `docker-compose.traefik.prod.yml`:
```yaml
labels:
  - "traefik.http.routers.frontend.rule=Host(`spravka.novamedika.com`)"
  # Должен ловить ВСЕ пути, включая /pharmacist
```

### Проблема: CORS ошибки

**Причина:** Frontend и API на разных доменах

**Решение:** Убедиться что `CORS_ORIGINS` включает основной домен:
```bash
CORS_ORIGINS=https://spravka.novamedika.com,http://localhost:5173
```

### Проблема: JWT токен не работает

**Проверка:**
1. Откройте WebApp
2. DevTools → Application → Local Storage
3. Проверьте наличие `access_token`

**Если токена нет:**
- URL должен содержать `?token=xxx`
- Frontend должен извлечь его в `useAuth` hook
- Проверьте `frontend/src/pharmacist/hooks/useAuth.js`

---

## 📱 Как это работает (технические детали)

### Flow аутентификации

```
1. Фармацевт нажимает кнопку в Telegram Bot
   ↓
2. Bot генерирует JWT токен с pharmacist UUID
   ↓
3. Открывается WebApp URL: https://spravka.novamedika.com/pharmacist?token=xxx
   ↓
4. Frontend (App.jsx) определяет режим по пути /pharmacist
   ↓
5. useAuth hook извлекает токен из URL
   ↓
6. Токен сохраняется в localStorage
   ↓
7. API запросы используют токен из localStorage
   ↓
8. Backend валидирует токен и возвращает данные фармацевта
```

### Код определения режима (App.jsx)

```javascript
const isPharmacistPath = window.location.pathname.startsWith('/pharmacist');
const hasAuthToken = new URLSearchParams(window.location.search).has('token');
const isPharmacistMode = isPharmacistPath || hasAuthToken;

if (isPharmacistMode) {
  return <PharmacistDashboard />;
} else {
  return <Search />; // Обычный поиск лекарств
}
```

### Генерация JWT токена (keyboards.py)

```python
def generate_pharmacist_webapp_url(telegram_id: int, pharmacist_uuid: str):
    token_data = {
        "sub": pharmacist_uuid,  # UUID фармацевта
        "telegram_id": telegram_id,
        "role": "pharmacist",
        "type": "access",
    }
    
    access_token = create_access_token(data=token_data)
    
    base_url = os.getenv("PHARMACIST_DASHBOARD_URL")
    return f"{base_url}?token={access_token}"
```

---

## 🎯 Итоговый чеклист

- [ ] Изменен `PHARMACIST_DASHBOARD_URL` в `.env` на сервере
- [ ] Перезапущен backend контейнер
- [ ] Push изменений в Git (если меняли код)
- [ ] Проверено открытие в браузере: `https://spravka.novamedika.com/pharmacist`
- [ ] Проверено открытие через Telegram Bot
- [ ] Проверены логи (нет ошибок)
- [ ] Проверена аутентификация (API возвращает 200 OK)
- [ ] Проверены CSP headers (разрешают Telegram embedding)

---

## 📞 Если нужна помощь

Проверьте эти файлы:
- Логи: `agent/server-logs/*.txt`
- Документация: `SIMPLIFIED_PHARMACIST_INTEGRATION.md`
- Код keyboard: `backend/src/bot/handlers/common_handlers/keyboards.py`
- Frontend routing: `frontend/src/App.jsx`

Или создайте issue в GitHub с описанием проблемы и логами.
