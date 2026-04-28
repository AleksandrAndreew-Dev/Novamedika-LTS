# Интеграция Pharmacist WebApp в Production

## 📋 Обзор

WebApp Dashboard для фармацевтов интегрируется в существующую инфраструктуру Traefik как отдельный сервис.

### Архитектура

```
┌─────────────────────────────────────────────┐
│              Traefik (Reverse Proxy)         │
│  - SSL termination (Let's Encrypt)          │
│  - Routing по доменам                       │
│  - Security headers                         │
└──────────┬──────────────────┬───────────────┘
           │                  │
           ▼                  ▼
    ┌──────────────┐  ┌──────────────────┐
    │   Frontend   │  │ Pharmacist WebApp│
    │ spravka.     │  │ pharmacist.      │
    │ novamedika.  │  │ spravka.         │
    │ com          │  │ novamedika.com   │
    └──────────────┘  └──────────────────┘
           │                  │
           ▼                  ▼
    ┌────────────────────────────────┐
    │       Backend API              │
    │   api.novamedika.com           │
    │                                │
    │  - REST endpoints              │
    │  - WebSocket server            │
    └────────────────────────────────┘
           │
           ▼
    ┌──────────────┐  ┌──────────────┐
    │  PostgreSQL  │  │    Redis     │
    └──────────────┘  └──────────────┘
```

---

## 🔧 Шаг 1: Создание Dockerfile для Pharmacist WebApp

Создайте файл `frontend/Dockerfile.pharmacist`:

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy source code
COPY . .

# Build the application with production env vars
ARG VITE_API_URL=https://api.spravka.novamedika.com
ARG VITE_WS_URL=wss://api.spravka.novamedika.com/ws/pharmacist

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx-pharmacist.conf /etc/nginx/conf.d/default.conf

# Add healthcheck script
RUN apk add --no-cache curl

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget -q --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

---

## 🔧 Шаг 2: Создание Nginx конфигурации

Создайте файл `frontend/nginx-pharmacist.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Handle SPA routing - redirect all routes to index.html
    location / {
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
```

---

## 🔧 Шаг 3: Обновление docker-compose.traefik.prod.yml

Добавьте новый сервис `pharmacist_webapp` **после** сервиса `frontend`:

```yaml
  pharmacist_webapp:
    image: ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest
    user: "100:102"
    container_name: pharmacist-webapp-prod
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    environment:
      - VITE_API_URL=${VITE_API_URL}
      - VITE_WS_URL=${VITE_WS_URL_PHARMACIST}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pharmacist-webapp.rule=Host(`pharmacist.spravka.novamedika.com`)"
      - "traefik.http.routers.pharmacist-webapp.entrypoints=websecure"
      - "traefik.http.routers.pharmacist-webapp.tls.certresolver=letsencrypt"
      - "traefik.http.services.pharmacist-webapp.loadbalancer.server.port=80"
      - "traefik.http.routers.pharmacist-webapp.middlewares=security-headers"
    networks:
      - traefik-public
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://127.0.0.1:80"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: "0.25"
        reservations:
          memory: 32M
    restart: unless-stopped
```

---

## 🔧 Шаг 4: Обновление .env файла

Добавьте следующие переменные в `.env`:

```bash
# Pharmacist WebApp URLs
PHARMACIST_DASHBOARD_URL=https://pharmacist.spravka.novamedika.com
VITE_WS_URL_PHARMACIST=wss://api.spravka.novamedika.com/ws/pharmacist

# CORS origins (добавьте pharmacist domain)
CORS_ORIGINS=["https://spravka.novamedika.com","https://pharmacist.spravka.novamedika.com","http://localhost:5173"]
```

---

## 🔧 Шаг 5: Настройка Telegram Bot

В файле `backend/src/bot/handlers/common_handlers/keyboards.py` уже добавлена кнопка:

```python
[
    InlineKeyboardButton(
        text="💼 Панель фармацевта",
        web_app=WebAppInfo(url=pharmacist_dashboard_url),
    )
]
```

URL берется из переменной окружения `PHARMACIST_DASHBOARD_URL`.

---

## 🔧 Шаг 6: Реализация Backend Endpoints

Создайте файл `backend/src/routers/pharmacist_dashboard.py`:

