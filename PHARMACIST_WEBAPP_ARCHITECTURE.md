# Архитектура WebApp Dashboard для фармацевтов

## 📊 Общая схема системы

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                             │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Telegram   │    │  Web Browser │    │ Mobile App   │  │
│  │     Bot      │    │  (WebApp)    │    │  (Future)    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                    │           │
└─────────┼───────────────────┼────────────────────┼──────────┘
          │                   │                    │
          │         HTTPS/WSS │                    │
          ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   GATEWAY LAYER                              │
│                                                               │
│                  ┌──────────────┐                            │
│                  │   Traefik    │                            │
│                  │   v3.6       │                            │
│                  │  (Reverse    │                            │
│                  │   Proxy)     │                            │
│                  └──────┬───────┘                            │
└─────────────────────────┼───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                 APPLICATION LAYER                            │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   FastAPI    │    │   FastAPI    │    │  WebSocket   │  │
│  │   Backend    │◄──►│   Routers    │◄──►│   Server     │  │
│  │              │    │              │    │              │  │
│  │ • Auth       │    │ • Orders     │    │ • Real-time  │  │
│  │ • Security   │    │ • Questions  │    │   Updates    │  │
│  │ • JWT        │    │ • Pharmacy   │    │ • Events     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
└─────────┼──────────────────┼────────────────────┼──────────┘
          │                  │                    │
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  SERVICE LAYER                               │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Order      │    │  Question    │    │ Notification │  │
│  │   Service    │    │   Service    │    │   Service    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
└─────────┼──────────────────┼────────────────────┼──────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA LAYER                                 │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ PostgreSQL   │    │    Redis     │    │   Celery     │  │
│  │    17        │    │   (Cache)    │    │   Worker     │  │
│  │              │    │              │    │              │  │
│  │ • Users      │    │ • Sessions   │    │ • Sync       │  │
│  │ • Orders     │    │ • Queue      │    │ • Tasks      │  │
│  │ • Questions  │    │              │    │              │  │
│  │ • Encrypted  │    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Frontend Architecture

### Component Hierarchy

```
App.jsx
├── PharmacistRoutes.jsx
│   ├── Public Routes
│   │   └── Login (/login)
│   │       └── LoginForm.jsx
│   │
│   └── Protected Routes (ProtectedRoute.jsx)
│       ├── Dashboard (/dashboard)
│       │   ├── MainLayout.jsx
│       │   │   ├── Sidebar.jsx
│       │   │   └── Content Area
│       │   │       ├── StatsCards.jsx
│       │   │       └── QuickActions.jsx
│       │
│       ├── Orders (/orders)
│       │   ├── MainLayout.jsx
│       │   └── OrdersPage.jsx
│       │       ├── OrderFilters.jsx
│       │       ├── OrdersTable.jsx
│       │       │   └── StatusBadge.jsx
│       │       └── OrderDetailsModal.jsx
│       │
│       ├── Consultations (/consultations)
│       │   ├── MainLayout.jsx
│       │   └── ConsultationsPage.jsx
│       │       ├── QuestionsList.jsx
│       │       └── ChatWindow.jsx
│       │           ├── MessageBubble.jsx
│       │           └── QuickReplies.jsx
│       │
│       └── Profile (/profile)
│           ├── MainLayout.jsx
│           └── ProfilePage.jsx
```

### Data Flow

```
User Action
    │
    ▼
React Component (UI)
    │
    ▼
Custom Hook (useAuth, useOrders, useQuestions)
    │
    ▼
Service Layer (authService, ordersService, questionsService)
    │
    ▼
API Client (axios with interceptors)
    │
    ▼
Backend API (FastAPI)
    │
    ▼
Database (PostgreSQL) / Cache (Redis)
    │
    ▼
Response flows back through the layers
    │
    ▼
State Update → UI Re-render
```

### State Management Strategy

```
┌─────────────────────────────────────────┐
│         Local Component State           │
│  (useState for UI-specific state)       │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│        Custom Hooks Layer               │
│  (useAuth, useOrders, useQuestions)     │
│  - Business logic                       │
│  - API calls                            │
│  - WebSocket subscriptions              │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│        Service Layer                    │
│  (authService, ordersService, etc.)     │
│  - API communication                    │
│  - Data transformation                  │
│  - Error handling                       │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│        External APIs                    │
│  - FastAPI Backend                      │
│  - WebSocket Server                     │
└─────────────────────────────────────────┘
```

---

## 🔌 API Endpoints Map

### Authentication
```
POST   /api/pharmacist/login/
POST   /api/pharmacist/refresh/
POST   /api/pharmacist/logout/
GET    /api/pharmacist/profile
PUT    /api/pharmacist/online
PUT    /api/pharmacist/offline
GET    /api/pharmacist/status
```

### Orders
```
GET    /api/pharmacist/orders
GET    /api/pharmacist/orders/{order_id}
PUT    /api/pharmacist/orders/{order_id}/status
GET    /api/pharmacist/orders/stats
```

### Questions
```
GET    /api/pharmacist/questions
GET    /api/pharmacist/questions/{question_id}
POST   /api/pharmacist/questions/{question_id}/answer
PUT    /api/pharmacist/questions/{question_id}/complete
POST   /api/pharmacist/questions/{question_id}/assign
GET    /api/pharmacist/questions/unread-count
```

