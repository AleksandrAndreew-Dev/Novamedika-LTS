# ЛОГИЧЕСКАЯ СХЕМА
## информационной системы NovaMedika2

---

**Наименование информационной системы:** NovaMedika2 — Справочный сервис поиска лекарственных средств

**Класс типовых информационных систем:** 3-ин

---

## 1. Направления информационных потоков

### 1.1 Внешние информационные потоки

| № | Откуда | Куда | Протокол | Назначение | Данные |
|---|--------|------|----------|------------|--------|
| W1 | Пользователь (браузер) | Frontend (nginx :80) | HTTPS | Загрузка SPA, поиск, заказы | Запросы поиска, данные заказов |
| W2 | Пользователь (браузер) | Backend (FastAPI :8000) | HTTPS | API-запросы (axios) | Поиск FTS, заказы, auth |
| W3 | Telegram Server | Backend (webhook :8000) | HTTPS | Webhook-сообщения бота | Тексты, callback_query |
| W4 | Аптека (CSV upload) | Backend (upload :8000) | HTTPS + Basic Auth | Загрузка CSV товаров | CSV-файлы с данными |
| W5 | Backend → Tabletka.by API | Внешний HTTPS | HTTPS | Синхронизация аптек | Данные аптек, наличие |
| W6 | Backend → A1 SMS API | Внешний HTTPS | HTTPS | SMS-уведомления | Телефон, текст |
| W7 | Backend → Telegram API | Внешний HTTPS | HTTPS | Отправка сообщений ботом | Тексты, клавиатуры |
| W8 | Traefik → Let's Encrypt | Внешний HTTPS | HTTPS | Получение TLS-сертификатов | ACME challenge |

### 1.2 Внутренние информационные потоки

| № | Откуда | Куда | Протокол | Назначение | Данные |
|---|--------|------|----------|------------|--------|
| I1 | Traefik → Backend | :8000 | HTTP | Маршрутизация API | Все API-запросы |
| I2 | Traefik → Frontend | :80 | HTTP | Маршрутизация SPA | Статика, index.html |
| I3 | Backend → PostgreSQL | :5432 | TCP (asyncpg) | Запросы к БД | SQL-запросы, ответы |
| I4 | Backend → Redis | :6379 | TCP | FSM-Storage, кэш | Данные состояний бота |
| I5 | Celery → Redis | :6379 | TCP | Broker задач | Задачи Celery |
| I6 | Celery → PostgreSQL | :5432 | TCP | Обработка CSV, upsert | Данные товаров, хэши |
| I7 | Frontend → Backend | :8000 | HTTP (через Traefik) | API-запросы от клиента | Поиск, заказы, auth |

---

## 2. Логические границы информационной системы

**Границы ИС:**

- **Входная точка:** Traefik (entrypoints web :80, websecure :443)
- **Выходные точки:**
  - Telegram API (api.telegram.org)
  - Tabletka.by API
  - A1 SMS API
  - Let's Encrypt ACME
- **Внутренняя изоляция:** Docker сеть `traefik-public` — только контейнеры ИС имеют доступ к PostgreSQL и Redis

### Сегментация:

