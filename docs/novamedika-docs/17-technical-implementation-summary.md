# ТЕХНИЧЕСКАЯ РЕАЛИЗАЦИЯ COOKIE POLICY И ТРАНСГРАНИЧНОЙ ПЕРЕДАЧИ

**Дата:** 20 мая 2026 г.  
**Статус:** ✅ ВЫПОЛНЕНО  
**Версия:** 1.0

---

## 📋 ВЫПОЛНЕННЫЕ РАБОТЫ

### 1. Миграция базы данных ✅

**Файл:** [backend/alembic/versions/85d18caad27f_add_transboundary_transfer_consent_.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\alembic\versions\85d18caad27f_add_transboundary_transfer_consent_.py)

**Добавленные поля в таблицу `qa_users`:**

```python
consent_transboundary_transfer = Column(Boolean, default=False, nullable=False)
# Согласие на трансграничную передачу ПД через Telegram (UK/UAE)

consent_transboundary_transfer_date = Column(DateTime, nullable=True)
# Дата и время предоставления согласия

transboundary_risks_acknowledged = Column(Boolean, default=False, nullable=False)
# Подтверждение ознакомления с рисками трансграничной передачи
```

**Комментарии к полям:**
- Все поля имеют подробные комментарии для документации БД
- Поля nullable=False с server_default='false' для безопасности
- DateTime поле nullable=True (заполняется только при предоставлении согласия)

---

### 2. Обновление модели User ✅

**Файл:** [backend/src/db/qa_models.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\qa_models.py)

**Изменения:**
- Добавлены 3 новых поля в модель `User`
- Поля синхронизированы с миграцией
- Готовы к использованию в коде

---

### 3. Обновление Telegram Bot - команда /start ✅

**Файл:** [backend/src/bot/handlers/common_handlers/commands.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\commands.py)

**Реализован двухэтапный flow согласий:**

#### Этап 1: Запрос общего согласия на обработку ПД

При первом использовании бота (`/start`) пользователь видит:

```
👋 Добро пожаловать в NovoMedika!

⚠️ Важная информация о защите данных:

🔒 Обработка персональных данных:
• Telegram ID (шифруется в базе данных)
• Имя и фамилия (из профиля Telegram)
• Текст ваших вопросов фармацевту
• История консультаций

🌍 Трансграничная передача данных:
Этот бот работает на платформе Telegram. Серверы Telegram расположены 
за пределами Республики Беларусь (Великобритания, ОАЭ).

При использовании бота ваши данные передаются через инфраструктуру Telegram:
• Telegram ID
• Ваше имя и фамилия
• Тексты сообщений
• Номер телефона (если вы его предоставите)

⚠️ Риски:
• Данные могут быть доступны иностранным государственным органам
• Отсутствие механизмов защиты по законодательству РБ за пределами страны

✅ Меры защиты:
• Ваши Telegram ID и телефон шифруются в нашей базе данных (AES-256)
• Мы минимизируем объем передаваемых данных
• Срок хранения: 1 год после последнего обращения
• Соответствие требованиям ОАЦ РБ (класс ИС 3-ин)

🔄 Альтернативные каналы связи:
Если вы не согласны с трансграничной передачей, используйте:
• Web-сайт: https://spravka.novamedika.com (только РБ)
• Email: support@novamedika.com

📖 Подробная информация:
Политика конфиденциальности
Политика cookie

Нажимая кнопку «✅ Согласен», вы подтверждаете, что:
1. Ознакомились с Политикой конфиденциальности
2. Даете согласие на обработку персональных данных
3. Понимаете риски трансграничной передачи через Telegram
```

**Кнопки:**
- ✅ Согласен → Переход к этапу 2
- ❌ Не согласен → Отказ в использовании сервиса
- 🌐 Использовать web-сайт вместо бота → Ссылка на spravka.novamedika.com

---

#### Этап 2: Запрос согласия на трансграничную передачу

Если пользователь дал общее согласие, но не дал согласие на трансграничную передачу:

```
⚠️ Подтверждение трансграничной передачи данных

Вы уже дали согласие на обработку персональных данных.

Для продолжения использования Telegram-бота необходимо подтвердить 
согласие на трансграничную передачу данных через серверы Telegram 
(Великобритания, ОАЭ).

📋 Вы подтверждаете, что:
1. Ознакомлены с рисками передачи данных через Telegram
2. Добровольно соглашаетесь на такую передачу
3. Понимаете, что можете использовать web-сайт вместо бота

🔄 Альтернатива:
Используйте web-сайт spravka.novamedika.com для обработки данных 
исключительно на территории РБ.

Нажмите «✅ Подтверждаю» для продолжения использования бота.
```

**Кнопки:**
- ✅ Подтверждаю → Сохранение согласия в БД, доступ к функциям бота
- ❌ Отказаться → Информация об альтернативных каналах
- 🌐 Перейти на web-сайт → Ссылка на spravka.novamedika.com