### WebSocket Events
```
Client → Server:
  - subscribe_to_pharmacy

Server → Client:
  - new_order
  - order_status_updated
  - new_question
  - question_answered
```

---

## 🔐 Security Flow

### Authentication Flow

```
1. User enters credentials
         │
         ▼
2. POST /api/pharmacist/login/
         │
         ▼
3. Backend validates credentials
         │
         ▼
4. Returns access_token + refresh_token
         │
         ▼
5. Frontend stores tokens in localStorage
         │
         ▼
6. All subsequent requests include:
   Authorization: Bearer <access_token>
         │
         ▼
7. If token expires (30 min):
   - Auto-refresh using refresh_token
   - If refresh fails → logout
```

### Authorization Flow

```
Request to protected endpoint
         │
         ▼
Check JWT token validity
         │
         ├─ Invalid → 401 Unauthorized
         │
         └─ Valid
              │
              ▼
         Check pharmacist role
              │
              ├─ No role → 403 Forbidden
              │
              └─ Has role
                   │
                   ▼
              Process request
```

---

## 📱 Responsive Design Breakpoints

```
Mobile First Approach:

Base (Mobile):     0 - 639px    (default styles)
Small (sm):        640px+       (sm:)
Medium (md):       768px+       (md:)
Large (lg):       1024px+       (lg:)
Extra Large (xl): 1280px+       (xl:)
```

### Layout Changes

```
Mobile (< 1024px):
┌──────────────────┐
│  Top Bar (fixed) │
├──────────────────┤
│                  │
│   Content Area   │
│                  │
└──────────────────┘
(Sidebar hidden, accessible via hamburger menu)

Desktop (≥ 1024px):
┌────────┬─────────────────┐
│Sidebar │                 │
│(fixed) │  Content Area   │
│        │                 │
└────────┴─────────────────┘
```

---

## ⚡ Performance Optimizations

### Code Splitting
```javascript
// Lazy load routes
const Dashboard = lazy(() => import('../pages/Dashboard'));
const Orders = lazy(() => import('../pages/Orders'));
const Consultations = lazy(() => import('../pages/Consultations'));
```

### Memoization
```javascript
// Memoize expensive components
const OrdersTable = React.memo(({ orders }) => {
  // ...
});

// Memoize callbacks
const handleSubmit = useCallback((data) => {
  // ...
}, [dependencies]);
```

### Virtual Scrolling (for large lists)
```javascript
// Use react-window for long lists
import { FixedSizeList } from 'react-window';
```

### Image Optimization
```javascript
// Lazy load images
<img loading="lazy" src={photoUrl} alt="..." />
```

---

## 🧪 Testing Strategy

### Unit Tests
- Services (authService, ordersService, questionsService)
- Custom hooks (useAuth, useOrders, useQuestions)
- Utility functions

### Component Tests
- LoginForm
- OrdersTable
- ChatWindow
- Sidebar

### Integration Tests
- Login flow
- Order status update
- Question answering

### E2E Tests (Playwright)
- Complete user journeys
- WebSocket real-time updates
- Mobile responsiveness

---

## 📊 Monitoring & Analytics

### Frontend Metrics
- Page load time
- Time to Interactive (TTI)
- First Contentful Paint (FCP)
- WebSocket connection status
- API response times

### Backend Metrics
- Request rate
- Error rate
- Database query performance
- WebSocket active connections

### Logging
```javascript
// Structured logging
logger.info('Order updated', {
  orderId: 'uuid',
  status: 'confirmed',
  pharmacistId: 'uuid',
  timestamp: Date.now(),
});
```

---

## 🔄 Deployment Pipeline

```
Development
    │
    ▼
Git Push → CI/CD Pipeline
    │
    ├─→ Run Tests
    │
    ├─→ Build Docker Images
    │
    ├─→ Security Scan (OWASP ZAP)
    │
    └─→ Deploy to Staging
            │
            ▼
        Manual Testing
            │
            ▼
        Deploy to Production
            │
            ▼
        Health Checks
            │
            ▼
        Monitor & Alert
```

---

## 🎯 Key Design Decisions

### 1. Why Custom Hooks instead of Redux?
- Simpler state management
- Better TypeScript support
- Easier to test
- Less boilerplate code

### 2. Why localStorage for tokens?
- Persistent across sessions
- No CSRF vulnerability (unlike cookies)
- Easy to clear on logout
- **Trade-off**: Vulnerable to XSS (mitigated by CSP headers)

### 3. Why WebSocket over polling?
- Real-time updates
- Lower latency
- Reduced server load
- Better user experience

### 4. Why Tailwind CSS?
- Rapid development
- Consistent design system
- Small bundle size (purge unused)
- Easy customization

### 5. Why not use a UI library?
- Full control over design
- Smaller bundle size
- Custom branding requirements
- Learning opportunity

---

## 📈 Scalability Considerations

### Horizontal Scaling
- Stateless backend (JWT auth)
- Redis for session storage
- Load balancer (Traefik)
- Multiple backend instances

### Vertical Scaling
- Database connection pooling
- Query optimization
- Caching strategies
- CDN for static assets

### Future Enhancements
- Microservices architecture
- GraphQL API
- Service workers (PWA)
- Edge computing (Cloudflare Workers)
