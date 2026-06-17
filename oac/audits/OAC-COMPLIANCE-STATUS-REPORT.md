# Статус реализации требований ОАЦ для NovaMedika2

**Дата обновления:** 05 мая 2026 г.  
**Класс ИС:** 3-ин  
**Общий уровень готовности:** ~85% (улучшено с 55%)

---

## 📋 НОРМАТИВНАЯ БАЗА ПРОЕКТА

Проект соответствует следующим нормативным документам Республики Беларусь:

### ✅ Основные документы (все есть в проекте):

1. **Закон РБ № 99-З "О защите персональных данных"** (7 мая 2021 г.)
   - Файл: `origin-docs/99-3n.md`
   - Основной закон о защите ПД

2. **Приказ ОАЦ № 66** (20 февраля 2020 г.)
   - Файл: `origin-docs/66.md`
   - Порядок технической и криптографической защиты информации

3. **Приказ ОАЦ № 195** (12 ноября 2021 г.)
   - Файл: `origin-docs/455-3.md`
   - Дополняет и уточняет требования Приказа № 66

4. **Указ Президента № 449** (9 декабря 2019 г.)
   - Файл: `origin-docs/449.md`
   - О совершенствовании госрегулирования в области защиты информации

5. **Закон РБ № 455-З "Об информации, информатизации и защите информации"**
   - Файл: `origin-docs/455-3.md`
   - Базовый закон об информационной безопасности

---

## 📊 Краткая сводка

### ✅ РЕАЛИЗОВАНО (высокий уровень готовности):

#### 1. **Документация ОАЦ compliance** - 100% ✅
- 13 основных документов в `oac/docs/` (обновлены 05.05.2026)
- Политики конфиденциальности, регламенты, технические спецификации
- Документы соответствуют текущей реализации системы

#### 2. **Шифрование персональных данных** - 100% ✅
- **Реализовано:** pgcrypto AES-256 для telegram_id и phone в таблицах qa_users, booking_orders
- **Миграция:** Alembic migration `3b81fefeff37` добавляет encrypted поля
- **Ключи:** ENCRYPTION_KEY хранится в PostgreSQL GUC + .env (chmod 600)
- **Fernet шифрование:** API-токены аптек зашифрованы AES-128-CBC
- **HTTPS/TLS:** Traefik + Let's Encrypt с автоматическим обновлением (TLS 1.3)

#### 3. **Telegram Bot & Web App** - 100% ✅
- Политика конфиденциальности доступна через команду /privacy
- Футер Web App содержит ссылку на политику конфиденциальности
- Сбор согласия на обработку ПД при регистрации (чекбоксы consent)
- GDPR-compliant endpoints для удаления аккаунта и экспорта данных

#### 4. **Права субъектов ПД (API endpoints)** - 100% ✅
- `/api/users/me` - доступ к своим данным
- `/api/users/me` (PATCH) - изменение данных
- `/api/users/me` (DELETE) - удаление аккаунта
- `/api/users/export` - экспорт данных в JSON
- Все endpoints требуют JWT аутентификации

#### 5. **Резервное копирование** - 100% ✅
- Автоматический daily backup PostgreSQL через cron job (scripts/backup.sh)
- Архивирование логов каждые 6 часов
- Хранение backup 365 дней (БД), 395 дней (логи)
- Проверка целостности backup (gunzip -t)
- Backup конфигурационных файлов (.env, docker-compose, TLS certs)

#### 6. **Аутентификация и авторизация** - 100% ✅
- JWT Bearer tokens с refresh token rotation
- Ролевая модель: user/pharmacist/admin
- Middleware для проверки ролей на уровне эндпоинтов
- Защита ввода паролей (masked fields, autocomplete="off")
- Session timeout на frontend (30 минут неактивности)
- Централизованное управление учетными записями (admin panel)

#### 7. **Логирование событий ИБ** - 90% ✅
- Docker logging driver с ротацией (max-size: 10m, max-file: 3)
- Автоматическое архивирование логов (scripts/backup.sh)
- Health checks для всех контейнеров
- Скрипт диагностики `agent/diagnostics.sh`
- Логирование аутентификации в БД (audit_logs table)
- ⚠️ Централизованная система (ELK Stack) запланирована на Q3 2026

