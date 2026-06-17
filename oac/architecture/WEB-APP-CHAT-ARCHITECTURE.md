# Web Application Architecture - Chat & Prescription System

**Дата:** 20 мая 2026  
**Версия:** 3.0 (с чатом)  
**Статус:** 🚧 В разработке

---

## 🎯 Архитектура разделения каналов

### Telegram Bot - Текстовые консультации БЕЗ фото
```
Пользователь → Telegram Bot → Текстовый вопрос → Фармацевт → Ответ
```

**Возможности:**
- ✅ Текстовые вопросы и ответы
- ✅ Быстрые консультации
- ✅ Уведомления о новых ответах
- ❌ БЕЗ загрузки фото/документов
- ❌ БЕЗ истории консультаций

**При попытке загрузить рецепт:**
```
"Для загрузки фото рецептов используйте наш web-сайт:
🌐 https://spravka.novamedika.com/prescriptions/upload"
```

---

### Web Application - Полный функционал с чатом

#### Для пользователей:
```
Авторизация (JWT) → Dashboard → Чат с фармацевтом → Загрузка рецептов → История
```

**Возможности:**
- ✅ Авторизация через email/phone + пароль
- ✅ Чат с фармацевтом (текст + фото)
- ✅ Загрузка рецептов с отдельным согласием
- ✅ Полная история консультаций
- ✅ Личный кабинет

#### Для фармацевтов:
```
Авторизация → Панель управления → Список вопросов → Ответы → Просмотр рецептов
```

**Возможности:**
- ✅ Панель управления вопросами
- ✅ Ответы пользователям в чате
- ✅ Просмотр фото рецептов (режим "глазок")
- ✅ Статистика и аналитика

---

## 📋 Backend API Structure

### Authentication Endpoints

**POST `/api/auth/login`** - Авторизация пользователя
```python
Request:
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_jwt",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Петров"
  }
}
```

**POST `/api/pharmacist/auth/login`** - Авторизация фармацевта
```python
Request:
{
  "email": "pharmacist@novamedika.com",
  "password": "secure_password"
}

Response: Same as user login + pharmacist info
```

---

### Consultation Endpoints (Web App)

**GET `/api/consultations`** - История консультаций пользователя
```python
Headers: Authorization: Bearer {jwt_token}

Response:
[
  {
    "id": "uuid",
    "text": "Вопрос пользователя",
    "status": "answered",
    "created_at": "2026-05-20T10:00:00",
    "answered_at": "2026-05-20T12:00:00",
    "pharmacist_name": "Мария Иванова",
    "message_count": 5,
    "has_prescription": true
  }
]
```

**POST `/api/consultations`** - Создать новый вопрос
```python
Headers: Authorization: Bearer {jwt_token}

Request:
{
  "text": "Описание проблемы...",
  "category": "general"
}

Response:
{
  "id": "uuid",
  "status": "pending",
  "created_at": "2026-05-20T14:00:00"
}
```

**GET `/api/consultations/{id}/messages`** - Получить сообщения чата
```python
Headers: Authorization: Bearer {jwt_token}

Response:
[
  {
    "id": "uuid",
    "message_type": "question",  // question, answer, clarification
    "sender_type": "user",       // user, pharmacist
    "text": "Текст сообщения",
    "created_at": "2026-05-20T14:05:00"
  },
  {
    "id": "uuid",
    "message_type": "answer",
    "sender_type": "pharmacist",
    "text": "Ответ фармацевта",
    "created_at": "2026-05-20T14:10:00"
  }
]
```

**POST `/api/consultations/{id}/messages`** - Отправить сообщение в чат
```python
Headers: Authorization: Bearer {jwt_token}

Request:
{
  "text": "Дополнительный вопрос...",
  "message_type": "clarification"
}

Response:
{
  "id": "uuid",
  "created_at": "2026-05-20T14:15:00"
}
```

---

### Prescription Endpoints (Web App)

**POST `/api/prescriptions/upload`** - Загрузить рецепт
```python
Headers: 
  Authorization: Bearer {jwt_token}
  Content-Type: multipart/form-data

Request: FormData with file

Validation:
- Проверка согласия на специальные ПД (checkbox в UI)
- Тип файла: image/jpeg, image/png
- Размер: макс 10 MB

Response:
{
  "success": true,
  "prescription_id": "uuid",
  "message": "Рецепт загружен. Фармацевт ответит в ближайшее время."
}
```

**GET `/api/prescriptions/my`** - Мои рецепты
```python
Headers: Authorization: Bearer {jwt_token}

Response:
[
  {
    "id": "uuid",
    "status": "uploaded",
    "file_name": "recipe.jpg",
    "created_at": "2026-05-20T10:00:00",
    "answered_at": "2026-05-20T12:00:00",
    "pharmacist_response": "Принимайте по 1 таблетке..."
  }
]
```

