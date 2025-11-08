# main.py - исправленные импорты
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging

# Добавить недостающие импорты:
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from celery import Celery

# Исправить пути импортов:

from db.database import Base, engine, get_db, async_session_maker
import asyncio

from router.upload import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Backend starting up...")

    # Создаем таблицы при старте
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database tables created/verified")
    yield

    print("🔴 Backend shutting down...")
    await engine.dispose()


app = FastAPI(
    title="Novamedika API",
    description="Backend API for Novamedika",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

# В main.py исправить URL Redis
celery = Celery(
    __name__,
    broker="redis://redis:6379/0",  # было localhost
    backend="redis://redis:6379/0"   # было localhost
)

# Более безопасная обработка CORS
origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# CORS configuration
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