```
┌─────────────────────────────────────────────────────────────┐
│                    ЗОНА: ВХОДНОЙ ТРАФИК                      │
│                                                              │
│  Traefik (reverse proxy + TLS termination)                  │
│  ├─ entrypoint: web (:80) → redirect → websecure            │
│  ├─ entrypoint: websecure (:443) → TLS + security headers   │
│  └─ маршрутизация:                                          │
│      ├─ api.{DOMAIN}       → backend:8000                   │
│      ├─ spravka.{DOMAIN}   → frontend:80                    │
│      └─ traefik.{DOMAIN}   → dashboard (basic auth)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                ЗОНА: ПРИЛОЖЕНИЯ                              │
│                                                              │
│  Backend (FastAPI :8000)              Frontend (nginx :80)  │
│  ├─ /api/search-fts                     ├─ React SPA        │
│  ├─ /api/upload/{pharmacy}/{number}/    ├─ Static files     │
│  ├─ /api/webhook                        └─ nginx.conf       │
│  ├─ /api/auth/*                                               │
│  ├─ /api/orders                                               │
│  └─ Telegram Bot (aiogram)                                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                ЗОНА: ДАННЫЕ                                  │
│                                                              │
│  PostgreSQL (:5432)                  Redis (:6379)           │
│  ├─ pharmacies                       ├─ Celery broker        │
│  ├─ products (+ FTS, search_vector)  ├─ Bot FSM Storage     │
│  ├─ qa_users                           └─ Кэш                 │
│  ├─ qa_questions                                              │
│  ├─ qa_answers                                                │
│  ├─ qa_dialog_messages                                        │
│  ├─ qa_pharmacists                                            │
│  ├─ booking_orders                                            │
│  ├─ pharmacy_api_configs                                      │
│  ├─ sync_logs                                                 │
│  └─ refresh_tokens                                            │
│                                                               │
│  Celery Worker (без открытых портов)                         │
│  └─ process_csv_incremental                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Информационные ресурсы

| № | Ресурс | IP-адрес | Сервер/Контейнер | Назначение |
|---|--------|----------|-----------------|------------|
| 1 | `api.spravka.novamedika.com` | [Docker IP] | backend-prod | FastAPI REST API |
| 2 | `spravka.novamedika.com` | [Docker IP] | frontend-prod | React SPA |
| 3 | `traefik.spravka.novamedika.com` | [Docker IP] | traefik-prod | Dashboard (basic auth) |
| 4 | PostgreSQL БД | [Docker IP] | postgres-prod | Основной volume: `postgres_data` |
| 5 | Redis кэш | [Docker IP] | redis-prod | Основной volume: `redis_data` |
| 6 | Uploaded CSV | Хост | backend-prod | Volume: `./uploaded_csv:/app/uploaded_csv` |
| 7 | TLS-сертификаты | Хост | traefik-prod | Volume: `./letsencrypt:/letsencrypt` |

---

## 4. Средства защиты информации

| № | Средство | IP-адрес администрирования | Назначение |
|---|---------|--------------------------|------------|
| 1 | Let's Encrypt ACME | — | Автоматическое получение/обновление TLS-сертификатов |
| 2 | Traefik Security Headers | — | CSP, HSTS (31536000s), X-Frame-Options SAMEORIGIN, X-Content-Type nosniff, Referrer-Policy, XSS-Filter |
| 3 | JWT (access 30 мин + refresh 7 дней) | — | Аутентификация фармацевтов, Q&A доступ |
| 4 | Fernet-шифрование | — | Шифрование API-токенов в `pharmacy_api_configs` |
| 5 | Redis AUTH (требует пароль) | — | Защита от несанкционированного доступа к Redis |
| 6 | PostgreSQL AUTH (логин/пароль) | — | Защита от несанкционированного доступа к БД |
| 7 | HTTP Basic Auth | — | Защита эндпоинтов `/upload/`, `/load-pharmacies`, `/clear-all-data` |
| 8 | API Keys | — | Защита `/orders`, Q&A read-эндпоинтов |
| 9 | Docker non-root | — | Все контейнеры работают от непривилегированных пользователей |
| 10 | Docker resource limits | — | Ограничение CPU/RAM для каждого контейнера |

---

## 5. Открытые порты транспортного уровня

| IP-адрес | Порт | Протокол | Технология/Сервис | Доступ |
|----------|------|----------|-------------------|--------|
| [Внешний IP] | 443 | TCP/TLS | HTTPS (Traefik → все сервисы) | Внешний (Интернет) |
| [Внешний IP] | 80 | TCP | HTTP (Traefik → redirect → HTTPS) | Внешний (Интернет) |
| [Docker IP] | 8000 | TCP | HTTP (FastAPI + gunicorn) | Только Traefik |
| [Docker IP] | 80 | TCP | HTTP (nginx) | Только Traefik |
| [Docker IP] | 5432 | TCP | PostgreSQL | Только backend, celery |
| [Docker IP] | 6379 | TCP | Redis (требует AUTH) | Только backend, celery |

---

## 6. Спецификация используемых технологий и протоколов

| Уровень | Технология/Протокол | Назначение |
|---------|-------------------|------------|
| Транспортный | TCP | Все внутренние соединения |
| Транспортный | TLS 1.3 | Внешний HTTPS (Let's Encrypt) |
| Сетевой | HTTP/2 | Traefik → клиенты |
| Сетевой | HTTP/1.1 | Внутренние соединения (Traefik → backend/frontend) |
| Прикладной | FastAPI (ASGI) | Backend API |
| Прикладной | gunicorn (3 uvicorn workers) | WSGI-сервер |
| Прикладной | aiogram 3.x | Telegram-бот |
| Прикладной | React 19 + Vite | Frontend SPA |
| Прикладной | nginx | Статика + SPA routing |
| Прикладной | asyncpg | Async PostgreSQL driver |
| Прикладной | Celery + Redis | Фоновые задачи |
| Прикладной | SQLAlchemy 2.0 | ORM |
| Сетевой | Docker bridge network | Изоляция контейнеров |
| Транспортный | WebSockets | Telegram-бот (aiogram long-polling/webhook) |

---

## 7. Списки VLAN

| VLAN ID | VLAN Name | IP-подсеть | Назначение |
|---------|-----------|------------|------------|
| — | `traefik-public` | Docker bridge (172.x.0.0/16) | Основная Docker сеть |

*Примечание: VLAN не используется на уровне хостинга. Сегментация обеспечивается Docker bridge network.*

---

## 8. IP-адреса устройств

| Устройство | Внешний IP | Внутренний IP | Docker IP | Назначение |
|-----------|-----------|--------------|-----------|------------|
| Сервер (хост) | [ВНЕШНИЙ IP] | 127.0.0.1 | — | Хост-машина |
| traefik-prod | — | — | [DOCKER IP] | Reverse proxy |
| backend-prod | — | — | [DOCKER IP] | API + бот |
| frontend-prod | — | — | [DOCKER IP] | SPA + nginx |
| postgres-prod | — | — | [DOCKER IP] | СУБД |
| redis-prod | — | — | [DOCKER IP] | Кэш/брокер |
| celery-worker-prod | — | — | [DOCKER IP] | Фоновые задачи |

---

## 9. Схема информационных потоков (текстовое описание)

```
                          ┌──────────────────────┐
                          │    ИНТЕРНЕТ           │
                          │  (открытые каналы)    │
                          └──────────┬───────────┘
                                     │ HTTPS (443)
                          ┌──────────▼───────────┐
                          │     TRAEFIK v3.6      │
                          │  :80 → :443 redirect  │
                          │  Security Headers     │
                          │  TLS (Let's Encrypt)  │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
          ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
          │  api.{DOMAIN}  │ │ spravka.     │ │ traefik.     │
          │  → backend:8000│ │ {DOMAIN}     │ │ {DOMAIN}     │
          │                │ │ → frontend:80│ │ → dashboard  │
          └───────┬────────┘ └──────┬───────┘ └──────────────┘
                  │                 │
      ┌───────────▼─────────────────▼───────────┐
      │            БЭКЕНД (FastAPI)              │
      │                                          │
      │  ┌──────────────────────────────────┐   │
      │  │  Роутеры:                        │   │
      │  │  • search (/search-fts)          │   │
      │  │  • upload (CSV, Basic Auth)      │   │
      │  │  • auth (JWT)                    │   │
      │  │  • qa (вопросы/ответы)           │   │
      │  │  • orders (заказы)               │   │
      │  │  • telegram_bot (webhook)        │   │
      │  └──────────────────────────────────┘   │
      │                                          │
      │  ┌──────────────────────────────────┐   │
      │  │  Telegram Bot (aiogram 3.x)      │   │
      │  │  • Регистрация фармацевтов       │   │
      │  │  • Q&A система                   │   │
      │  │  • FSM (Redis Storage)           │   │
      │  └──────────────────────────────────┘   │
      └────────┬───────────────────┬────────────┘
               │                   │
     ┌─────────▼──────┐  ┌────────▼────────┐
     │  PostgreSQL :5432│ │  Redis :6379    │
     │  (9+ таблиц)    │ │  (broker + FSM) │
     │                 │ │                  │
     │  • pharmacies   │ │  • Celery queue  │
     │  • products+FTS │ │  • Bot states    │
     │  • qa_*         │ │  • Кэш           │
     │  • booking_*    │ │                  │
     │  • refresh_*    │ │                  │
     └─────────────────┘ └───────┬─────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Celery Worker          │
                    │  (process_csv)           │
                    │                           │
                    │  • CSV parsing           │
                    │  • Hash-diff             │
                    │  • Batch upsert          │
                    │  • Tabletka sync (3x/d)  │
                    └──────────────────────────┘
```

---

**Дата составления:** «___» ____________ 20___ г.

**Составил:** [Должность, ФИО] _______________ (подпись)
