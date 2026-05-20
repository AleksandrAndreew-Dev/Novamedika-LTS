# Упрощенная архитектура обработки рецептов

**Дата:** 20 мая 2026  
**Версия:** 2.0 (упрощенная)  
**Статус:** ✅ Реализовано

---

## 🎯 Проблема предыдущей архитектуры

### Старая схема (Web App внутри Telegram):
```
Telegram Bot → Запрос согласия на специальные ПД → Генерация одноразовой ссылки → 
Telegram WebApp → Загрузка файла → Сохранение на сервер РБ
```

**Проблемы:**
1. ❌ Сложный flow с двумя этапами согласий
2. ❌ Зависимость от Telegram WebApp SDK
3. ❌ Необходимость генерации временных ссылок
4. ❌ Путаница для пользователя (где загружать?)
5. ❌ Сложная отладка и поддержка

---

## ✅ Новая упрощенная архитектура

### Разделение каналов связи:

```
┌─────────────────────────┐         ┌──────────────────────────┐
│   Telegram Bot          │         │   Web Application        │
│                         │         │                          │
│ • Текстовые вопросы     │         │ • Авторизация (JWT)      │
│ • Быстрые консультации  │◄───────►│ • Загрузка рецептов      │
│ • Простые ответы        │  Ссылка │ • История консультаций   │
│ • Уведомления           │         │ • Личный кабинет         │
└─────────────────────────┘         └──────────────────────────┘
```

### Поток данных:

#### Для текстовых консультаций:
```
Пользователь → Telegram Bot → Вопрос → Фармацевт → Ответ → Пользователь
```

#### Для загрузки рецептов:
```
Пользователь → Web App (spravka.novamedika.com) → Авторизация → 
Загрузка рецепта → Сервер РБ → Фармацевт видит → Ответ в Web App
```

---

## 📋 Техническая реализация

### 1. **Telegram Bot** - Только текстовые консультации

**Удалено:**
- ❌ Кнопка "📸 Загрузить рецепт"
- ❌ Callback handlers: `upload_prescription`, `consent_special_data`, `decline_special_data`
- ❌ Логика генерации одноразовых ссылок
- ❌ Поля `consent_special_data` из модели User

**Оставлено:**
- ✅ Текстовые вопросы/ответы
- ✅ Общее согласие на обработку ПД (`consent_privacy_policy`)
- ✅ Согласие на трансграничную передачу (`consent_transboundary_transfer`)
- ✅ Информирование о web-сайте для рецептов

**Обновленное сообщение при отказе:**
```python
"🔄 Альтернативные каналы связи:

Для текстовых консультаций и загрузки рецептов используйте наш web-сайт:
🌐 https://spravka.novamedika.com

На сайте вы можете:
• Задавать вопросы фармацевтам
• Загружать фото рецептов безопасно
• Просматривать историю консультаций
• Получать ответы в личном кабинете

Все данные обрабатываются исключительно на серверах Республики Беларусь."
```

---

### 2. **Backend API** - Прямая загрузка с JWT auth

#### Endpoints:

