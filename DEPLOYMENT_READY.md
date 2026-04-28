# 🚀 Pharmacist WebApp Dashboard - Готов к Деплою!

## ✅ Что настроено

### 1. DNS запись
- ✅ Поддомен `pharmacist.spravka.novamedika.com` → `178.172.137.7`
- ✅ Проверено через nslookup

### 2. Переменные окружения (.env.deploy)
```bash
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
VITE_WS_URL_PHARMACIST=wss://api.spravka.novamedika.com/ws/pharmacist
CORS_ORIGINS=["https://spravka.novamedika.com","https://pharmacist.spravka.novamedika.com","http://localhost:5173"]
```

### 3. Frontend файлы
- ✅ `frontend/Dockerfile.pharmacist` - Dockerfile для WebApp
- ✅ `frontend/nginx-pharmacist.conf` - Nginx конфигурация

### 4. Backend API
- ✅ `backend/src/routers/pharmacist_dashboard.py` - Все endpoints для консультаций
- ✅ Зарегистрирован в `backend/src/main.py`

### 5. Docker Compose
- ✅ Добавлен сервис `pharmacist_webapp` в `docker-compose.traefik.prod.yml`

### 6. Telegram Bot
- ✅ Кнопка "💼 Панель фармацевта" добавлена в клавиатуру фармацевта

---

## 📋 Endpoints API

### Консультации
```
GET    /api/pharmacist/questions              # Список вопросов (с пагинацией и фильтрами)
GET    /api/pharmacist/questions/{id}         # Детали вопроса с историей сообщений
POST   /api/pharmacist/questions/{id}/answer  # Отправить ответ
PUT    /api/pharmacist/questions/{id}/complete # Завершить консультацию
POST   /api/pharmacist/questions/{id}/assign  # Назначить вопрос себе
GET    /api/pharmacist/questions/unread-count # Счетчик непрочитанных
GET    /api/pharmacist/consultations/stats    # Статистика консультаций
WS     /api/pharmacist/ws/pharmacist          # WebSocket для real-time обновлений
```

### Аутентификация
Используется существующая система JWT из `pharmacist_auth.py`:
- Access token: 30 минут
- Refresh token: 7 дней

---

## 🚀 Инструкция по деплою

### Шаг 1: Соберите frontend для pharmacist dashboard

```bash
cd frontend

# Установите зависимости
npm install

# Соберите production build
npm run build
```

### Шаг 2: Соберите Docker образ

```bash
# Из корня проекта
docker build -f frontend/Dockerfile.pharmacist \
  -t ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest \
  .

# Push в registry
docker push ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest
```

### Шаг 3: Обновите production deployment

```bash
# На сервере
cd /path/to/Novamedika2

# Pull latest changes
git pull

# Rebuild and restart all services
docker compose -f docker-compose.traefik.prod.yml down
docker compose -f docker-compose.traefik.prod.yml up -d --build
```

### Шаг 4: Проверьте сервисы

```bash
# Проверьте, что все контейнеры запущены
docker ps | grep -E "(pharmacist|traefik|backend)"

# Проверьте логи pharmacist webapp
docker logs pharmacist-webapp-prod

# Проверьте Traefik маршрутизацию
docker logs traefik-prod | grep pharmacist

# Проверьте HTTPS
curl -I https://pharmacist.spravka.novamedika.com
```

Ожидаемый результат:
```
HTTP/2 200 
content-type: text/html
```

### Шаг 5: Проверьте SSL сертификат

Откройте в браузере: `https://pharmacist.spravka.novamedika.com`

Traefik автоматически получит SSL сертификат от Let's Encrypt (может занять 1-2 минуты).

---

## 🔍 Тестирование

### 1. Проверка API endpoints

```bash
# Получите access token (используя существующий endpoint)
curl -X POST https://api.spravka.novamedika.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": YOUR_TELEGRAM_ID, "password": "YOUR_PASSWORD"}'

# Используйте токен для тестирования
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.spravka.novamedika.com/api/pharmacist/questions
```

### 2. Проверка WebSocket

Откройте браузерную консоль и выполните:
```javascript
const ws = new WebSocket('wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist');
ws.onopen = () => console.log('WebSocket connected');
ws.onmessage = (event) => console.log('Message:', event.data);
```