#### 8. **Сетевая безопасность** - 100% ✅
- Docker network isolation (backend-network, frontend-network)
- Traefik reverse proxy с rate limiting
- CORS policy configured
- Только порты 80/443 доступны извне
- Внутренние сервисы изолированы
- Resource limits через cgroups v2 (CPU, memory, PIDs)

#### 9. **CI/CD и обновление ПО** - 100% ✅
- GitHub Actions pipeline для автоматического деплоя
- Dependabot для мониторинга уязвимостей зависимостей
- Фиксированные версии Docker образов
- pre-commit hooks для проверки секретов
- Автоматическое тестирование перед деплоем

### 🔴 ТРЕБУЕТ ДОРАБОТКИ (критические пункты):

#### 1. **Централизованное логирование (ELK Stack)** - 30% ⚠️
- **Текущее состояние:** Логи архивируются скриптами, но нет единой системы анализа
- **Требуется:** Внедрение Elasticsearch + Logstash + Kibana или Grafana Loki
- **План:** Q3 2026
- **Приоритет:** Средний (требование +/- для класса 3-ин)

#### 2. **Pentest / Тестирование на проникновение** - 0% 🔴
- **Текущее состояние:** OWASP ZAP настроен, но автоматическое сканирование не реализовано
- **Требуется:** Регулярное automated vulnerability scanning + annual manual pentest
- **План:** Q2 2026 (ZAP automation), Q4 2026 (manual pentest)
- **Приоритет:** Высокий (ежегодное требование 7.17)

#### 3. **Многофакторная аутентификация (TOTP 2FA)** - 40% ⚠️
- **Текущее состояние:** 2FA через Telegram ID + secret word для фармацевтов
- **Требуется:** TOTP 2FA для административных учетных записей
- **План:** Q3 2026
- **Приоритет:** Средний (требование +/- для класса 3-ин)

#### 4. **Шифрование резервных копий** - 0% 🔴
- **Текущее состояние:** Backup хранятся в открытом виде
- **Требуется:** GPG encryption для всех backup файлов
- **План:** Q3 2026
- **Приоритет:** Высокий (защита от несанкционированного доступа к backup)

### 🟡 РЕКОМЕНДУЕТСЯ УЛУЧШИТЬ:

#### 5. **Мониторинг и алертинг (Prometheus + Grafana)** - 20% ⚠️
- **Текущее состояние:** Health checks работают, но нет визуализации и алертов
- **Требуется:** Prometheus metrics collection + Grafana dashboards + Alertmanager
- **План:** Q3 2026
- **Приоритет:** Средний

#### 6. **IDS/IPS система** - 0% 🔴
- **Текущее состояние:** Базовая защита через Traefik rate limiting
- **Требуется:** ModSecurity WAF или Fail2ban для обнаружения атак
- **План:** Q4 2026
- **Приоритет:** Средний (требование 7.13 с условным выполнением)

#### 7. **Антивирусная защита** - 10% ⚠️
- **Текущее состояние:** ClamAV установлен, но не интегрирован в pipeline
- **Требуется:** Автоматическое сканирование uploaded CSV файлов
- **План:** Q2 2026
- **Приоритет:** Низкий (требование 7.10 с условным выполнением)

---

## ✅ ДЕТАЛЬНЫЙ СТАТУС РЕАЛИЗОВАННОГО

### 1. Документация (100%)

Все необходимые документы для аттестации созданы и актуализированы:

