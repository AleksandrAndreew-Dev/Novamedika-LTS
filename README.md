# Novamedika 2 — Справочный сервис поиска лекарств

Full-stack приложение (FastAPI + React) с интеграцией Telegram-бота и автоматическим деплоем.

## 🏗 Архитектура

- **Backend:** FastAPI, aiogram 3.x (Telegram Bot), Celery, Redis.
- **Frontend:** React 19, Vite.
- **Proxy/Edge:** Traefik v3.6 (HTTPS, TLS Let's Encrypt).
- **DB:** PostgreSQL 17.

## 📂 Структура проекта

- `backend/` — Серверная часть, логика бота и фоновые задачи. Использует `uv`.
- `frontend/` — Клиентская часть на React.
- `oac/` — Документация и политики для аттестации ОАЦ РБ (Класс 3-ин).
- `traefic/` — Конфигурация динамического роутинга и сертификатов.
- `uploaded_csv/` — Хранилище данных для синхронизации аптек.

## 🛠 Разработка и Workflow

Проект разработан по принципу: **Локальная разработка -> Git Push -> CI/CD -> Server**.

### Локальный запуск (Development)

```bash
# Сборка и запуск в dev-режиме
docker-compose -f docker-compose.traefik.dev.yml up --build
```

- Frontend: `http://localhost`
- Backend API: `http://api.localhost`
- Traefik Dashboard: `http://localhost:8080`

### Продакшн (через scripts в корневом package.json)

```bash
npm run prod:up      # Запуск продакшн окружения
npm run prod:logs    # Просмотр логов
npm run prod:restart # Перезапуск всех контейнеров
```

## 🔐 Безопасность и ОАЦ

Проект соответствует требованиям **Класса 3-ин** ОАЦ Республики Беларусь:

- HTTPS/TLS шифрование.
- JWT аутентификация с ролевой моделью.
- Логирование событий безопасности (хранение 1 год).
- Разделение сетей контейнеров.

Подробности в директории `/oac/docs`.
