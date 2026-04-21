# Project Rules: NovaMedika2

## Архитектура и Workflow
- **Workflow:** Локальная разработка -> `git push` -> GitHub Actions (deploy.yml/develop.yml) -> Автоматический деплой на сервер.
- **Backend:** Python FastAPI, менеджер пакетов `uv`. Запуск через `gunicorn/uvicorn` в Docker.
- **Frontend:** React + Vite. Сборка через Docker (nginx).
- **Database:** PostgreSQL 17.
- **Proxy:** Traefik v3.6 (управляет TLS и маршрутизацией).
- **Bot:** aiogram 3.x для логики Telegram-бота.

## Правила разработки
1. **Безопасность (ОАЦ):**
   - Все новые эндпоинты должны проверять роли (user/pharmacist/admin).
   - Логирование действий пользователей обязательно.
   - Персональные данные должны обрабатываться согласно `oac/docs/04-privacy-policy.md`.
2. **Backend:**
   - Используй `uv` для управления зависимостями в `backend/`.
   - При добавлении моделей БД — обязательно создавай миграции `alembic`.
3. **Frontend:**
   - Используй `Vite` для сборки.
   - Все API запросы должны идти через `/api/` (проксируется Traefik).
4. **Docker:**
   - Не изменяй `docker-compose.*.yml` без необходимости.
   - Используй `npm run prod:up` из корня для управления продакшн-контейнерами.
5. **Git:**
   - Не комить `.env` файлы.
   - Обновляй `.env.example`, если добавляешь новые переменные окружения.

## Структура проекта
- `/backend`: FastAPI, Bot, Celery.
- `/frontend`: React приложение.
- `/oac`: Документация для регулятора (ОАЦ РБ).
- `/traefic`: Конфигурация прокси.
- `/uploaded_csv`: Папка для синхронизации данных аптек.