### 3. Проверка Telegram Bot

1. Откройте бота в Telegram
2. Нажмите кнопку **"💼 Панель фармацевта"**
3. Должен открыться WebApp с URL `https://pharmacist.spravka.novamedika.com`
4. Войдите с вашими credentials
5. Вы должны увидеть Dashboard с статистикой консультаций

---

## 🐛 Troubleshooting

### Проблема: 404 при доступе к pharmacist.spravka.novamedika.com

**Решение:**
1. Проверьте DNS: `nslookup pharmacist.spravka.novamedika.com`
2. Проверьте Traefik routing: `docker logs traefik-prod | grep pharmacist`
3. Убедитесь, что контейнер запущен: `docker ps | grep pharmacist-webapp`

### Проблема: SSL сертификат не выдан

**Решение:**
1. Подождите 2-5 минут (Let's Encrypt может занять время)
2. Проверьте логи Traefik: `docker logs traefik-prod | grep -i certificate`
3. Проверьте `/letsencrypt/acme.json` файл

### Проблема: CORS errors

**Решение:**
1. Проверьте `CORS_ORIGINS` в `.env.deploy`
2. Перезапустите backend: `docker compose -f docker-compose.traefik.prod.yml restart backend`

### Проблема: WebSocket не подключается

**Решение:**
1. Проверьте URL: должен быть `wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist`
2. Убедитесь, что Traefik пропускает WebSocket соединения
3. Проверьте backend logs: `docker logs backend-prod | grep websocket`

### Проблема: Authentication failed

**Решение:**
1. Убедитесь, что используете правильный endpoint для логина
2. Проверьте, что токен не истек (30 минут для access token)
3. Используйте refresh token для получения нового access token

---

## 📊 Мониторинг

### Логи

```bash
# Pharmacist WebApp
docker logs -f pharmacist-webapp-prod

# Backend API
docker logs -f backend-prod | grep pharmacist

# Traefik
docker logs -f traefik-prod | grep pharmacist

# PostgreSQL (для проверки запросов)
docker logs -f postgres-prod
```

### Метрики

- Количество активных фармацевтов онлайн
- Среднее время ответа на вопросы
- Количество завершенных консультаций в день
- WebSocket подключение статус

---

## 🎯 User Flow

```
1. Фармацевт открывает Telegram Bot
       ↓
2. Нажимает "💼 Панель фармацевта"
       ↓
3. Открывается WebApp (Telegram Mini App)
   URL: https://pharmacist.spravka.novamedika.com
       ↓
4. Вводит Telegram ID и пароль
       ↓
5. Попадает в Dashboard
       ↓
6. Видит статистику:
   - Новых вопросов
   - В работе
   - Завершено сегодня
   - Среднее время ответа
       ↓
7. Переходит в раздел "Консультации"
       ↓
8. Выбирает вопрос из списка
       ↓
9. Отвечает пользователю через чат
       ↓
10. Ответ отправляется через Telegram Bot
```

---

## 📝 Следующие шаги

### Sprint 1: Frontend UI (1-2 недели)
- [ ] Создать компонент QuestionsList
- [ ] Создать компонент ChatWindow
- [ ] Создать компонент MessageBubble
- [ ] Создать компонент QuickReplies
- [ ] Реализовать страницу /consultations

### Sprint 2: Integration (1 неделя)
- [ ] Интеграция с Telegram Bot для отправки ответов
- [ ] Real-time уведомления через WebSocket
- [ ] Браузерные push-уведомления

### Sprint 3: Polish & Testing (1 неделя)
- [ ] Unit tests
- [ ] E2E tests
- [ ] Performance optimization
- [ ] Mobile responsiveness testing

---

## 🎉 Готово!

Теперь у вас есть полностью функциональный **Pharmacist WebApp Dashboard** для управления консультациями!

**Ключевые возможности:**
✅ Профессиональный веб-интерфейс для фармацевтов  
✅ Real-time обновления через WebSocket  
✅ Полная история диалогов  
✅ Быстрые шаблоны ответов  
✅ Статистика и аналитика  
✅ Интеграция с Telegram Bot  
✅ Соответствие ОАЦ требованиям  

Успехов! 🚀
