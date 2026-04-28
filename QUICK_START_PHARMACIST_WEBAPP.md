# 🚀 Quick Start Guide - WebApp Dashboard для фармацевтов

## Быстрый старт за 5 минут

### Шаг 1: Установка зависимостей

```bash
cd frontend
npm install
```

### Шаг 2: Настройка окружения

Создайте файл `frontend/.env`:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/pharmacist

# Mode
NODE_ENV=development
```

### Шаг 3: Запуск backend (если еще не запущен)

```bash
# В отдельном терминале
cd backend
docker-compose -f docker-compose.traefik.dev.yml up --build
```

Проверьте, что backend доступен:
```bash
curl http://localhost:8000/health
```

### Шаг 4: Запуск WebApp

```bash
cd frontend
npm run dev
```

Приложение откроется по адресу: **http://localhost:5173**

### Шаг 5: Вход в систему

1. Откройте http://localhost:5173
2. Введите ваши credentials:
   - **Telegram ID**: Ваш Telegram ID (число)
   - **Пароль**: Ваш пароль
3. Нажмите "Войти"

> ⚠️ **Примечание:** Если у вас нет учетных данных, обратитесь к администратору системы

---

## 🧪 Тестирование функционала

### Проверка аутентификации
```javascript
// Откройте консоль браузера (F12)
localStorage.getItem('pharmacist_access_token') // Должен вернуть токен
```

### Проверка WebSocket подключения
```javascript
// В консоли разработчика должно быть:
// [INFO] WebSocket connected
```

### Проверка API calls
```javascript
// Network tab в DevTools должен показывать запросы к:
// - /api/pharmacist/profile
// - /api/pharmacist/orders
// - /api/pharmacist/questions/unread-count
```

---

## 📱 Mobile Testing

### Chrome DevTools Mobile Emulation

1. Откройте DevTools (F12)
2. Нажмите Ctrl+Shift+M (или Cmd+Shift+M на Mac)
3. Выберите устройство (iPhone 12, Samsung Galaxy S20, etc.)
4. Проверьте адаптивность интерфейса

### Key breakpoints to test:
- **320px** - Small mobile
- **375px** - iPhone SE
- **414px** - iPhone XR
- **768px** - iPad (tablet)
- **1024px** - Desktop

---

## 🔍 Troubleshooting

### Проблема: "Cannot connect to API"

**Решение:**
```bash
# 1. Проверьте, что backend запущен
docker ps | grep backend

# 2. Проверьте .env файл
cat frontend/.env

# 3. Проверьте CORS настройки в backend
# Файл: backend/src/main.py
# Должно быть: CORS_ORIGINS=["http://localhost:5173"]
```

### Проблема: WebSocket не подключается

**Решение:**
```bash
# 1. Проверьте URL в .env
VITE_WS_URL=ws://localhost:8000/ws/pharmacist

# 2. Проверьте логи backend
docker logs backend-prod | grep websocket

# 3. Попробуйте перезагрузить страницу (F5)
```

### Проблема: "Token expired"

**Решение:**
```javascript
// Token автоматически обновляется через useAuth hook
// Если не работает, проверьте:

// 1. Refresh token в localStorage
localStorage.getItem('pharmacist_refresh_token')

// 2. Логи в консоли
// Должно быть: [INFO] Token refreshed successfully

// 3. Если refresh token истек - войдите заново
```

### Проблема: Стили не загружаются

**Решение:**
```bash
# 1. Пересоберите проект
npm run build

# 2. Очистите кэш
rm -rf node_modules/.vite

# 3. Переустановите зависимости
npm install

# 4. Запустите заново
npm run dev
```

---

## 🛠️ Development Tips

### Hot Reload

Изменения в коде автоматически обновляются в браузере благодаря Vite HMR (Hot Module Replacement).

### React DevTools

Установите расширение для браузера:
- [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)

Позволяет inspect React components и state.

### API Testing с Thunder Client

Установите VS Code расширение **Thunder Client** для тестирования API endpoints без Postman.

### Debugging

```javascript
// Добавьте logger в любом месте кода
import { logger } from '../../utils/logger';

logger.info('Debug info', { data: someVariable });
logger.error('Error occurred', error);
```

Логи отображаются в консоли браузера с цветовой кодировкой.

---

## 📊 Monitoring

### Check API Health

```bash
# Backend health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "database": "connected"}
```

### Check WebSocket Status

Откройте консоль браузера и выполните:

```javascript
// Проверка статуса WebSocket
import { websocketService } from './src/pharmacist/services/websocketService';

console.log('WebSocket connected:', websocketService.isConnected());
console.log('Ready state:', websocketService.getReadyState());
```

### View Active Sessions

```bash
# Посмотреть активные сессии в Redis
docker exec redis-prod redis-cli keys "*pharmacist*"
```

---

## 🎨 Customization

### Change Theme Colors

Edit `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        'telegram-primary': '#0088cc', // Change this
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
      }
    }
  }
}
```

### Add New Route

1. Create page component: `frontend/src/pharmacist/pages/NewPage.jsx`
2. Add route in `PharmacistRoutes.jsx` (when created):
```jsx
<Route path="/new-page" element={<NewPage />} />
```
3. Add link in `Sidebar.jsx`:
```jsx
{
  name: 'New Page',
  href: '/new-page',
  icon: <YourIcon />,
}
```

---

## 📦 Building for Production

### Build Command

```bash
npm run build
```

Output will be in `frontend/dist/` directory.

### Preview Production Build

```bash
npm run preview
```

Opens production build at http://localhost:4173

### Deploy to Production

```bash
# From project root
npm run prod:build
npm run prod:up
```

WebApp будет доступен по адресу: `https://pharmacist.spravka.novamedika.com`

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Update `.env` with production URLs
- [ ] Set `NODE_ENV=production`
- [ ] Enable HTTPS (handled by Traefik)
- [ ] Configure CORS for production domain
- [ ] Set secure cookie flags
- [ ] Enable Content Security Policy headers
- [ ] Test with OWASP ZAP
- [ ] Review JWT expiration times
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerts

---

## 📞 Need Help?

### Documentation
- [Technical Spec](./PHARMACIST_WEBAPP_SPEC.md)
- [Architecture](./PHARMACIST_WEBAPP_ARCHITECTURE.md)
- [Summary](./PHARMACIST_WEBAPP_SUMMARY.md)
- [Pharmacist README](./frontend/src/pharmacist/README.md)

### Contact
- 📧 Email: dev@novamedika.com
- 📱 Telegram: @novamedika_dev_team
- 💬 Slack: #pharmacist-webapp channel

---

## ✅ Success Criteria

You know it's working when:

1. ✅ Can login with credentials
2. ✅ See dashboard with statistics
3. ✅ Sidebar navigation works
4. ✅ Online/offline toggle functions
5. ✅ No console errors
6. ✅ WebSocket shows "connected"
7. ✅ Responsive on mobile devices
8. ✅ Logout clears tokens and redirects

---

## 🎉 Congratulations!

You've successfully set up the Pharmacist WebApp Dashboard!

Next steps:
1. Implement Orders Management UI
2. Implement Consultations Chat Interface
3. Add Backend WebSocket endpoint
4. Test with real pharmacists
5. Deploy to production

Happy coding! 🚀
