# Упрощенная интеграция Pharmacist Dashboard в основное приложение

## 📋 Новая концепция

Вместо создания отдельного React приложения с routing, pharmacist dashboard теперь **интегрирован в основное приложение** и открывается по специальному URL пути `/pharmacist`.

### Архитектура:

```
spravka.novamedika.com/          → Поиск лекарств (для всех)
spravka.novamedika.com/pharmacist → Dashboard фармацевта (только для авторизованных)
```

---

## ✅ Преимущества нового подхода

1. **Проще** - нет необходимости в react-router-dom
2. **Единый build** - один Docker образ для всего frontend
3. **Меньше зависимостей** - не нужно управлять несколькими entry points
4. **Легче поддерживать** - общий код, общие компоненты
5. **Telegram WebApp friendly** - открывается как отдельная страница внутри Telegram

---

## 🔧 Как это работает

### 1. Определение режима в App.jsx

Приложение проверяет URL path:
```javascript
const isPharmacistMode = window.location.pathname.startsWith('/pharmacist');

if (isPharmacistMode) {
  return <PharmacistDashboard />;
}
```

### 2. PharmacistDashboard компонент

Показывает:
- **Страницу входа** если пользователь не авторизован
- **Dashboard** с тремя вкладками:
  - 📊 Статистика (DashboardStats)
  - 💬 Консультации (QuestionsList)
  - 👤 Профиль

### 3. Аутентификация

Использует существующий `useAuth` hook:
- Проверка JWT токена
- Автоматическая переаутентификация через Telegram
- Защищенные роуты

---

## 🚀 Деплой

### Шаг 1: Запушить изменения

```bash
git add .
git commit -m "feat: simplify pharmacist dashboard integration into main app"
git push origin main
```

### Шаг 2: CI/CD автоматически соберет образ

GitHub Actions:
- Соберет frontend с правильными VITE_API_URL
- Создаст один образ `frontend:latest`
- Запушит в GHCR

### Шаг 3: Обновить production

```bash
ssh user@server
cd /opt/novamedika-prod

# Pull новый образ
docker compose -f docker-compose.traefik.prod.yml pull frontend

# Перезапустить
docker compose -f docker-compose.traefik.prod.yml up -d frontend

# Проверить статус
docker compose -f docker-compose.traefik.prod.yml ps
```

---

## 📱 Использование в Telegram Bot

### Настройка кнопки в Bot:

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💊 Поиск лекарств")],
        [KeyboardButton(
            text="💼 Панель фармацевта",
            web_app=WebAppInfo(url="https://spravka.novamedika.com/pharmacist")
        )]
    ],
    resize_keyboard=True
)
```

### Flow пользователя:

1. Фармацевт открывает бота
2. Нажимает "💼 Панель фармацевта"
3. Открывается Telegram WebApp на `/pharmacist`
4. Если не авторизован - показывает страницу входа
5. После входа - видит dashboard с консультациями

---

## 🔍 Проверка работы

### 1. Основной сайт (для клиентов):
Откройте [https://spravka.novamedika.com/](https://spravka.novamedika.com/)
- ✅ Показывает поиск лекарств
- ✅ Выбор города
- ✅ Бронирование в аптеках

### 2. Pharmacist Dashboard:
Откройте [https://spravka.novamedika.com/pharmacist](https://spravka.novamedika.com/pharmacist)
- ✅ Если не авторизован - страница входа
- ✅ Если авторизован - dashboard со статистикой
- ✅ Вкладки: Дашборд, Консультации, Профиль

### 3. В Telegram:
- Откройте бота
- Нажмите кнопку "Панель фармацевта"
- Должен открыться WebApp с dashboard

---

## 📊 Структура файлов

```
frontend/src/
├── App.jsx                          ← Определяет режим (обычный/pharmacist)
├── pharmacist/
│   ├── PharmacistDashboard.jsx     ← Главный компонент dashboard
│   ├── hooks/
│   │   └── useAuth.js              ← Аутентификация
│   ├── services/
│   │   ├── authService.js
│   │   ├── questionsService.js
│   │   └── websocketService.js
│   ├── components/
│   │   ├── auth/
│   │   │   ├── Login.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── layout/
│   │   │   ├── MainLayout.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── dashboard/
│   │   │   └── DashboardStats.jsx  ← Статистика
│   │   └── consultations/
│   │       └── QuestionsList.jsx   ← Список консультаций
│   └── pages/
│       └── Dashboard.jsx           ← (можно удалить, не используется)
```

---

## ⚠️ Важные замечания

### 1. Nginx конфигурация

Убедитесь что nginx правильно обрабатывает `/pharmacist` path. Файл `nginx-pharmacist.conf` должен быть настроен на отдачу index.html для всех путей (SPA fallback).

### 2. CORS

Backend должен разрешать запросы с `https://spravka.novamedika.com` (общий домен).

### 3. WebSocket

WebSocket подключение использует тот же endpoint:
```
wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist
```

### 4. Аутентификация

JWT tokens хранятся в localStorage и работают для обоих режимов (обычный + pharmacist).

---

## 🎯 Результат

После применения:

| URL | Назначение | Доступ |
|-----|-----------|--------|
| `spravka.novamedika.com/` | Поиск лекарств | Все пользователи |
| `spravka.novamedika.com/pharmacist` | Dashboard фармацевта | Только авторизованные фармацевты |
| `api.spravka.novamedika.com` | Backend API | Общий для всех |

**Преимущества:**
- ✅ Один Docker образ
- ✅ Простая архитектура
- ✅ Легко поддерживать
- ✅ Идеально для Telegram WebApp
- ✅ Нет лишних зависимостей

---

## 🛠️ Troubleshooting

### Проблема: 404 при открытии /pharmacist

**Решение:** Проверьте nginx конфигурацию. Должен быть fallback на index.html:
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### Проблема: Не работает аутентификация

**Решение:** 
1. Проверьте что JWT token сохранен в localStorage
2. Убедитесь что backend принимает токен
3. Проверьте console на ошибки CORS

### Проблема: Компоненты не загружаются

**Решение:**
1. Проверьте импорты в PharmacistDashboard.jsx
2. Убедитесь что все файлы существуют
3. Запустите `npm run lint` для проверки ошибок
