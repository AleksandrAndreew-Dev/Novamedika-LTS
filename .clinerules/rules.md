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

---

## 🚀 Быстрые команды (Quick Commands)

### Диагностика проблем
```bash
# Полная диагностика всех компонентов
bash agent/diagnostics.sh all

# Только статус контейнеров (быстрая проверка)
bash agent/diagnostics.sh status

# Логи с автофильтрацией ошибок
bash agent/diagnostics.sh logs

# Backend логи (последние 500 строк)
bash agent/diagnostics.sh backend

# Frontend + API тесты
bash agent/diagnostics.sh frontend

# Telegram бот диагностика
bash agent/diagnostics.sh bot

# База данных + Redis статистика
bash agent/diagnostics.sh db
```

### Управление средой
```bash
# Production
npm run prod:up           # Запустить всё
npm run prod:down         # Остановить всё
npm run prod:restart      # Перезапустить всё
npm run prod:restart-backend    # Только backend
npm run prod:restart-frontend   # Только frontend
npm run prod:logs         # Просмотр логов
npm run prod:ps           # Статус контейнеров
npm run prod:build        # Пересобрать образы

# Development
docker-compose -f docker-compose.traefik.dev.yml up --build

# Monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### Проверка безопасности
```bash
# OAC compliance check
py oac/check_normative_docs.py

# OWASP ZAP scan
sh scripts/run-zap-scan.sh
```

---

## 📁 Ключевые файлы для быстрого доступа

### Backend Core
- `backend/src/main.py` - Точка входа FastAPI
- `backend/src/auth/` - Аутентификация и JWT
- `backend/src/bot/` - Telegram бот (aiogram)
- `backend/src/routers/` - API endpoints
- `backend/src/tasks/` - Celery задачи
- `backend/src/db/` - Модели SQLAlchemy и сессии

### Frontend Core
- `frontend/src/App.jsx` - Главный компонент
- `frontend/src/pages/` - Страницы приложения
- `frontend/src/components/` - Переиспользуемые компоненты
- `frontend/src/api/` - API клиенты
- `frontend/src/telegram/` - Интеграция с Telegram WebApp

### Configuration
- `docker-compose.traefik.prod.yml` - Production конфигурация
- `docker-compose.traefik.dev.yml` - Development конфигурация
- `.env.example` - Шаблон переменных окружения
- `traefic/traefik.yml` - Настройки Traefik

### Documentation & Compliance
- `.ai-rules.md` - **ПРАВИЛА AI-АГЕНТА** (читать первым!)
- `oac/docs/` - 13 документов для ОАЦ Class 3-in
- `oac/guides/` - Руководства по внедрению
- `oac/audits/` - Аудиты и отчеты
- `README.md` - Общая документация проекта

### Scripts & Automation
- `agent/diagnostics.sh` - **Главный инструмент диагностики**
- `scripts/backup.sh` - Резервное копирование
- `scripts/setup-security.sh` - Настройка безопасности
- `scripts/deploy-with-monitoring.sh` - Деплой с мониторингом

---

## 🔍 Паттерны поиска кода

### Когда искать код:
1. **Проблемы с аутентификацией** → `backend/src/auth/` + `frontend/src/hooks/useAuth*`
2. **Telegram бот не работает** → `backend/src/bot/` + `agent/diagnostics.sh bot`
3. **API endpoint не отвечает** → `backend/src/routers/` + проверить Traefik маршруты
4. **База данных** → `backend/src/db/models*.py` + `backend/alembic/versions/`
5. **Celery задачи** → `backend/src/tasks/` + проверить Redis статус
6. **Frontend ошибки** → `frontend/src/` + `agent/diagnostics.sh frontend`
7. **OAC compliance** → `oac/docs/` + `oac/checklist/`

### Инструменты для поиска:
- `search_symbol` - для конкретных классов/функций (PmsProduct, UserService)
- `search_codebase` - для концепций (authentication, encryption, consent)
- `grep_code` - для текстовых паттернов (regex)
- `read_file` - всегда использовать `view_dependencies=true` при модификации

---

## ⚠️ Критические правила (.ai-rules.md summary)

### ЗАПРЕЩЕНО говорить:
- ❌ "✅ FULLY IMPLEMENTED"
- ❌ "Works perfectly"
- ❌ "Problem solved"
- ❌ "100% working"

### РАЗРЕШЕНО говорить:
- ✅ "Код изменен согласно спецификации"
- ✅ "Готово к тестированию - требуется ваша проверка"
- ✅ "Изменения применены, ожидает подтверждения"

### Обязательная структура ответа:
```markdown
## Статус выполнения

**Что сделано:**
- [конкретные изменения]