---

### 4. Callback Handlers для обработки согласий ✅

**Файл:** [backend/src/bot/handlers/common_handlers/callbacks.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\callbacks.py)

**Добавленные handlers:**

#### 4.1. `consent_transboundary_transfer_callback`

Обработка согласия на трансграничную передачу:

```python
user.consent_transboundary_transfer = True
user.transboundary_risks_acknowledged = True
user.consent_transboundary_transfer_date = get_utc_now_naive()
await db.commit()
```

**Логирование:**
- Успешное сохранение согласия
- Ошибки при сохранении (с отправкой alert пользователю)

---

#### 4.2. `decline_transboundary_transfer_callback`

Обработка отказа от трансграничной передачи:

```
❌ Согласие на трансграничную передачу не получено

Без согласия на трансграничную передачу данных использование Telegram-бота невозможно.

🔄 Альтернативные каналы связи:
Вы можете использовать следующие каналы, обработка данных через которые 
осуществляется исключительно на территории Республики Беларусь:

🌐 Web-сайт: https://spravka.novamedika.com
📧 Email: support@novamedika.com
📱 Телефон: +375 (XX) XXX-XX-XX

Если вы передумаете, нажмите /start повторно и дайте согласие.
```

---

### 5. API Endpoints для управления согласиями ✅

**Файл:** [backend/src/routers/privacy.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\routers\privacy.py)

**Добавленные Pydantic модели:**

```python
class ConsentUpdateRequest(BaseModel):
    """Запрос на обновление согласий"""
    consent_privacy_policy: Optional[bool] = None
    consent_transboundary_transfer: Optional[bool] = None

class ConsentStatusResponse(BaseModel):
    """Статус согласий пользователя"""
    user_id: str
    consent_privacy_policy: bool
    consent_privacy_policy_date: Optional[str] = None
    consent_transboundary_transfer: bool
    consent_transboundary_transfer_date: Optional[str] = None
    transboundary_risks_acknowledged: bool
    updated_at: str

class CookieDataResponse(BaseModel):
    """Данные cookie и локального хранилища пользователя"""
    user_id: str
    consents: dict
    preferences: Optional[dict] = None
    exported_at: str
```

---

#### 5.1. GET `/api/privacy/cookie-data`

**Назначение:** Получение данных cookie и локального хранилища пользователя

**Ответ:**
```json
{
  "user_id": "uuid",
  "consents": {
    "privacy_policy": {
      "given": true,
      "date": "2026-05-20T07:30:00"
    },
    "transboundary_transfer": {
      "given": true,
      "date": "2026-05-20T07:30:00",
      "risks_acknowledged": true
    }
  },
  "preferences": {
    "user_type": "customer",
    "created_at": "2026-05-20T07:00:00"
  },
  "exported_at": "2026-05-20T07:30:00"
}
```

**Требования:**
- Авторизация (JWT токен)
- Возвращает все согласия пользователя
- Включает даты предоставления согласий

---

#### 5.2. PUT `/api/privacy/update-consents`

**Назначение:** Обновление согласий на обработку персональных данных

**Запрос:**
```json
{
  "consent_privacy_policy": true,
  "consent_transboundary_transfer": true
}
```

**Ответ:**
```json
{
  "user_id": "uuid",
  "consent_privacy_policy": true,
  "consent_privacy_policy_date": "2026-05-20T07:30:00",
  "consent_transboundary_transfer": true,
  "consent_transboundary_transfer_date": "2026-05-20T07:30:00",
  "transboundary_risks_acknowledged": true,
  "updated_at": "2026-05-20T07:30:00"
}
```

**Логика:**
- Если `consent_privacy_policy = true` → устанавливается дата
- Если `consent_privacy_policy = false` → дата очищается
- Если `consent_transboundary_transfer = true` → устанавливается дата и `risks_acknowledged = true`
- Если `consent_transboundary_transfer = false` → дата очищается и `risks_acknowledged = false`

**Логирование:**
- Запись об изменении согласий с UUID пользователя

---

#### 5.3. POST `/api/privacy/revoke-all-consents`

**Назначение:** Отзыв всех согласий на обработку персональных данных

**Ответ:**
```json
{
  "success": true,
  "message": "All consents have been revoked. You will need to provide consent again to use the service.",
  "revoked_at": "2026-05-20T07:30:00"
}
```

**Логика:**
- Очищает ВСЕ согласия
- Очищает ВСЕ даты
- Устанавливает `transboundary_risks_acknowledged = false`
- Пользователь не сможет использовать сервис до повторного согласия

**Логирование:**
- WARNING уровень логирования для аудита безопасности

---

### 6. Существующие endpoints (уже реализованы)