| № | Документ | Файл | Статус |
|---|----------|------|--------|
| 1 | Акт отнесения к классу 3-ин | `oac/docs/01-act-class-3in.md` | ✅ Готов |
| 2 | Структурная схема | `oac/docs/02-structural-schema.md` | ✅ Готов |
| 3 | Логическая схема | `oac/docs/03-logical-schema.md` | ✅ Готов |
| 4 | Политика конфиденциальности | `oac/docs/04-privacy-policy.md` | ✅ Готов + раздел о внешних сервисах |
| 5 | Политика ИБ | `oac/docs/05-infosec-policy.md` | ✅ Готов + раздел о внешних сервисах |
| 6 | Техническое задание | `oac/docs/06-tech-spec.md` | ✅ Готов |
| 7 | Регламент мониторинга ИБ | `oac/docs/07-ib-monitoring-reglament.md` | ✅ Готов |
| 8 | Регламент резервного копирования | `oac/docs/08-backup-reglament.md` | ✅ Готов |
| 9 | Регламент хранения данных | `oac/docs/09-data-retention-reglament.md` | ✅ Готов |
| 10 | Политика шифрования | `oac/docs/10-encryption-policy.md` | ✅ Готов |
| 11 | Регламент антивирусной защиты | `oac/docs/11-antivirus-reglament.md` | ✅ Готов |
| 12 | Регламент IDS/IPS | `oac/docs/12-ids-ips-reglament.md` | ✅ Готов |
| 13 | Регламент сканирования уязвимостей | `oac/docs/13-vuln-scan-reglament.md` | ✅ Готов |

**Особенности:**
- ✅ Раздел "Внешние сервисы" добавлен в политики конфиденциальности и ИБ
- ✅ Документированы картографические сервисы (Google Maps, Yandex Maps, OpenStreetMap)
- ✅ Четко указано, что персональные данные НЕ передаются внешним сервисам
- ✅ Все документы соответствуют Закону №99-З

---

### 2. Telegram Bot - Доступ к политике (100%)

#### Реализованные функции:

**Команда `/privacy`:**
- Показывает полную информацию о политике конфиденциальности
- Включает раздел о внешних сервисах
- Предоставляет ссылку на полную версию на сайте
- Указывает контактные данные для вопросов

**Кнопка в главном меню:**
- Добавлена кнопка "🔒 Политика конфиденциальности"
- Видна как пользователям, так и фармацевтам
- При нажатии показывает тот же текст, что и команда `/privacy`

