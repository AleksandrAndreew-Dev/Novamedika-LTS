# ⚡ Быстрое решение: Pharmacist Dashboard в Telegram

## 🎯 Самая простая конфигурация

### Изменить ТОЛЬКО ОДНУ переменную на сервере:

```bash
ssh user@server
cd /opt/novamedika-prod

# Открыть .env и изменить одну строку:
nano .env
```

**НАЙТИ:**
```
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
```

**ЗАМЕНИТЬ НА:**
```
PHARMACIST_DASHBOARD_URL=https://spravka.novamedika.com/pharmacist
```

Сохранить: `Ctrl+O` → `Enter` → `Ctrl+X`

### Перезапустить backend:

```bash
docker compose -f docker-compose.traefik.prod.yml restart backend
```

### Готово! ✅

Теперь кнопка "Панель фармацевта" в боте будет открывать WebApp по адресу:
`https://spravka.novamedika.com/pharmacist`

---

## 🧪 Проверка (2 минуты)

### 1. В браузере:
```
Откройте: https://spravka.novamedika.com/pharmacist
Результат: Страница входа или Dashboard
```

### 2. В Telegram:
```
1. Откройте @Novamedika_bot
2. Нажмите "💼 Панель фармацевта"
3. WebApp должен открыться внутри Telegram
```

### 3. Проверить логи:
```bash
docker logs backend-prod --tail 20 | grep pharmacist
```

Должны видеть:
```
GET /api/pharmacist/me HTTP/1.1" 200
```

---

## ❓ Если не работает

### Проблема: 404 ошибка
**Причина:** Traefik не маршрутизирует `/pharmacist`  
**Решение:** Проверить что frontend контейнер запущен и healthy

```bash
docker compose -f docker-compose.traefik.prod.yml ps
```

### Проблема: CORS ошибка
**Причина:** Неправильный CORS_ORIGINS  
**Решение:** Добавить основной домен

```bash
CORS_ORIGINS=https://spravka.novamedika.com,http://localhost:5173
```

Затем перезапустить backend:
```bash
docker compose -f docker-compose.traefik.prod.yml restart backend
```

### Проблема: WebApp не открывается в Telegram
**Причина:** CSP headers блокируют embedding  
**Проверка:**
```bash
curl -I https://spravka.novamedika.com/pharmacist | grep frame-ancestors
```

Должно быть:
```
frame-ancestors 'self' https://t.me https://web.telegram.org
```

Если нет - проверить Traefik configuration в `docker-compose.traefik.prod.yml`

---

## 🔍 Почему это проще?

| Подход | URL | Сложность |
|--------|-----|-----------|
| **Path-based (НОВЫЙ)** | `spravka.novamedika.com/pharmacist` | ✅ Простой |
| Subdomain-based (СТАРЫЙ) | `pharmacist.spravka.novamedika.com` | ❌ Сложный |

**Преимущества path-based:**
- ✅ Один SSL сертификат
- ✅ Нет CORS между поддоменами
- ✅ Одна DNS запись
- ✅ Frontend уже поддерживает
- ✅ Меньше точек отказа

---

## 📋 Чеклист изменений

- [ ] Изменил `PHARMACIST_DASHBOARD_URL` в `.env`
- [ ] Перезапустил backend контейнер
- [ ] Проверил в браузере (`/pharmacist`)
- [ ] Проверил в Telegram Bot
- [ ] Проверил логи (нет ошибок)

**Всё!** Больше ничего менять не нужно. Frontend и backend уже поддерживают этот подход.