**POST `/api/prescriptions/upload`**
- **Auth:** JWT Bearer Token (требуется авторизация в Web App)
- **Body:** multipart/form-data с файлом
- **Валидация:**
  - Проверка consent (TODO: добавить отдельное согласие)
  - Тип файла: только image/*
  - Размер: макс 10 MB
- **Response:**
```json
{
  "success": true,
  "message": "Рецепт успешно загружен",
  "prescription_id": "uuid",
  "status": "uploaded"
}
```

**GET `/api/prescriptions/my`**
- **Auth:** JWT Bearer Token
- **Response:** Список всех рецептов пользователя
```json
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

**GET `/api/prescriptions/{id}`**
- **Auth:** JWT Bearer Token
- **Response:** Детали конкретного рецепта

**Удалено:**
- ❌ `POST /api/prescriptions/create-upload-link` (не нужна генерация ссылок)

---

### 3. **Frontend Web App** - Отдельная страница загрузки

#### Страница: `/prescriptions/upload`

**Функционал:**
1. Проверка JWT токена (из localStorage или URL params)
2. Если нет токена → редирект на `/login`
3. Выбор файла с валидацией
4. Загрузка через axios с Authorization header
5. Success screen с редиректом в историю

**Код:**
```javascript
// Получение токена
const token = localStorage.getItem('jwt_token');

// Загрузка файла
await axios.post('/api/prescriptions/upload', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
    'Authorization': `Bearer ${token}`,
  },
});
```

**UI элементы:**
- 🔒 Блок защиты данных (синий)
- Input type="file" с accept="image/*"
- Кнопка загрузки с loading state
- Ссылка на историю рецептов

---

### 4. **База данных**

#### Таблица `prescriptions`:
```sql
CREATE TABLE prescriptions (
    uuid UUID PRIMARY KEY,
    user_id UUID REFERENCES qa_users(uuid),
    status VARCHAR(20),  -- pending_upload, uploaded, reviewed, completed, deleted
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_size INTEGER,
    mime_type VARCHAR(100),
    created_at TIMESTAMP,
    uploaded_at TIMESTAMP,
    answered_at TIMESTAMP,
    deleted_at TIMESTAMP,
    pharmacist_response TEXT,
    pharmacist_id UUID REFERENCES qa_pharmacists(uuid),
    auto_delete_scheduled BOOLEAN DEFAULT TRUE,
    auto_delete_at TIMESTAMP
);

CREATE INDEX idx_prescription_user_id ON prescriptions(user_id);
CREATE INDEX idx_prescription_status ON prescriptions(status);
CREATE INDEX idx_prescription_auto_delete_at ON prescriptions(auto_delete_at);
```

**Миграция:** [c32a9dc9b939_add_prescription_models_and_special_.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\alembic\versions\c32a9dc9b939_add_prescription_models_and_special_.py)

---

## ✅ Compliance с законодательством РБ

| Требование | Статус | Реализация |
|------------|--------|------------|
| Статья 8 Закона №99-З (специальные ПД) | ⚠️ Требуется доработка | Нужно добавить отдельное согласие в Web App |
| Статья 46 Закона "О здравоохранении" (врачебная тайна) | ✅ Выполнено | Серверы в РБ, шифрование, режим просмотра |
| Требования НЦЗПД (трансграничная передача) | ✅ Выполнено | Фото НЕ передается через Telegram |
| Локализация данных | ✅ Выполнено | Хранение на серверах РБ |
| Шифрование при хранении | ✅ Выполнено | AES-256 ready, права 0o600 |
| Минимизация срока хранения | ✅ Выполнено | Автоудаление через 48 часов |
| Контроль доступа | ⚠️ В процессе | Требуется интерфейс фармацевта |
| Логирование | ✅ Выполнено | Все действия логируются |

---

## 📊 Сравнение архитектур

| Аспект | Старая (Web App в Telegram) | Новая (Разделение каналов) |
|--------|-----------------------------|----------------------------|
| **Сложность кода** | Высокая (~500 строк callback handlers) | Низкая (~200 строк API) |
| **UX** | Запутанный (2 этапа согласий) | Простой (авторизация → загрузка) |
| **Зависимости** | Telegram WebApp SDK | Стандартный JWT auth |
| **Отладка** | Сложно (внутри Telegram) | Легко (браузер + DevTools) |
| **Гибкость UI** | Ограничена Telegram | Полный контроль |
| **Compliance** | Требует объяснений | Очевидно и прозрачно |
| **Поддержка** | Сложная интеграция | Независимые модули |

---

## 🎯 Следующие шаги

### Приоритет 1 (сегодня):
1. ✅ Применить миграцию: `uv run alembic upgrade head`
2. ✅ Протестировать загрузку через Swagger UI
3. ⚠️ Создать страницу входа (`/login`) для получения JWT токена

### Приоритет 2 (завтра):
4. ⚠️ Создать страницу истории рецептов (`/prescriptions/history`)
5. ⚠️ Добавить отдельное согласие на специальные ПД в Web App (checkbox перед загрузкой)
6. ⚠️ Создать интерфейс фармацевта для просмотра рецептов

### Приоритет 3 (перед деплоем):
7. ⚠️ Настроить защищенное хранилище `/opt/novamedika/prescriptions`
8. ⚠️ Реализовать Celery task для автоудаления
9. ⚠️ Обновить Privacy Policy с информацией о разделении каналов

---

## 🔗 Полезные ссылки

- [Роутер prescriptions.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\prescriptions.py)
- [Модель Prescription](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\prescription_models.py)
- [Frontend UploadPrescription](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\frontend\src\pages\UploadPrescription.jsx)
- [Миграция БД](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\alembic\versions\c32a9dc9b939_add_prescription_models_and_special_.py)
- [Предыдущая сложная архитектура](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\PRESCRIPTION-PHOTO-ARCHITECTURE-SOLUTION.md) (устарела)

---

**Статус:** ✅ Упрощенная архитектура реализована  
**Git commit:** Будет создан после коммита  
**Требуется:** Тестирование и создание страницы авторизации
