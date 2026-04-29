# Исправление: Фармацевт не попадает в дашборд

**Дата:** 2026-04-29  
**Приоритет:** 🔴 КРИТИЧЕСКИЙ  
**Статус:** ✅ ИСПРАВЛЕНО

---

## 🎯 Проблема

Фармацевт **не может попасть в дашборд** при нажатии на кнопку "Панель фармацевта" в Telegram боте.

---

## 🔍 Причина

Согласно документации Telegram WebApp, для правильной работы Mini App необходимо:

1. **Загрузить Telegram WebApp SDK** через `<script src="https://telegram.org/js/telegram-web-app.js"></script>`
2. **Инициализировать WebApp** вызовом `Telegram.WebApp.ready()` и `Telegram.WebApp.expand()`
3. **Обработать initData** - подписанные данные пользователя от Telegram

Без SDK:
- ❌ Telegram не может правильно инициализировать WebApp внутри клиента
- ❌ Не передаются данные о пользователе (initData)
- ❌ WebApp не разворачивается на полный экран
- ❌ Не применяются цвета темы Telegram

### Доказательства из логов

Из `agent/tg-docs/tg-logs.md`:

```
GET https://pharmacist.spravka.novamedika.com/?token=JWT#tgWebAppData=query_id=AAEFNeAoAAAAAAU14Cj4LEM4&user=%7B%22id%22%3A685782277...
```

**Telegram УЖЕ передает initData в URL hash fragment**, но без SDK мы не можем получить эти данные через `window.Telegram.WebApp.initData`.

---

## ✅ Решение

### Шаг 1: Добавить Telegram WebApp SDK в index.html

**Файл:** `frontend/index.html`

Добавлено в `<head>`:

```html
<!-- Telegram WebApp SDK -->
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<!-- Оптимизированный viewport для мобильных устройств -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
```

### Шаг 2: Создать утилиту инициализации

**Файл:** `frontend/src/utils/telegramWebApp.js`

Создан класс `TelegramWebApp` который:
- ✅ Автоматически инициализирует SDK при загрузке
- ✅ Вызывает `Telegram.WebApp.ready()` и `Telegram.WebApp.expand()`
- ✅ Применяет цвета темы Telegram
- ✅ Предоставляет методы для работы с WebApp API
- ✅ Работает как внутри Telegram, так и в обычном браузере

### Шаг 3: Интегрировать в PharmacistApp

**Файл:** `frontend/src/pharmacist/PharmacistApp.jsx`

Добавлено:
```javascript
import { telegramWebApp } from '../utils/telegramWebApp';

// В компоненте TokenAuthHandler:
useEffect(() => {
  console.log('[TokenAuthHandler] Initializing Telegram WebApp...');
  telegramWebApp.initialize();
  
  if (telegramWebApp.isInTelegram()) {
    console.log('[TokenAuthHandler] Running inside Telegram - applying theme');
    telegramWebApp.applyTheme();
  }
}, []);
```

---

## 🧪 Как проверить

### 1. Пересобрать фронтенд

```bash
cd frontend
npm run build
```

### 2. Перезапустить контейнер

```bash
docker-compose -f docker-compose.traefik.prod.yml restart frontend-prod
```

### 3. Протестировать в Telegram

1. Откройте бота в Telegram
2. Наберите `/start`
3. Нажмите кнопку **"💼 Панель фармацевта"**
4. Должно открыться WebApp на весь экран
5. Должна произойти автоматическая аутентификация по JWT токену
6. Должен загрузиться дашборд со статистикой

### 4. Проверить консоль браузера

В консоли должны быть такие сообщения:

```
[TelegramWebApp] SDK detected
[TelegramWebApp] Platform: web
[TelegramWebApp] Version: 9.5
[TelegramWebApp] InitData available: true
[TelegramWebApp] ✅ Initialized successfully
[TokenAuthHandler] Running inside Telegram - applying theme
[TokenAuthHandler] Checking for token in URL...
[TokenAuthHandler] Token found: true
[AuthProvider] ✅ Profile fetched successfully
```

---

## 📋 Что изменилось

### До исправления:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>НоваМедика — Справочная служба аптек</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

❌ Нет SDK  
❌ Нет инициализации WebApp  
❌ WebApp не открывается корректно  