---

### Pharmacist Endpoints

**GET `/api/pharmacist/questions`** - Список вопросов для фармацевта
```python
Headers: Authorization: Bearer {jwt_token} (pharmacist)

Query params: status=pending|answered|completed

Response:
[
  {
    "id": "uuid",
    "user_name": "Иван Петров",
    "text": "Вопрос пользователя",
    "status": "pending",
    "created_at": "2026-05-20T14:00:00",
    "has_prescription": true,
    "message_count": 3
  }
]
```

**POST `/api/pharmacist/questions/{id}/answer`** - Ответить на вопрос
```python
Headers: Authorization: Bearer {jwt_token} (pharmacist)

Request:
{
  "text": "Ответ фармацевта..."
}

Response:
{
  "success": true,
  "answered_at": "2026-05-20T14:30:00"
}
```

**GET `/api/pharmacist/prescriptions/{id}/view`** - Просмотр рецепта (режим "глазок")
```python
Headers: Authorization: Bearer {jwt_token} (pharmacist)

Response: Image stream (не скачиваемый файл)

Security:
- Запрет правого клика (JS)
- CSS pointer-events: none
- Watermark с ID фармацевта
- Логирование просмотра
```

---

## 🎨 Frontend Structure

### User Web App Pages

**1. /login** - Страница входа
- Email/Phone input
- Password input
- "Забыли пароль?" link
- Submit button → JWT auth
- Redirect to /dashboard on success

**2. /dashboard** - Главная страница
- Приветствие пользователя
- Кнопка "Задать вопрос"
- Список последних консультаций
- Статистика (всего вопросов, ожидающих ответа)
- Навигация: Консультации | Рецепты | Профиль

**3. /chat/{consultation_id}** - Чат с фармацевтом
- История сообщений (scrollable)
- Input field для нового сообщения
- Кнопка отправки
- Индикатор "Фармацевт печатает..." (WebSocket)
- Кнопка "Загрузить рецепт" (если еще не загружен)
- Auto-refresh или WebSocket для real-time

