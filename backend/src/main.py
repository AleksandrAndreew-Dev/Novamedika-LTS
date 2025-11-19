from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

from db.database import Base, engine

# Импорты роутеров
from routers.upload import router as upload_router
from routers.search import router as search_router
from routers.pharmacies_info import router as pharm_info_router
from routers.telegram_bot import router as telegram_router
from routers.pharmacist_auth import router as pharmacist_router
from routers.qa import router as qa_router
from auth.auth import router as auth_router


# Импорты бота
from bot.core import bot_manager

from bot.handlers.registration import router as registration_router
from bot.handlers.user_questions import router as user_questions_router
from bot.handlers.qa_handlers import router as qa_handlers_router
from bot.handlers.common_handlers import router as common_handlers_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def lifespan(app: FastAPI):
    print("🚀 Backend starting up...")

    # Создаем таблицы при старте
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot, dp = await bot_manager.initialize()
    if bot and dp:
        print("✅ Telegram bot initialized")

        from bot.middleware.db import DbMiddleware
        from bot.middleware.role_middleware import RoleMiddleware

        # Регистрируем middleware
        dp.update.middleware(DbMiddleware())
        dp.update.middleware(RoleMiddleware())

        # Регистрируем роутеры в правильном порядке
        dp.include_router(common_handlers_router)
        dp.include_router(registration_router)
        dp.include_router(user_questions_router)
        dp.include_router(qa_handlers_router)

        # Автоматически устанавливаем webhook в production
        if os.getenv("ENVIRONMENT") == "production":
            try:
                webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
                if webhook_url:
                    secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
                    webhook_config = {
                        "url": webhook_url,
                        "drop_pending_updates": True,
                        "max_connections": 40,
                    }
                    if secret_token:
                        webhook_config["secret_token"] = secret_token

                    await bot.set_webhook(**webhook_config)
                    print(f"✅ Production webhook set: {webhook_url}")
            except Exception as e:
                print(f"❌ Failed to set production webhook: {e}")
    else:
        print("❌ Telegram bot not configured")

    print("✅ Database tables created/verified")
    yield

    print("🔴 Backend shutting down...")
    # Корректное завершение работы бота
    await bot_manager.shutdown()
    await engine.dispose()

app = FastAPI(
    title="Novamedika API",
    description="Backend API for Novamedika",
    version="1.0.0",
    lifespan=lifespan,
)

# Включение роутеров с префиксами
app.include_router(upload_router, tags=["upload"])
app.include_router(search_router, tags=["search"])
app.include_router(pharm_info_router, tags=["pharmacies"])
app.include_router(telegram_router, tags=["telegram"])
app.include_router(pharmacist_router, tags=["pharmacists"])
app.include_router(qa_router, tags=["q&a"])
app.include_router(auth_router, tags=["auth"])

# Более безопасная обработка CORS
origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get_main():
    return {"message": "Hello Novamedika API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "backend", "version": "1.0.0"}

@app.get("/api/info")
async def api_info():
    return {
        "name": "Novamedika Backend",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