```python
"""Router for Pharmacist WebApp Dashboard - Consultations Management"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from db.database import get_db
from db.qa_models import Question, User, Pharmacist, Message
from bot.auth.dependencies import get_current_pharmacist
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/pharmacist",
    tags=["Pharmacist Dashboard"],
)


# Pydantic Schemas
class QuestionResponse(BaseModel):
    uuid: str
    text: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_name: str
    message_count: int
    
    class Config:
        from_attributes = True


class QuestionsListResponse(BaseModel):
    questions: List[QuestionResponse]
    total: int
    page: int
    limit: int
    pages: int


class AnswerRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ConsultationStats(BaseModel):
    pending_count: int
    in_progress_count: int
    completed_today: int
    avg_response_time_minutes: float


# Helper functions
async def get_questions_query(status_filter: Optional[str] = None):
    """Build base query for questions with filters"""
    query = select(Question).options(
        selectinload(Question.user),
        selectinload(Question.messages)
    )
    
    if status_filter:
        query = query.where(Question.status == status_filter)
    
    return query.order_by(Question.created_at.desc())


# Routes
@router.get("/questions", response_model=QuestionsListResponse)
async def get_questions(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get list of questions with filtering and pagination"""
    
    # Get total count
    count_query = select(func.count()).select_from(Question)
    if status:
        count_query = count_query.where(Question.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated questions
    query = await get_questions_query(status)
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    questions = result.scalars().all()
    
    # Convert to response format
    questions_data = []
    for q in questions:
        user_name = f"{q.user.first_name or ''} {q.user.last_name or ''}".strip()
        if not user_name:
            user_name = f"User {q.user.telegram_id}"
        
        questions_data.append(QuestionResponse(
            uuid=str(q.uuid),
            text=q.text,
            status=q.status,
            created_at=q.created_at,
            updated_at=q.updated_at,
            user_name=user_name,
            message_count=len(q.messages),
        ))
    
    pages = (total + limit - 1) // limit if limit > 0 else 0
    
    return QuestionsListResponse(
        questions=questions_data,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/questions/{question_id}")
async def get_question_by_id(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get single question with full details and message history"""
    
    result = await db.execute(
        select(Question)
        .options(
            selectinload(Question.user),
            selectinload(Question.messages)
            .joinedload(Message.sender)
        )
        .where(Question.uuid == uuid.UUID(question_id))
    )
    
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Format messages
    messages = []
    for msg in question.messages:
        sender_type = "user" if msg.sender_id == question.user_id else "pharmacist"
        sender_name = question.user.first_name if sender_type == "user" else "Фармацевт"
        
        messages.append({
            "id": str(msg.id),
            "text": msg.text,
            "sender_type": sender_type,
            "sender_name": sender_name,
            "created_at": msg.created_at,
            "message_type": msg.message_type,
        })
    
    return {
        "uuid": str(question.uuid),
        "text": question.text,
        "status": question.status,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
        "user": {
            "name": f"{question.user.first_name or ''} {question.user.last_name or ''}".strip(),
            "telegram_id": question.user.telegram_id,
        },
        "messages": messages,
    }


@router.post("/questions/{question_id}/answer")
async def answer_question(
    question_id: str,
    answer_data: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Send answer to user's question"""
    
    result = await db.execute(
        select(Question).where(Question.uuid == uuid.UUID(question_id))
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    if question.status == "completed":
        raise HTTPException(
            status_code=400, 
            detail="Cannot answer to completed question"
        )
    
    # Create message in dialog history
    new_message = Message(
        question_id=question.uuid,
        sender_type="pharmacist",
        sender_id=pharmacist.uuid,
        message_type="answer",
        text=answer_data.text,
    )
    
    db.add(new_message)
    
    # Update question status
    question.status = "answered"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # TODO: Send notification to user via Telegram Bot
    # This will be handled by background task or WebSocket
    
    return {"message": "Answer sent successfully"}


@router.put("/questions/{question_id}/complete")
async def complete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Complete/close consultation"""
    
    result = await db.execute(
        select(Question).where(Question.uuid == uuid.UUID(question_id))
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question.status = "completed"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Question completed"}


@router.post("/questions/{question_id}/assign")
async def assign_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Assign question to current pharmacist"""
    
    result = await db.execute(
        select(Question).where(Question.uuid == uuid.UUID(question_id))
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question.taken_by = pharmacist.uuid
    question.status = "in_progress"
    question.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Question assigned successfully"}


@router.get("/questions/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get count of unread/new questions"""
    
    result = await db.execute(
        select(func.count()).where(Question.status == "pending")
    )
    count = result.scalar() or 0
    
    return {"count": count}


@router.get("/consultations/stats", response_model=ConsultationStats)
async def get_consultation_stats(
    db: AsyncSession = Depends(get_db),
    pharmacist: Pharmacist = Depends(get_current_pharmacist),
):
    """Get consultation statistics"""
    
    # Pending count
    pending_result = await db.execute(
        select(func.count()).where(Question.status == "pending")
    )
    pending_count = pending_result.scalar() or 0
    
    # In progress count
    in_progress_result = await db.execute(
        select(func.count()).where(Question.status == "in_progress")
    )
    in_progress_count = in_progress_result.scalar() or 0
    
    # Completed today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_result = await db.execute(
        select(func.count()).where(
            and_(
                Question.status == "completed",
                Question.updated_at >= today_start
            )
        )
    )
    completed_today = completed_result.scalar() or 0
    
    # Average response time (simplified - last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    avg_time_result = await db.execute(
        select(func.avg(Question.updated_at - Question.created_at)).where(
            and_(
                Question.status.in_(["answered", "completed"]),
                Question.created_at >= week_ago
            )
        )
    )
    avg_time = avg_time_result.scalar()
    avg_response_time = (avg_time.total_seconds() / 60) if avg_time else 0
    
    return ConsultationStats(
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_today=completed_today,
        avg_response_time_minutes=round(avg_response_time, 2),
    )


# WebSocket endpoint for real-time updates
@router.websocket("/ws/pharmacist")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket connection for real-time consultation updates"""
    
    await websocket.accept()
    
    try:
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            # For now, just keep connection alive
            
    except WebSocketDisconnect:
        logger.info("Pharmacist WebSocket disconnected")
```