**4. /prescriptions/upload** - Загрузка рецепта
- Checkbox: "Согласен на обработку специальных ПД"
- File input (image/*)
- Preview выбранного фото
- Upload button с progress bar
- Security info block
- Redirect to /prescriptions/history on success

**5. /prescriptions/history** - История рецептов
- Таблица/карточки рецептов
- Статус каждого рецепта
- Ответ фармацевта (если есть)
- Дата загрузки и ответа

**6. /profile** - Личный кабинет
- Информация о пользователе
- Настройки уведомлений
- Управление согласиями
- Logout button

---

### Pharmacist Web App Pages

**1. /pharmacist/login** - Вход для фармацевта
- Аналогично user login
- Separate authentication endpoint

**2. /pharmacist/dashboard** - Панель управления
- Статистика: онлайн/офлайн статус
- Количество новых вопросов
- Кнопки: Онлайн/Офлайн
- Быстрый доступ к вопросам

**3. /pharmacist/questions** - Список вопросов
- Фильтры: Новые | В работе | Завершенные
- Карточки вопросов с превью
- Priority indicators
- Click to open chat

**4. /pharmacist/chat/{question_id}** - Чат с пользователем
- История диалога
- Input для ответа
- Кнопка "Запросить фото рецепта" (отправляет ссылку пользователю)
- Кнопка "Завершить консультацию"
- Просмотр загруженных рецептов (inline preview)

**5. /pharmacist/prescription/{id}** - Просмотр рецепта
- Full-screen image viewer
- Режим "глазок" (no download, no right-click)
- Watermark с ID фармацевта и timestamp
- Кнопка "Ответить" (возврат в чат)
- Логирование просмотра

---

## 🔧 Technical Implementation

### Database Models (Already exist)

**Question** - Консультация/вопрос
```python
uuid, user_id, text, status, category,
assigned_to, answered_by, created_at, answered_at
```

**Answer** - Ответ фармацевта
```python
uuid, question_id, pharmacist_id, text, created_at
```

**DialogMessage** - Сообщения чата
```python
uuid, question_id, message_type, sender_type, 
sender_id, text, file_id, caption, created_at
```

**Prescription** - Рецепты (уже создана)
```python
uuid, user_id, status, file_path, file_name,
created_at, uploaded_at, answered_at, 
pharmacist_response, auto_delete_at
```

---

### Real-time Communication

**Option 1: WebSocket (Recommended)**
```python
# backend/src/websockets/chat.py
from fastapi import WebSocket, Depends

@app.websocket("/ws/chat/{consultation_id}")
async def websocket_chat(
    websocket: WebSocket,
    consultation_id: str,
    token: str = Query(...)
):
    await websocket.accept()
    # Authenticate with JWT
    # Join room for this consultation
    # Broadcast messages to both user and pharmacist
```

**Option 2: Polling (Simpler)**
```javascript
// frontend/src/hooks/useChatPolling.js
useEffect(() => {
  const interval = setInterval(() => {
    fetchMessages(consultationId);
  }, 5000); // Poll every 5 seconds
  
  return () => clearInterval(interval);
}, [consultationId]);
```

**Recommendation:** Start with polling (simpler), migrate to WebSocket later if needed.

---

### Security Considerations

**1. JWT Authentication**
- Access token: 15 minutes expiry
- Refresh token: 7 days expiry
- Stored in localStorage (for simplicity) or httpOnly cookies (more secure)

**2. Special Data Consent**
```javascript
// Before prescription upload
const [consentChecked, setConsentChecked] = useState(false);

<input 
  type="checkbox" 
  checked={consentChecked}
  onChange={(e) => setConsentChecked(e.target.checked)}
/>
<label>
  Я согласен на обработку специальных персональных данных 
  (сведений о здоровье) в соответствии со ст. 8 Закона №99-З
</label>

// Backend validation
if not consent_checked:
    raise HTTPException(403, "Требуется согласие на обработку специальных ПД")
```

**3. Prescription Photo Protection**
- Store in `/opt/novamedika/prescriptions` with permissions `0o600`
- Encrypt file path in database
- Auto-delete after 48 hours (Celery task)
- Pharmacist view-only mode (no download)
- Log all access attempts

**4. Audit Logging**
```python
# Log all prescription views by pharmacists
audit_log = AuditLog(
    user_id=pharmacist.user_id,
    action="view_prescription",
    resource=f"prescription:{prescription_id}",
    ip_address=request.client.host,
    created_at=datetime.utcnow()
)
db.add(audit_log)
```

---

## 📊 Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
1. ✅ Restore Question, Answer, DialogMessage models
2. ⚠️ Create authentication endpoints (/api/auth/login)
3. ⚠️ Create consultation CRUD endpoints
4. ⚠️ Create message endpoints for chat
5. ⚠️ Implement JWT authentication middleware

### Phase 2: User Web App (Week 2)
6. ⚠️ Create /login page with JWT auth
7. ⚠️ Create /dashboard with consultation list
8. ⚠️ Create /chat/{id} with message history
9. ⚠️ Implement message sending (polling)
10. ⚠️ Create /prescriptions/upload with consent checkbox
11. ⚠️ Create /prescriptions/history page

### Phase 3: Pharmacist Web App (Week 3)
12. ⚠️ Create /pharmacist/login
13. ⚠️ Create /pharmacist/dashboard
14. ⚠️ Create /pharmacist/questions list
15. ⚠️ Create /pharmacist/chat/{id} for answering
16. ⚠️ Create prescription viewer (eye-mode)
17. ⚠️ Implement audit logging

### Phase 4: Polish & Testing (Week 4)
18. ⚠️ Add loading states and error handling
19. ⚠️ Implement responsive design (mobile-first)
20. ⚠️ Add notifications (new message alerts)
21. ⚠️ Write unit tests for API endpoints
22. ⚠️ Test complete flow end-to-end
23. ⚠️ Deploy to staging environment

### Phase 5: Production Deployment
24. ⚠️ Apply database migrations
25. ⚠️ Configure production environment variables
26. ⚠️ Set up SSL certificates
27. ⚠️ Configure Celery tasks for auto-deletion
28. ⚠️ Monitor logs and metrics
29. ⚠️ Train pharmacists on new system

---

## ✅ Compliance Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Статья 8 Закона №99-З (специальные ПД) | ⚠️ Pending | Checkbox consent before upload |
| Статья 46 Закона "О здравоохранении" | ✅ Ready | Servers in RB, encryption, eye-mode |
| Требования НЦЗПД (трансграничная передача) | ✅ Compliant | Photos NOT sent via Telegram |
| Локализация данных | ✅ Ready | Storage on Belarus servers |
| Шифрование при хранении | ✅ Ready | AES-256, file permissions 0o600 |
| Минимизация срока хранения | ✅ Ready | Auto-delete after 48 hours |
| Контроль доступа | ⚠️ Pending | JWT auth + role-based access |
| Логирование | ⚠️ Pending | Audit logs for all actions |
| Режим просмотра без скачивания | ⚠️ Pending | JS protection + watermark |

---

## 🔗 Related Documents

- [Упрощенная архитектура](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\SIMPLIFIED-PRESCRIPTION-ARCHITECTURE.md)
- [Модели БД](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\qa_models.py)
- [Prescription router](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\prescriptions.py)
- [UploadPrescription page](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\frontend\src\pages\UploadPrescription.jsx)

---

**Статус:** 🚧 Проектирование завершено, начинается реализация  
**Next Step:** Создание authentication endpoints и user login page
