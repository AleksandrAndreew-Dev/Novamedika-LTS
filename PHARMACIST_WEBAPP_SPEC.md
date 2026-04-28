# WebApp Dashboard для фармацевтов - Техническое задание

## 📋 Обзор проекта

**Цель:** Создание профессионального веб-интерфейса для фармацевтов, позволяющего эффективно управлять заказами бронирования, консультировать пользователей и отслеживать статистику работы.

**Подход:** Гибридная архитектура - пользователи остаются в Telegram Bot, фармацевты получают расширенный WebApp Dashboard.

---

## 🎯 Функциональные требования

### 1. Аутентификация и авторизация
- **JWT Authentication**: Использование существующей системы токенов из `pharmacist_auth.py`
- **Refresh Token**: Автоматическое обновление сессии
- **Logout**: Безопасный выход с отзывом токенов
- **Session Management**: Отображение статуса онлайн/офлайн

### 2. Управление заказами бронирования

#### 2.1 Список заказов (Orders List)
- Табличное представление всех заказов аптеки
- Фильтры по статусу: `pending`, `confirmed`, `cancelled`, `failed`
- Сортировка по дате создания (новые сверху)
- Пагинация (20 заказов на страницу)
- Поиск по имени клиента или номеру телефона
- Real-time обновление через WebSocket

**Колонки таблицы:**
- ID заказа
- Название препарата
- Количество упаковок
- Имя клиента
- Телефон клиента
- Статус (с цветовой индикацией)
- Дата создания
- Действия (подтвердить/отменить/просмотреть)

#### 2.2 Детали заказа (Order Details)
- Полная информация о заказе
- Данные о препарате (название, форма, производитель, цена)
- Данные о клиенте (имя, телефон, telegram_id если есть)
- История изменения статусов
- Кнопки действий:
  - ✅ Подтвердить заказ
  - ❌ Отменить заказ (с указанием причины)
  - 📞 Позвонить клиенту (tel: link)
  - 💬 Написать в Telegram (если есть telegram_id)

#### 2.3 Обновление статуса заказа
- Изменение статуса через API endpoint `/api/pharmacy/orders/{order_id}/status`
- Валидация переходов статусов
- Уведомление пользователя в Telegram при изменении статуса
- Логирование всех изменений

### 3. Система консультаций (Q&A)

#### 3.1 Список вопросов
- Отображение вопросов от пользователей
- Фильтры: `pending`, `in_progress`, `answered`, `completed`
- Индикация новых вопросов (badge)
- Предпросмотр текста вопроса
- Время создания вопроса

#### 3.2 Диалог с пользователем
- Чат-интерфейс (как в мессенджере)
- История сообщений с временными метками
- Возможность прикреплять фото рецептов
- Быстрые шаблоны ответов
- Кнопка "Завершить консультацию"

#### 3.3 Управление статусом фармацевта
- Переключение онлайн/офлайн
- Отображение текущего статуса
- Время последней активности

### 4. Дашборд и статистика

#### 4.1 Основные метрики
- Количество заказов сегодня
- Количество активных консультаций
- Среднее время ответа
- Конверсия бронирований

#### 4.2 Графики и визуализация
- Заказы по дням (линейный график)
- Распределение по статусам (pie chart)
- Топ препаратов (bar chart)

### 5. Профиль фармацевта
- Информация об аптеке (название, адрес, телефон)
- Личные данные (ФИО, должность)
- Настройки уведомлений
- Смена пароля

---

## 🏗️ Архитектура системы

### Frontend (React 19 + Vite)

```
frontend/src/
├── pharmacist/                  # Новая папка для фармацевта
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── dashboard/
│   │   │   ├── StatsCards.jsx
│   │   │   ├── OrdersChart.jsx
│   │   │   └── QuickActions.jsx
│   │   ├── orders/
│   │   │   ├── OrdersTable.jsx
│   │   │   ├── OrderFilters.jsx
│   │   │   ├── OrderDetails.jsx
│   │   │   └── StatusBadge.jsx
│   │   ├── consultations/
│   │   │   ├── QuestionsList.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   └── QuickReplies.jsx
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Header.jsx
│   │   │   └── MainLayout.jsx
│   │   └── common/
│   │       ├── LoadingSpinner.jsx
│   │       ├── EmptyState.jsx
│   │       └── ErrorBoundary.jsx
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Orders.jsx
│   │   ├── Consultations.jsx
│   │   └── Profile.jsx
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useWebSocket.js
│   │   ├── useOrders.js
│   │   └── useQuestions.js
│   ├── services/
│   │   ├── authService.js
│   │   ├── ordersService.js
│   │   ├── questionsService.js
│   │   └── websocketService.js
│   ├── store/
│   │   ├── authStore.js
│   │   └── appStore.js
│   └── routes/
│       └── PharmacistRoutes.jsx
```

