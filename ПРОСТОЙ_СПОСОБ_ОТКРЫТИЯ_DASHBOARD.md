# 🎯 Самый простой способ открыть Dashboard фармацевта через Telegram

## Краткий ответ

**Измените ОДНУ строку в `.env` на сервере:**

```bash
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

**Перезапустите backend:**
```bash
docker compose restart backend
```

**Готово!** ✅ Кнопка в боте теперь будет открывать WebApp надежно.

---

## Что было проверено

### ✅ Логи сервера (agent/server-logs/)
- Backend работает нормально
- API `/api/pharmacist/me` возвращает 200 OK
- Нет критических ошибок

### ✅ CSP Headers
- Правильно настроены для Telegram WebApp
- `frame-ancestors 'self' https://t.me https://web.telegram.org` разрешает встраивание

### ✅ Frontend код
- Поддерживает оба режима: subdomain и path
- `App.jsx` проверяет путь `/pharmacist`
- JWT токен извлекается из URL автоматически

### ✅ Bot keyboard
- Генерирует JWT токен с pharmacist UUID
- Передает токен как query параметр `?token=xxx`
- Использует переменную окружения `PHARMACIST_DASHBOARD_URL`

---

## Проблема текущей конфигурации

Сейчас используется **отдельный поддомен**:
```
https://pharmacist.spravka.novamedika.com
```

**Минусы:**
- ❌ Нужна отдельная DNS запись
- ❌ Возможны CORS проблемы между поддоменами
- ❌ Сложнее управление SSL сертификатами
- ❌ Два разных URL для одного приложения

---

## Решение: Path-based подход

Использовать **путь вместо поддомена**:
```
https://spravka.novamedika.com/pharmacist
```

**Плюсы:**
- ✅ Один домен - проще SSL/TLS
- ✅ Нет CORS проблем (same-origin)
- ✅ Меньше DNS записей
- ✅ Проще деплой
- ✅ Frontend уже поддерживает!

---

## Пошаговая инструкция

### Шаг 1: Подключиться к серверу

```bash
ssh user@server
cd /opt/novamedika-prod
```

### Шаг 2: Изменить .env

```bash
nano .env
```

Найти строку:
```
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
```

Заменить на:
```
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

Сохранить: `Ctrl+O` → `Enter` → `Ctrl+X`

### Шаг 3: Перезапустить backend

```bash
docker compose -f docker-compose.traefik.prod.yml restart backend
```

### Шаг 4: Проверить работу

#### В браузере:
Откройте: `https://spravka.novamedika.com/pharmacist`

Должна показаться страница входа или dashboard.

#### В Telegram:
1. Откройте бота [@Novamedika_bot](https://t.me/Novamedika_bot)
2. Нажмите кнопку **"💼 Панель фармацевта"**
3. Должен открыться WebApp внутри Telegram

#### Проверить логи:
```bash
docker logs backend-prod --tail 50 | grep pharmacist
```

Должны видеть успешные запросы:
```
GET /api/pharmacist/me HTTP/1.1" 200
```

---

## Как это работает

### 1. Фармацевт нажимает кнопку в боте

Bot генерирует URL с JWT токеном:
```
https://spravka.novamedika.com/pharmacist?token=eyJhbGci...
```

### 2. Открывается Telegram WebApp

Telegram загружает страницу внутри WebView.

### 3. Frontend определяет режим

`App.jsx` проверяет:
- Путь начинается с `/pharmacist`? → Да
- Есть токен в URL? → Да

Показывает компонент `PharmacistDashboard`.

### 4. Токен сохраняется

`useAuth` hook:
- Извлекает токен из URL
- Сохраняет в `localStorage`
- Очищает URL (убирает `?token=...`)

### 5. API запросы работают

Все запросы к backend включают токен:
```
Authorization: Bearer eyJhbGci...
```

Backend валидирует токен и возвращает данные фармацевта.

---

## Troubleshooting

### Проблема: WebApp не открывается

**Проверьте CSP headers:**
```bash
curl -I https://spravka.novamedika.com/pharmacist | grep frame-ancestors
```

Должно быть:
```
frame-ancestors 'self' https://t.me https://web.telegram.org
```

Если нет - проверьте Traefik configuration.

### Проблема: 404 ошибка

**Причина:** Traefik не маршрутизирует `/pharmacist`

**Решение:** Убедитесь что frontend контейнер запущен:
```bash
docker compose ps
```

### Проблема: CORS ошибка

**Причина:** Неправильный `CORS_ORIGINS`

**Решение:** Проверьте `.env`:
```bash
CORS_ORIGINS=https://spravka.novamedika.com,http://localhost:5173
```

Затем перезапустите backend.

### Проблема: JWT токен не работает

**Проверьте:**
1. Откройте WebApp
2. DevTools → Application → Local Storage
3. Должен быть ключ `access_token`

Если нет - URL должен содержать `?token=xxx`

---

## Чеклист

- [ ] Изменил `PHARMACIST_DASHBOARD_URL` в `.env`
- [ ] Перезапустил backend контейнер
- [ ] Проверил в браузере (`/pharmacist`)
- [ ] Проверил в Telegram Bot
- [ ] Проверил логи (нет ошибок)
- [ ] Проверил localStorage (есть access_token)
- [ ] Проверил API запросы (возвращают 200 OK)

---

## Дополнительные материалы

- 📖 Подробное руководство: `SIMPLEST_PHARMACIST_WEBAPP_GUIDE.md`
- ⚡ Быстрая шпаргалка: `QUICK_FIX_PHARMACIST_WEBAPP.md`
- 📊 Визуальная схема: `VISUAL_PHARMACIST_WEBAPP_GUIDE.md`
- 🏗️ Архитектура: `SIMPLIFIED_PHARMACIST_INTEGRATION.md`

---

## Итог

**Для надежного открытия Dashboard через Telegram нужно:**

1. ✅ Изменить одну переменную в `.env`
2. ✅ Перезапустить backend
3. ✅ Готово!

Больше ничего менять не нужно. Frontend и backend уже поддерживают этот подход.

**Время выполнения:** 5 минут  
**Сложность:** Очень низкая  
**Риск:** Минимальный  
