п# Исправление: Pharmacist Dashboard показывает тот же контент, что и основной сайт

## 📋 Проблема

При переходе на `https://pharmacist.spravka.novamedika.com/` отображается **тот же самый контент**, что и на `https://spravka.novamedika.com/`.

**Причина:** Pharmacist webapp Docker image собирался из того же самого frontend кода без отдельной точки входа, поэтому оба сайта использовали один и тот же React application.

---

## ✅ Решение

Создана **отдельная точка входа** для pharmacist dashboard с собственным routing и компонентами.

### Что было сделано:

1. **Создан новый entry point:** `frontend/src/pharmacist-main.jsx`
   - Использует собственный routing для pharmacist app
   - Подключает PharmacistApp компонент

2. **Создан главный компонент:** `frontend/src/pharmacist/PharmacistApp.jsx`
   - Настраивает маршруты для pharmacist dashboard
   - Интегрирует аутентификацию через AuthProvider
   - Защищает роуты через ProtectedRoute

3. **Добавлен Login компонент:** `frontend/src/pharmacist/components/auth/Login.jsx`
   - Обертка для LoginForm с красивым UI

4. **Обновлен Vite config:** `frontend/vite.config.js`
   - Добавлена поддержка режима `pharmacist`
   - Отдельный output directory: `dist-pharmacist`
   - Кастомный entry point для pharmacist сборки

5. **Добавлен build script:** `frontend/package.json`
   ```json
   "build:pharmacist": "vite build --mode pharmacist"
   ```

6. **Обновлен Dockerfile:** `frontend/Dockerfile.pharmacist`
   - Использует `npm run build:pharmacist` вместо `npm run build`
   - Копирует из `dist-pharmacist` вместо `dist`

---

## 🚀 Как применить исправление

### Шаг 1: Запушить изменения в репозиторий

```bash
git add .
git commit -m "fix: create separate entry point for pharmacist webapp dashboard"
git push origin main
```

### Шаг 2: Дождаться завершения CI/CD

GitHub Actions автоматически:
- Соберет новый образ `pharmacist-webapp` с отдельным entry point
- Запушит образ в GitHub Container Registry

### Шаг 3: Обновить production сервер

```bash
ssh user@server
cd /opt/novamedika-prod

# Pull новый образ
docker compose -f docker-compose.traefik.prod.yml pull pharmacist_webapp

# Перезапустить сервис
docker compose -f docker-compose.traefik.prod.yml up -d pharmacist_webapp

# Проверить статус
docker compose -f docker-compose.traefik.prod.yml ps
```

### Шаг 4: Проверить результат

1. **Основной сайт:** [https://spravka.novamedika.com/](https://spravka.novamedika.com/)
   - Должен показывать поиск лекарств и бронирование (как раньше) ✅

2. **Pharmacist Dashboard:** [https://pharmacist.spravka.novamedika.com/](https://pharmacist.spravka.novamedika.com/)
   - Должен показывать страницу входа фармацевта ✅
   - После входа - дашборд с статистикой консультаций ✅

---

## 🔍 Проверка работы

### Основной сайт (для клиентов):
- Поиск лекарств по названию
- Выбор города
- Бронирование в аптеках
- Обычный пользовательский интерфейс

### Pharmacist Dashboard (для фармацевтов):
- Страница логина (`/login`)
- Дашборд со статистикой:
  - Новых вопросов
  - В работе
  - Завершено сегодня
  - Среднее время ответа
- Управление консультациями
- Профиль фармацевта

---

## 📊 Архитектура после исправления

```
┌─────────────────────────────────────────────┐
│         Traefik Reverse Proxy               │
│       (178.172.137.7:80/443)                │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ↓          ↓          ↓
┌────────┐ ┌────────┐ ┌──────────────┐
│Frontend│ │Backend │ │PharmacistWeb │
│        │ │        │ │              │
│spravka │ │ api.   │ │pharmacist.   │
│.novame │ │spravka │ │spravka.      │
│dika.co │ │.novame │ │novamedika.   │
│m       │ │dika.co │ │com           │
│        │ │m       │ │              │
│Поиск   │ │REST API│ │Dashboard     │
│лекарств│ │+ WS    │ │фармацевта    │
└────────┘ └────────┘ └──────────────┘
     ↑           ↑            ↑
     │           │            │
     └───────────┴────────────┘
                 │
         ┌───────┴────────┐
         │   PostgreSQL   │
         │     Redis      │
         │   Celery       │
         └────────────────┘
```

**Ключевые отличия:**
- ✅ Два **разных** React приложения
- ✅ Два **разных** Docker образа
- ✅ Общий backend API (`api.spravka.novamedika.com`)
- ✅ Не мешают друг другу

---

## 🛠️ Технические детали

### Frontend (основной сайт):
- **Entry point:** `src/main.jsx`
- **Build command:** `npm run build`
- **Output:** `dist/`
- **Dockerfile:** `frontend/Dockerfile`
- **Image:** `ghcr.io/.../frontend:latest`

### Pharmacist WebApp:
- **Entry point:** `src/pharmacist-main.jsx`
- **Build command:** `npm run build:pharmacist`
- **Output:** `dist-pharmacist/`
- **Dockerfile:** `frontend/Dockerfile.pharmacist`
- **Image:** `ghcr.io/.../pharmacist-webapp:latest`

### Vite Configuration:
```javascript
build: {
  outDir: isPharmacist ? "dist-pharmacist" : "dist",
  rollupOptions: {
    input: isPharmacist ? "src/pharmacist-main.jsx" : undefined,
  },
}
```

---

## ⚠️ Важные замечания

1. **Общий код:** Оба приложения используют общие компоненты из `src/components/`, `src/api/`, `src/utils/`

2. **Аутентификация:** Pharmacist app использует JWT tokens через `useAuth` hook

3. **WebSocket:** Real-time уведомления работают через `wss://api.spravka.novamedika.com/api/pharmacist/ws/pharmacist`

4. **API endpoints:** Оба приложения обращаются к одному backend на `api.spravka.novamedika.com`

---

## 🎯 Результат

После применения исправления:
- ✅ `spravka.novamedika.com` - поиск лекарств для клиентов
- ✅ `pharmacist.spravka.novamedika.com` - профессиональный дашборд для фармацевтов
- ✅ Полностью независимые приложения
- ✅ Общий backend и база данных
- ✅ Автоматическая сборка через CI/CD