### Backend (FastAPI)

```
backend/src/routers/
├── pharmacist_dashboard.py     # Новый router для WebApp
├── pharmacist_auth.py          # Существующий (расширить)
├── booking_orders.py           # Существующий (расширить)
└── qa.py                       # Существующий (расширить)

backend/src/services/
├── order_service.py            # Бизнес-логика заказов
├── notification_service.py     # Уведомления в Telegram
└── websocket_service.py        # WebSocket управление
```

---

## 🔌 API Endpoints

### Аутентификация
```
POST   /api/pharmacist/login/           # Вход
POST   /api/pharmacist/refresh/         # Обновление токена
POST   /api/pharmacist/logout/          # Выход
GET    /api/pharmacist/status           # Статус фармацевта
PUT    /api/pharmacist/online           # Перевести в онлайн
PUT    /api/pharmacist/offline          # Перевести в офлайн
```

### Заказы
```
GET    /api/pharmacist/orders                    # Список заказов (с фильтрами)
GET    /api/pharmacist/orders/{order_id}         # Детали заказа
PUT    /api/pharmacist/orders/{order_id}/status  # Обновить статус
GET    /api/pharmacist/orders/stats              # Статистика заказов
```

### Консультации
```
GET    /api/pharmacist/questions                 # Список вопросов
GET    /api/pharmacist/questions/{question_id}   # Детали вопроса + сообщения
POST   /api/pharmacist/questions/{question_id}/answer  # Ответить
PUT    /api/pharmacist/questions/{question_id}/complete  # Завершить
WS     /ws/pharmacist                            # WebSocket для real-time
```

### Профиль
```
GET    /api/pharmacist/profile                   # Получить профиль
PUT    /api/pharmacist/profile                   # Обновить профиль
```

---

## 🎨 UI/UX Дизайн

### Цветовая схема
- **Primary**: `#0088cc` (Telegram blue)
- **Success**: `#10b981` (зеленый для confirmed)
- **Warning**: `#f59e0b` (желтый для pending)
- **Danger**: `#ef4444` (красный для cancelled)
- **Background**: `#f8fafc` (светло-серый)
- **Surface**: `#ffffff` (белый)

### Типографика
- **Font Family**: Inter, system-ui, sans-serif
- **Base Size**: 16px
- **Headings**: 24px (h1), 20px (h2), 18px (h3)

### Компоненты
- Использовать Tailwind CSS (уже настроен)
- Shadcn/ui или Headless UI для сложных компонентов
- React Query для управления состоянием сервера
- Zustand для глобального состояния

### Адаптивность
- Mobile-first подход
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Touch-friendly элементы (min 48x48px)

---

## ⚡ Real-time функциональность

### WebSocket события

**От сервера к клиенту:**
```json
{
  "type": "new_order",
  "data": {
    "order_id": "uuid",
    "product_name": "Парацетамол",
    "customer_name": "Иван Иванов",
    "created_at": "2026-04-28T10:00:00Z"
  }
}
```

```json
{
  "type": "order_status_updated",
  "data": {
    "order_id": "uuid",
    "status": "confirmed"
  }
}
```

```json
{
  "type": "new_question",
  "data": {
    "question_id": "uuid",
    "text": "Есть ли в наличии...",
    "user_name": "Мария"
  }
}
```

**От клиента к серверу:**
```json
{
  "type": "subscribe_to_pharmacy",
  "data": {
    "pharmacy_id": "uuid"
  }
}
```

---

## 🔐 Безопасность