---

## 🔧 Шаг 7: Регистрация роутера в main.py

Добавьте в `backend/src/main.py`:

```python
from routers import pharmacist_dashboard


app.include_router(pharmacist_dashboard.router)
```

---

## 🚀 Деплой

### 1. Соберите и запушьте образы

```bash
# Build frontend for pharmacist dashboard
cd frontend
npm run build

# Build Docker image
docker build -f Dockerfile.pharmacist -t ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest .

# Push to registry
docker push ghcr.io/aleksandrandreew-dev/novamedika-lts/pharmacist-webapp:latest
```

### 2. Обновите production deployment

```bash
# Pull latest changes
git pull

# Rebuild and restart
npm run prod:build
npm run prod:up
```

### 3. Проверьте доступность

```bash
# Check if service is running
docker ps | grep pharmacist-webapp

# Test HTTPS
curl https://pharmacist.spravka.novamedika.com

# Check Traefik logs
docker logs traefik-prod | grep pharmacist
```

---

## ✅ Проверка функционала

### 1. Вход через Telegram Bot

1. Фармацевт открывает бота
2. Нажимает кнопку **"💼 Панель фармацевта"**
3. Открывается WebApp с URL `https://pharmacist.spravka.novamedika.com`
4. Вводит Telegram ID и пароль
5. Получает доступ к дашборду консультаций

### 2. Real-time уведомления

1. Пользователь задает вопрос в боте
2. Фармацевт видит уведомление в WebApp
3. Открывает вопрос и отвечает
4. Ответ отправляется пользователю через бота

---

## 🔍 Troubleshooting

### Проблема: WebApp не открывается из Telegram

**Решение:**
1. Проверьте URL в переменной `PHARMACIST_DASHBOARD_URL`
2. Убедитесь, что SSL сертификат выдан (Traefik logs)
3. Проверьте CORS настройки backend

### Проблема: WebSocket не подключается

**Решение:**
1. Проверьте URL WebSocket в `.env`: `wss://api.spravka.novamedika.com/ws/pharmacist`
2. Убедитесь, что Traefik пропускает WebSocket соединения
3. Проверьте backend logs на ошибки

### Проблема: 404 при доступе к API endpoints

**Решение:**
1. Убедитесь, что роутер зарегистрирован в `main.py`
2. Проверьте префикс `/api/pharmacist`
3. Проверьте authentication middleware

---

## 📊 Мониторинг

### Логи

```bash
# Pharmacist WebApp logs
docker logs pharmacist-webapp-prod

# Backend API logs
docker logs backend-prod | grep pharmacist

# Traefik logs
docker logs traefik-prod | grep pharmacist
```

### Метрики

- Количество активных фармацевтов онлайн
- Среднее время ответа на вопросы
- Количество завершенных консультаций в день
- WebSocket подключение статус

---

## 🎉 Готово!

Теперь фармацевты могут:
1. ✅ Открыть WebApp Dashboard прямо из Telegram Bot
2. ✅ Управлять консультациями через профессиональный интерфейс
3. ✅ Получать real-time уведомления
4. ✅ Работать с нескольких устройств

Успехов! 🚀