**GET `/api/privacy/export-data`** ✅ Уже есть
- Экспорт всех данных пользователя в JSON формате
- Включает вопросы, ответы, заказы, профиль

**GET `/api/privacy/my-data`** ✅ Уже есть
- Получение копии персональных данных
- Читаемый формат для пользователя

**PUT `/api/privacy/profile`** ✅ Уже есть
- Изменение персональных данных (ФИ, телефон, username)

**DELETE `/api/privacy/delete-account`** ✅ Уже есть
- Удаление аккаунта (анонимизация данных)

---

## 📊 СВОДКА ИЗМЕНЕНИЙ

### Backend изменения:

| Файл | Тип изменения | Строк добавлено | Строк изменено |
|------|---------------|-----------------|----------------|
| `alembic/versions/85d18caad27f_*.py` | Новая миграция | 25 | 0 |
| `db/qa_models.py` | Модель User | 9 | 0 |
| `bot/handlers/common_handlers/commands.py` | Handler /start | 85 | 35 |
| `bot/handlers/common_handlers/callbacks.py` | Callback handlers | 55 | 0 |
| `routers/privacy.py` | API endpoints | 140 | 15 |
| **ИТОГО** | | **314** | **50** |

---

## ✅ CHECKLIST ГОТОВНОСТИ BACKEND

### База данных:
- [x] Миграция создана
- [ ] Миграция применена локально
- [ ] Миграция применена на production

### Telegram Bot:
- [x] Команда /start обновлена
- [x] Callback handlers добавлены
- [x] Логирование настроено
- [ ] Тестирование flow согласий

### API Endpoints:
- [x] GET /api/privacy/cookie-data создан
- [x] PUT /api/privacy/update-consents создан
- [x] POST /api/privacy/revoke-all-consents создан
- [x] Pydantic модели определены
- [ ] Swagger документация проверена
- [ ] Тесты написаны

### Безопасность:
- [x] Все endpoints требуют авторизации
- [x] Логирование изменений согласий
- [x] Audit trail для отзыва согласий
- [ ] Rate limiting настроен

---

## 🧪 ТЕСТИРОВАНИЕ

### Локальное тестирование:

```bash
# 1. Применить миграцию
cd backend
uv run alembic upgrade head

# 2. Проверить структуру таблицы
docker exec -it backend-prod psql -U postgres -d novamedika -c "\d qa_users"

# 3. Запустить backend
uv run uvicorn src.main:app --reload

# 4. Запустить бота
uv run python -m bot.core
```

### Тестовые сценарии:

#### Сценарий 1: Новый пользователь
1. Отправить `/start` новому пользователю
2. Проверить появление запроса общего согласия
3. Нажать "✅ Согласен"
4. Проверить появление запроса трансграничного согласия
5. Нажать "✅ Подтверждаю"
6. Проверить появление главного меню
7. Проверить БД: все 3 поля = true

#### Сценарий 2: Отказ от трансграничной передачи
1. Отправить `/start`
2. Дать общее согласие
3. Нажать "❌ Отказаться" на этапе трансграничной передачи
4. Проверить сообщение об альтернативах
5. Проверить БД: `consent_privacy_policy = true`, остальные = false

#### Сценарий 3: API endpoint cookie-data
```bash
curl -X GET http://localhost:8000/api/privacy/cookie-data \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

#### Сценарий 4: API endpoint update-consents
```bash
curl -X PUT http://localhost:8000/api/privacy/update-consents \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"consent_transboundary_transfer": false}'
```

#### Сценарий 5: API endpoint revoke-all-consents
```bash
curl -X POST http://localhost:8000/api/privacy/revoke-all-consents \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

---

## 📝 СЛЕДУЮЩИЕ ШАГИ

### Приоритет 1 (немедленно):
1. Применить миграцию на local database
2. Протестировать flow согласий в Telegram боте
3. Проверить работу API endpoints через Swagger UI

### Приоритет 2 (1-2 дня):
4. Написать unit tests для новых endpoints
5. Добавить интеграционные тесты для callback handlers
6. Проверить логирование в Grafana/Loki

### Приоритет 3 (перед деплоем):
7. Применить миграцию на staging
8. Протестировать на staging environment
9. Применить миграцию на production
10. Мониторить логи после деплоя

---

## 🔗 СВЯЗАННЫЕ ДОКУМЕНТЫ

- [Cookie Policy](../oac/docs/05-cookie-policy.md)
- [Privacy Policy](../oac/docs/04-privacy-policy.md)
- [Анализ трансграничной передачи](../oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md)
- [Инструкция по внедрению](../oac/docs/IMPLEMENTATION-GUIDE-PRIVACY-COOKIE-POLICIES.md)

---

**Статус:** ✅ Backend реализация завершена  
**Требуется:** Тестирование и деплой  
**Автор:** AI-ассистент  
**Дата создания:** 20 мая 2026 г.