### Соответствие ОАЦ требованиям
- ✅ JWT токены с expiration (30 минут access, 7 дней refresh)
- ✅ HTTPS (Traefik с Let's Encrypt)
- ✅ Шифрование персональных данных в БД (pgcrypto)
- ✅ Логирование всех действий фармацевта
- ✅ Rate limiting на endpoints
- ✅ CORS policy (только разрешенные домены)
- ✅ Content Security Policy headers

### Защита от атак
- XSS: Sanitization input данных
- CSRF: SameSite cookies для refresh token
- SQL Injection: Parameterized queries (SQLAlchemy ORM)
- Brute Force: Rate limiting на login endpoint

---

## 📱 Telegram Mini App интеграция

### Инициализация
```javascript
import { WebApp } from '@twa-dev/sdk';

// Инициализация при загрузке
WebApp.ready();
WebApp.expand();

// Получение данных пользователя
const initData = WebApp.initDataUnsafe;
const user = initData.user; // { id, first_name, username, ... }
```

### Haptic Feedback
```javascript
WebApp.HapticFeedback.impactOccurred('light'); // При кликах
WebApp.HapticFeedback.notificationOccurred('success'); // При успехе
```

### Theme Integration
```javascript
// Использование цветов Telegram
const theme = WebApp.themeParams;
// bg_color, text_color, hint_color, button_color, etc.
```

---

## 🧪 Тестирование

### Unit Tests
- Jest + React Testing Library для frontend
- pytest для backend

### E2E Tests
- Playwright для критических пользовательских сценариев

### Manual Testing Checklist
- [ ] Аутентификация работает корректно
- [ ] Заказы отображаются и фильтруются
- [ ] Статус обновляется в real-time
- [ ] WebSocket переподключается при разрыве
- [ ] Мобильная версия адаптивна
- [ ] Telegram Mini App открывается корректно

---

## 📊 Метрики успеха

### Performance
- First Contentful Paint < 1.5s
- Time to Interactive < 3s
- WebSocket latency < 100ms
- API response time p95 < 500ms

### UX
- Task completion rate > 90%
- Average session duration > 10 min
- User satisfaction score > 4.5/5

---

## 🗓️ План разработки (4 спринта по 1 неделе)

### Спринт 1: Foundation
- [ ] Настройка структуры проекта
- [ ] Аутентификация (login, refresh, logout)
- [ ] Базовый layout (sidebar, header)
- [ ] Protected routes
- [ ] API client с interceptors

### Спринт 2: Orders Management
- [ ] Orders table с фильтрами и сортировкой
- [ ] Order details modal
- [ ] Status update functionality
- [ ] Pagination
- [ ] Search by customer name/phone

### Спринт 3: Consultations
- [ ] Questions list
- [ ] Chat interface
- [ ] Message history
- [ ] Quick replies templates
- [ ] Online/offline status toggle

### Спринт 4: Polish & Deploy
- [ ] Dashboard with stats
- [ ] WebSocket integration
- [ ] Error handling & loading states
- [ ] Responsive design testing
- [ ] Telegram Mini App integration
- [ ] Documentation
- [ ] Deployment

---

## 📚 Документация

### Для разработчиков
- README.md с инструкциями по запуску
- API documentation (Swagger/OpenAPI)
- Architecture diagram
- Component library (Storybook опционально)

### Для пользователей (фармацевтов)
- User guide (PDF)
- Video tutorials
- FAQ section в приложении
- Contact support button

---

## 🚀 Деплой

### Development
```bash
docker-compose -f docker-compose.traefik.dev.yml up --build
```

### Production
```bash
npm run prod:build
npm run prod:up
```

### Environment Variables
```env
# Frontend
VITE_API_URL=https://api.spravka.novamedika.com
VITE_WS_URL=wss://api.spravka.novamedika.com/ws

# Backend (уже есть в .env)
SECRET_KEY=...
ENCRYPTION_KEY=...
TELEGRAM_BOT_TOKEN=...
```

---

## 🎯 Следующие шаги

1. **Создать структуру директорий** для pharmacist модуля
2. **Реализовать аутентификацию** (LoginForm, auth hooks)
3. **Разработать Orders Table** с базовыми CRUD операциями
4. **Интегрировать WebSocket** для real-time обновлений
5. **Создать Chat Interface** для консультаций
6. **Добавить Dashboard** с графиками и статистикой
7. **Протестировать** на мобильных устройствах
8. **Интегрировать с Telegram Mini App**
9. **Написать документацию** для фармацевтов
10. **Запустить в production**

---

## 💡 Дополнительные возможности (Phase 2)

- AI-powered suggestions для ответов на вопросы
- Voice messages в чате
- Video calls с пользователями
- Analytics dashboard с predictive insights
- Multi-pharmacy support (для сетей аптек)
- Export reports to PDF/Excel
- Mobile app (React Native)