**Что НЕ проверено:**
- [что требует тестирования]

**Следующие шаги:**
1. [шаг 1]
2. [шаг 2]
```

---

## 🎯 Специфика проекта Novamedika2

### OAC Class 3-in Compliance (КРИТИЧНО)
Все изменения должны учитывать:
- Шифрование персональных данных (см. `oac/docs/10-encryption-policy.md`)
- Трансграничная передача данных (Telegram = трансграничная!)
- Audit logs всех действий
- Согласие пользователя на обработку данных
- Право на удаление/экспорт данных

### Технические особенности:
1. **Traefik управляет всем трафиком** - все запросы через него
2. **Celery + Redis** для фоновых задач (импорт CSV, уведомления)
3. **Alembic** для миграций БД - никогда не менять модели без миграции
4. **JWT + RBAC** - три роли: user, pharmacist, admin
5. **Telegram WebApp** - отдельный flow авторизации
6. **Monitoring stack** - Prometheus + Grafana + Loki + Promtail

### Частые проблемы и решения:
- **Бот не запускается** → проверить Gunicorn workers (`FIX-BOT-GUNICORN-WORKERS.md`)
- **Race condition в auth** → см. `AuthProvider.jsx` и историю коммитов
- **Проблемы с шифрованием** → `oac/guides/ENCRYPTION-IMPLEMENTATION-GUIDE.md`
- **Трансграничная передача** → `oac/privacy-policy/transboundary-transfer-telegram-analysis-2026-05-20.md`

---

## 💡 Оптимизация токенов

### Для экономии контекста:
1. **Не загружать всю документацию OAC** - использовать поиск по ключевым словам
2. **Использовать search_symbol** вместо чтения целых файлов
3. **Читать файлы частями** (start_line, end_line) когда возможно
4. **Использовать diagnostics.sh** вместо ручного сбора логов
5. **Ссылаться на файлы** вместо их полного цитирования

### Примеры эффективных запросов:
```
❌ ПЛОХО: "Покажи мне весь код аутентификации"
✅ ХОРОШО: "Найди символы AuthService.authenticate и JWT token generation"

❌ ПЛОХО: "Прочитай всю документацию OAC"
✅ ХОРОШО: "Найди требования к шифрованию в oac/docs/"

❌ ПЛОХО: "Покажи все логи"
✅ ХОРОШО: "Запусти bash agent/diagnostics.sh errors-only"
```

---

## 📊 MCP Skills (Концептуально)

Если бы использовался MCP, вот какие навыки были бы полезны:

### Skill 1: "OAC Compliance Checker"
- Автоматически проверяет изменения на соответствие ОАЦ
- Ссылается на конкретные документы из `oac/docs/`
- Предлагает необходимые обновления политики

### Skill 2: "Deployment Validator"
- Проверяет docker-compose конфиги
- Валидирует Traefik маршруты
- Проверяет .env переменные

### Skill 3: "Security Auditor"
- Сканирует код на уязвимости
- Проверяет наличие audit logs
- Верифицирует шифрование полей

### Skill 4: "Diagnostic Runner"
- Знает когда запускать diagnostics.sh
- Автоматически анализирует логи
- Предлагает решения на основе ошибок

---

## 🔄 Workflow для AI-агента

### При получении задачи:
1. **Проверить .ai-rules.md** - вспомнить запреты на абсолютные утверждения
2. **Определить область** - backend/frontend/bot/db/compliance
3. **Использовать правильный инструмент**:
   - Код → `search_symbol` или `search_codebase`
   - Конфиги → `read_file` с dependencies
   - Проблемы → `run_in_terminal` с diagnostics.sh
4. **Внести изменения** → `edit_file` с минимальными правками
5. **Проверить** → `get_problems` для валидации
6. **Отчитаться** → использовать обязательную структуру отчета

### При проблемах:
1. Сначала `bash agent/diagnostics.sh all`
2. Анализировать `${TIMESTAMP}_errors-only.txt`
3. Искать конкретные ошибки в коде
4. Предложить решение с учетом OAC compliance
5. Указать что требует проверки в production

---

## 📝 Checklist перед ответом

Перед каждым ответом проверь:
- [ ] Избегал ли я абсолютных утверждений?
- [ ] Использовал ли я правильную структуру отчета?
- [ ] Указал ли что НЕ проверено?
- [ ] Предложил ли конкретные шаги для проверки?
- [ ] Учел ли OAC compliance требования?
- [ ] Использовал ли оптимальные инструменты поиска?
- [ ] Не загрузил ли слишком много контекста?

---

**Версия правил:** 2.0  
**Обновлено:** 2026-05-28  
**Основано на:** `.ai-rules.md` + опыт работы с проектом