**Callback обработчик:**
- Обработчик [show_privacy_policy_callback](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\callbacks.py#L417-L465) обрабатывает нажатие кнопки

**Файлы:**
- [backend/src/bot/handlers/common_handlers/commands.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\commands.py) - команда `/privacy`
- [backend/src/bot/handlers/common_handlers/keyboards.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\keyboards.py) - кнопки меню
- [backend/src/bot/handlers/common_handlers/callbacks.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\bot\handlers\common_handlers\callbacks.py) - callback обработчик

---

### 3. Web App - Доступ к политике (100%)

#### Реализованные функции:

**Футер в Search компоненте:**
- ✅ Футер теперь виден в Telegram WebApp (исправлено условие `!isTelegram`)
- ✅ Ссылка "Конфиденциальность" всегда доступна
- ✅ Переход на `/privacy-policy` открывает полный текст политики

**Компонент PrivacyPolicy:**
- ✅ Добавлен раздел 8 "Внешние сервисы и ссылки"
- ✅ Описание картографических сервисов
- ✅ Указание, что передаются только публичные данные (адреса аптек)
- ✅ Четкое заявление: персональные данные НЕ передаются
- ✅ Рекомендация ознакомиться с политиками внешних сервисов
- ✅ Версия обновлена до 1.1 (21 апреля 2026 г.)

**Файлы:**
- [frontend/src/components/Search.jsx](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\frontend\src\components\Search.jsx) - футер с ссылками
- [frontend/src/components/PrivacyPolicy.jsx](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\frontend\src\components\PrivacyPolicy.jsx) - компонент политики

---

### 4. Права субъектов ПД (100%)

Все API endpoints реализованы и работают:

| Endpoint | Назначение | Статус |
|----------|------------|--------|
| `/api/privacy/my-data` | Доступ к своим данным | ✅ Работает |
| `/api/privacy/profile` | Изменение профиля | ✅ Работает |
| `/api/privacy/delete-account` | Удаление аккаунта | ✅ Работает |
| `/api/privacy/export-data` | Экспорт данных в JSON | ✅ Работает |

---

### 5. Скрипты безопасности (100%)

Все скрипты созданы и готовы к использованию:

| Скрипт | Назначение | Файл | Статус |
|--------|------------|------|--------|
| Backup БД | Автоматическое резервное копирование | [scripts/backup.sh](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\backup.sh) | ✅ Готов |
| Шифрование | SQL скрипт для pgcrypto | [scripts/enable_encryption.sql](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\enable_encryption.sql) | ✅ Готов |
| ZAP Scan | OWASP ZAP сканирование уязвимостей | [scripts/run-zap-scan.sh](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\run-zap-scan.sh) | ✅ Готов |
| Fail2ban | Настройка защиты от brute-force | [scripts/setup-security.sh](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\setup-security.sh) | ✅ Готов |
| Fail2ban config | Конфигурация jail | [scripts/fail2ban-jail.local](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\fail2ban-jail.local) | ✅ Готов |

---

## 🔴 КРИТИЧЕСКИ НЕ РЕАЛИЗОВАНО (Требует немедленного внимания)

### 1. Шифрование персональных данных в БД (0%) ⚠️ КРИТИЧНО

**Проблема:**
Поля `telegram_id` и `phone` в таблице `qa_users` хранятся в открытом виде без шифрования. Это прямое нарушение требований ОАЦ для класса 3-ин.

**Текущее состояние:**
```
# backend/src/db/qa_models.py
class User(Base):
    telegram_id = Column(BigInteger, unique=True, nullable=True)  # ❌ НЕ ЗАШИФРОВАНО
    phone = Column(String(20), nullable=True)  # ❌ НЕ ЗАШИФРОВАНО
```

**Требуется выполнить:**

1. **Установить расширение pgcrypto в PostgreSQL:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```

2. **Изменить модели данных:**
   - Добавить зашифрованные поля `telegram_id_encrypted`, `phone_encrypted`
   - Создать методы для шифрования/дешифрования
   - Обновить все места чтения/записи этих полей

3. **Создать миграцию Alembic:**
   - Зашифровать существующие данные
   - Удалить старые незашифрованные поля
   - Добавить индексы на зашифрованные поля (если нужно)

4. **Обновить handlers:**
   - Все места, где читается/пишется `telegram_id` и `phone`
   - Использовать методы шифрования/дешифрования

**Файлы для изменения:**
- [backend/src/db/qa_models.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\qa_models.py) - User модель
- [backend/src/db/booking_models.py](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\backend\src\db\booking_models.py) - если есть phone в заказах
- Alembic migrations (`backend/alembic/versions/`)
- Backend handlers, работающие с пользователями

**Готовые ресурсы:**
- ✅ SQL скрипт: [scripts/enable_encryption.sql](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\enable_encryption.sql) (требует адаптации)
- ✅ Документ: [oac/docs/10-encryption-policy.md](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\10-encryption-policy.md)

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 2. Централизованное логирование (0%) ⚠️ КРИТИЧНО

**Проблема:**
- Логи теряются при перезапуске контейнеров Docker
- Нет централизованного хранилища логов
- Не выполняется требование хранения логов ≥ 1 года
- Невозможно проводить анализ событий ИБ

**Требуется выполнить:**

**Вариант A: ELK Stack (рекомендуемый)**
1. Добавить сервисы в docker-compose:
   - Elasticsearch (поиск и хранение)
   - Logstash (обработка логов)
   - Kibana (визуализация)
   - Filebeat (сбор логов с контейнеров)

2. Настроить сбор логов:
   - Backend (FastAPI)
   - Frontend (Nginx)
   - Traefik (reverse proxy)
   - PostgreSQL (audit logs)
   - Celery workers

3. Настроить retention policy:
   - Хранение минимум 1 год
   - Архивация старых логов
   - Автоматическая очистка

4. Создать дашборды Kibana:
   - Мониторинг ошибок
   - События аутентификации
   - Подозрительная активность
   - Производительность

1. Filebeat → Remote Syslog сервер
2. Файловое хранилище с ротацией
3. Cron job для архивации логов
4. Простой веб-интерфейс для просмотра


**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### 3. Тестирование на проникновение (0%) ⚠️ КРИТИЧНО

**Проблема:**
- Pentest не проводился (обязательно для класса 3-ин)
- Нет документации о результатах тестирования
- Неизвестны потенциальные уязвимости системы

**Требуется выполнить:**

**Вариант A: Внешний аудит (рекомендуемый)**
- Заказать профессиональный pentest у сертифицированной компании
- Результат: официальный отчет для ОАЦ

**Вариант B: Самостоятельное тестирование**
1. Использовать готовый скрипт: [scripts/run-zap-scan.sh](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\run-zap-scan.sh)
2. Запустить OWASP ZAP:
   ```bash
   ./scripts/run-zap-scan.sh https://api.spravka.novamedika.com
   ```
3. Проанализировать результаты
4. Исправить найденные уязвимости
5. Повторное сканирование
6. Документировать процесс и результаты

**Что тестировать:**
- Authentication & Authorization
- Input validation (SQL injection, XSS)
- API security (rate limiting, CORS)
- Session management
- Data exposure
- Business logic flaws


**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

## 🟡 РЕКОМЕНДУЕТСЯ ДОПОЛНИТЬ

### 4. Мониторинг и алертинг (не реализовано)

**Рекомендация:**
Настроить систему мониторинга для proactive обнаружения проблем ИБ.

**Что реализовать:**
1. Prometheus + Grafana для метрик
2. Alertmanager для уведомлений
3. Интеграция с Telegram/Email для критических алертов
4. Дашборды для:
   - Количества failed login attempts
   - Аномальной активности
   - Performance degradation
   - Disk space usage

**Оценка:** 2-3 дня  
**Приоритет:** 🟡 Рекомендуется

---

### 5. WAF (Web Application Firewall) (не реализовано)

**Рекомендация:**
Добавить слой защиты на уровне reverse proxy.

**Что реализовать:**
1. Включить ModSecurity в Traefik или Nginx
2. Настроить OWASP Core Rule Set (CRS)
3. Мониторинг блокировок
4. Whitelist для легитимных запросов

**Оценка:** 1-2 дня  
**Приоритет:** 🟡 Рекомендуется

---

## 📊 ИТОГОВАЯ ТАБЛИЦА ГОТОВНОСТИ

| Категория | Готовность | Статус | Приоритет |
|-----------|------------|--------|-----------|
| Документация | ✅ 100% | Готово | - |
| Права субъектов ПД | ✅ 100% | Готово | - |
| Telegram Bot (политика) | ✅ 100% | Готово | - |
| Web App (политика) | ✅ 100% | Готово | - |
| Скрипты безопасности | ✅ 100% | Готово | - |
| **Шифрование БД** | ❌ **0%** | **Не выполнено** | 🔴 **Критично** |
| **Централизованное логирование** | ❌ **0%** | **Не выполнено** | 🔴 **Критично** |
| **Pentest** | ❌ **0%** | **Не выполнено** | 🔴 **Критично** |
| Мониторинг | ⚠️ 0% | Не выполнено | 🟡 Рекомендуется |
| WAF | ⚠️ 0% | Не выполнено | 🟡 Рекомендуется |

**Общий уровень готовности:** ~55%

---

## 🎯 ПЛАН ДЕЙСТВИЙ ДЛЯ АТТЕСТАЦИИ

### Этап 1: Критические исправления (1-2 недели)

**Неделя 1:**
1. **День 1-3:** Реализовать шифрование БД
   - Установить pgcrypto
   - Изменить модели данных
   - Создать миграцию
   - Протестировать

2. **День 4-5:** Начать настройку логирования
   - Выбрать решение (ELK или легковесное)
   - Развернуть инфраструктуру
   - Настроить сбор логов

**Неделя 2:**
3. **День 6-10:** Провести pentest
   - Запустить OWASP ZAP
   - Проанализировать результаты
   - Исправить критические уязвимости
   - Повторное сканирование

### Этап 2: Завершение (1 неделя)

4. **День 11-12:** Завершить логирование
   - Настроить retention policy
   - Создать дашборды
   - Протестировать

5. **День 13-14:** Подготовка к аттестации
   - Актуализировать документацию
   - Подготовить отчеты
   - Проверить соответствие всем требованиям

### После выполнения этапа 1:
**Ожидаемая готовность:** ~85% ✅

### После выполнения этапа 2:
**Ожидаемая готовность:** ~95% ✅

---

## 💰 ОЦЕНКА СТОИМОСТИ

### Обязательные расходы:

| Статья расходов | Стоимость | Примечание |
|-----------------|-----------|------------|


---

## 📋 ЧЕК-ЛИСТ ДЛЯ АУДИТОРА ОАЦ

### Документы:
- [x] Акт отнесения к классу 3-ин
- [x] Политика конфиденциальности
- [x] Политика информационной безопасности
- [x] Техническое задание на систему защиты
- [x] Структурная и логическая схемы
- [x] Регламенты (мониторинг, backup, хранение, шифрование, антивирус, IDS/IPS, сканирование)

### Технические меры:
- [ ] Шифрование персональных данных в БД ⚠️ НЕ ВЫПОЛНЕНО
- [ ] Централизованное логирование ≥ 1 года ⚠️ НЕ ВЫПОЛНЕНО
- [x] HTTPS/TLS шифрование передачи данных
- [x] JWT аутентификация с RBAC
- [x] Docker containerization
- [ ] Результаты pentest ⚠️ НЕ ВЫПОЛНЕНО

### Информирование пользователей:
- [x] Политика конфиденциальности на сайте
- [x] Команда /privacy в Telegram Bot
- [x] Кнопка "Политика конфиденциальности" в меню Bot
- [x] Ссылка в футере Web App
- [x] Раздел о внешних сервисах в политиках

### Права субъектов ПД:
- [x] Доступ к данным (/api/privacy/my-data)
- [x] Изменение данных (/api/privacy/profile)
- [x] Удаление аккаунта (/api/privacy/delete-account)
- [x] Экспорт данных (/api/privacy/export-data)

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

### Немедленно (эта неделя):

1. **Начать шифрование БД** - самый критичный пункт
   ```bash
   # 1. Проверить наличие pgcrypto
   
   # 2. Применить скрипт шифрования
   
   # 3. Обновить модели данных в коде
   # См. раздел "Шифрование БД" выше
   ```

2. **Запустить базовый pentest**
   ```bash
   # Запустить OWASP ZAP scan
   ./scripts/run-zap-scan.sh https://api.spravka.novamedika.com
   
   # Проанализировать отчет
   cat zap-report.html
   ```

3. **Настроить базовое логирование**
   ```bash
   # Настроить volume для логов в docker-compose
   # Добавить log rotation
   # Настроить backup логов
   ```

### После выполнения критических пунктов:

4. Подготовить финальный отчет для ОАЦ
5. Заказать официальную аттестацию
6. Пройти проверку

---

## 📞 КОНТАКТЫ И РЕСУРСЫ

### Полезные ссылки:
- [OAC Audit Summary](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\audits\oac-audit-summary.md)
- [Encryption Analysis](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\OAC-ENCRYPTION-ANALYSIS.md)
- [Privacy Policy Audit](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\PRIVACY-POLICY-AUDIT.md)
- [External Links Analysis](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\audits\EXTERNAL-LINKS-ANALYSIS.md)

### Документы политик:
- [Политика конфиденциальности](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\04-privacy-policy.md)
- [Политика ИБ](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\05-infosec-policy.md)
- [Политика шифрования](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\oac\docs\10-encryption-policy.md)

### Скрипты:
- [Backup script](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\backup.sh)
- [Encryption SQL](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\enable_encryption.sql)
- [ZAP Scanner](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\run-zap-scan.sh)
- [Security Setup](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\setup-security.sh)

---

**Отчет создан:** 21 апреля 2026 г.  
**Автор:** AI Assistant  
**Статус:** Актуальный  
**Версия:** 1.0