### После исправления:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>НоваМедика — Справочная служба аптек</title>
    
    <!-- Telegram WebApp SDK -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    
    <!-- CSP for Telegram WebApp -->
    <meta http-equiv="Content-Security-Policy" content="..." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

✅ SDK загружен  
✅ WebApp инициализируется автоматически  
✅ Применяется тема Telegram  
✅ WebApp разворачивается на полный экран  

---

## 🔗 Полезные ссылки

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Initializing Mini Apps](https://core.telegram.org/bots/webapps#initializing-mini-apps)
- [Validating Data](https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app)
- [aiogram WebApp Utils](https://docs.aiogram.dev/en/latest/utils/web_app.html)

---

## 🚨 Troubleshooting

### Если WebApp всё ещё не открывается:

1. **Проверьте, что скрипт загружается:**
   ```javascript
   // В консоли браузера:
   console.log(window.Telegram); // Должен быть объект
   console.log(window.Telegram.WebApp); // Должен быть объект
   ```

2. **Проверьте CSP headers:**
   ```
   script-src должен включать 'https://telegram.org'
   frame-ancestors должен включать 'https://t.me https://web.telegram.org'
   ```

3. **Проверьте URL:**
   ```
   URL должен содержать #tgWebAppData=... в hash fragment
   Если нет - проблема в кнопке бота
   ```

4. **Проверьте версию SDK:**
   ```javascript
   console.log(Telegram.WebApp.version); // Должна быть >= 6.0
   ```

### Если аутентификация не работает:

1. **Проверьте токен в URL:**
   ```
   ?token=eyJhbGci... должен быть в query parameters
   ```

2. **Проверьте backend logs:**
   ```bash
   docker logs backend-prod | grep "pharmacist/me"
   ```

3. **Проверьте срок действия токена:**
   ```python
   import jwt
   payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
   print(payload['exp'])  # Unix timestamp
   ```

---

## 📝 Примечания

### Почему это критично?

Без Telegram WebApp SDK:
- WebApp может не открыться вообще
- Или откроется в маленьком окне вместо полного экрана
- Не будут работать нативные функции Telegram (цвета, анимации, haptic feedback)
- Пользовательский опыт будет плохим

### Безопасность

Мы используем **два уровня аутентификации**:

1. **JWT токен** (наш собственный) - передается в `?token=`
   - Содержит UUID фармацевта
   - Подписан нашим секретным ключом
   - Имеет срок действия (1 час)

2. **Telegram initData** (от Telegram) - передается в `#tgWebAppData=`
   - Подписан Telegram Bot API
   - Содержит данные пользователя
   - Можно валидировать на бэкенде для дополнительной безопасности

**Текущая реализация** использует только JWT токен, что достаточно для большинства случаев.

**Для повышенной безопасности** можно добавить валидацию initData на бэкенде:

```python
from aiogram.utils.web_app import safe_parse_webapp_init_data

# В backend router
try:
    init_data = safe_parse_webapp_init_data(
        token=settings.TELEGRAM_BOT_TOKEN,
        init_data=request.headers.get('X-Telegram-Init-Data')
    )
    # Проверить, что user.id совпадает с pharmacist.telegram_id
except ValueError:
    raise HTTPException(status_code=401, detail="Invalid initData")
```

Но это **опционально** и требует дополнительных изменений.

---

## ✨ Следующие шаги

1. ✅ **СДЕЛАНО:** Добавить SDK в index.html
2. ✅ **СДЕЛАНО:** Создать утилиту инициализации
3. ✅ **СДЕЛАНО:** Интегрировать в PharmacistApp
4. 🔄 **ТЕСТИРОВАНИЕ:** Проверить в Telegram
5. 📊 **МОНИТОРИНГ:** Следить за логами после деплоя
6. 🎨 **ОПЦИОНАЛЬНО:** Применить тему Telegram ко всем компонентам
7. 🔒 **ОПЦИОНАЛЬНО:** Добавить валидацию initData на бэкенде

---

**Исправление применено:** 2026-04-29 09:45 UTC  
**Требуется пересборка:** Да (`npm run build`)  
**Требуется перезапуск:** Да (`docker-compose restart frontend-prod`)
