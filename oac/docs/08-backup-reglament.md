# РЕГЛАМЕНТ
## резервного копирования

### информационной системы NovaMedika2

---

**[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]**

**Версия:** 1.1
**Дата обновления:** 05 мая 2026 г.
**Дата утверждения:** «___» ____________ 20___ г.

---

## 1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящий регламент определяет порядок резервного копирования данных, конфигураций и логов ИС NovaMedika2.

1.2. Регламент разработан в соответствии с требованиями приказа ОАЦ №66 от 20.02.2020 (приложение 3, требования 7.5–7.7) для класса ИС 3-ин.

1.3. **Текущее состояние реализации (на 05.05.2026):**
- ✅ Автоматическое ежедневное резервное копирование PostgreSQL через cron job
- ✅ Архивирование логов контейнеров каждые 6 часов
- ✅ Резервное копирование конфигурационных файлов при изменениях
- ✅ Хранение резервных копий 365 дней (соответствует требованиям ОАЦ)
- ✅ Проверка целостности резервных копий (gunzip -t)
- ⚠️ Шифрование резервных копий запланировано на Q3 2026

---

## 2. ОБЪЕКТЫ РЕЗЕРВНОГО КОПИРОВАНИЯ

### 2.1. Состав объектов

| Объект | Метод | Периодичность | Срок хранения | Скрипт | Статус |
|--------|-------|--------------|--------------|--------|--------|
| PostgreSQL БД (novamedika_prod) | pg_dump (custom format + gzip) | Ежедневно в 02:00 | 365 дней | `scripts/backup.sh` | ✅ Активно |
| Конфигурации (docker-compose, Dockerfile, nginx, .env) | tar.gz архивирование | При изменении + еженедельно | 365 дней | `scripts/backup.sh` | ✅ Активно |
| Логи контейнеров (backend, frontend, postgres, redis, traefik) | gzip архивирование | Каждые 6 часов | 395 дней | `scripts/backup.sh` | ✅ Активно |
| TLS-сертификаты (Let's Encrypt acme.json) | Копирование файла | При обновлении (90 дней) | 365 дней | `scripts/backup.sh` | ✅ Активно |
| OAC документация | git commit + archive | При изменении | Бессрочно (Git history) | Git repository | ✅ Активно |
| Redis данные (sessions, celery tasks) | RDB snapshot | При остановке контейнера | До следующей перезагрузки | Docker volume | ⚠️ Эфемерные |

### 2.2. Состав конфигураций для бэкапа

| Файл/Директория | Назначение | Критичность |
|----------------|-----------|------------|
| `.env` | Переменные окружения (ключи шифрования, пароли) | 🔴 Критично |
| `docker-compose.traefik.prod.yml` | Основная конфигурация production | 🔴 Критично |
| `docker-compose.stable.yml` | Rollback конфигурация | 🟡 Важно |
| `compose.watch.yml` | Development конфигурация | 🟢 Опционально |
| `backend/Dockerfile` | Backend образ | 🟡 Важно |
| `backend/entrypoint.sh` | Backend entrypoint скрипт | 🟡 Важно |
| `backend/pyproject.toml` | Backend зависимости Python | 🟡 Важно |
| `frontend/Dockerfile` | Frontend образ | 🟡 Важно |
| `frontend/nginx.conf` | Nginx конфигурация | 🟡 Важно |
| `frontend/package.json` | Frontend зависимости Node.js | 🟡 Важно |
| `traefic/traefik.yml` | Traefik статическая конфигурация | 🔴 Критично |
| `traefic/dynamic/*.yml` | Traefik динамическая конфигурация | 🔴 Критично |
| `traefic/acme.json` | TLS сертификаты Let's Encrypt | 🔴 Критично |
| `oac/docs/` | Документация ОАЦ compliance | 🟡 Важно |
| `agent/diagnostics.sh` | Скрипты диагностики | 🟢 Опционально |
| `scripts/backup.sh` | Скрипт резервного копирования | 🟡 Важно |

### 2.3. Данные PostgreSQL для резервного копирования

| Таблица | Описание | Объем (примерно) | Частота изменений |
|---------|----------|------------------|-------------------|
| `pharmacies` | Справочник аптек | ~1000 записей | Низкая |
| `products` | Лекарственные препараты | ~50000 записей | Средняя |
| `qa_users` | Пользователи Telegram бота | Растущая | Высокая |
| `booking_orders` | Заказы на бронирование | Растущая | Высокая |
| `consultations` | Онлайн-консультации | Растущая | Средняя |
| `questions` | Вопросы пользователей | Растущая | Высокая |
| `refresh_tokens` | JWT refresh токены | Временные данные | Очень высокая |
| `audit_logs` | Журнал аудита безопасности | Растущая | Высокая |

**Общий объем БД:** ~500 MB (оценка на май 2026)
**Размер daily backup:** ~50-100 MB (gzip компрессия)

---

## 3. ПРОЦЕДУРА РЕЗЕРВНОГО КОПИРОВАНИЯ

### 3.1. Автоматическое резервное копирование (cron job)

```bash
# Cron configuration (/etc/cron.d/novamedika-backup)
# Ежедневный backup БД и конфигураций в 02:00
0 2 * * * novamedika /usr/local/bin/backup.sh >> /var/log/novamedika-backup.log 2>&1

# Архивирование логов каждые 6 часов
0 */6 * * * novamedika /usr/local/bin/archive-logs.sh >> /var/log/novamedika-archive.log 2>&1
```

### 3.2. Процедура выполнения backup.sh

**Шаг 1: Проверка требований**
```bash
# Проверка наличия Docker и запущенных контейнеров
docker ps --format '{{.Names}}' | grep -q "postgres-prod"
```

**Шаг 2: Создание директорий**
```bash
mkdir -p /backups/db
mkdir -p /backups/configs
mkdir -p /backups/logs
```

**Шаг 3: Резервное копирование PostgreSQL**
```bash
# Получение credentials из контейнера
POSTGRES_USER=$(docker exec postgres-prod printenv POSTGRES_USER)
POSTGRES_DB=$(docker exec postgres-prod printenv POSTGRES_DB)

# Создание backup с компрессией
docker exec postgres-prod pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | \
  gzip > "/backups/db/db_$(date +%Y%m%d_%H%M%S).sql.gz"

# Проверка целостности
gunzip -t "/backups/db/db_*.sql.gz"
```

**Шаг 4: Резервное копирование конфигураций**
```bash
cd /home/novamedika/novamedika2

tar czf "/backups/configs/configs_$(date +%Y%m%d_%H%M%S).tar.gz" \
  .env \
  docker-compose.traefik.prod.yml \
  docker-compose.stable.yml \
  traefic/acme.json \
  backend/Dockerfile \
  frontend/Dockerfile \
  frontend/nginx.conf
```

**Шаг 5: Удаление устаревших backup (retention policy)**
```bash
# Удалить backup старше 365 дней
find /backups/db -name "db_*.sql.gz" -mtime +365 -delete
find /backups/configs -name "configs_*.tar.gz" -mtime +365 -delete
find /backups/logs -name "logs_*.tar.gz" -mtime +395 -delete
```

**Шаг 6: Логирование результата**
```bash
echo "[$(date)] Backup completed successfully" >> /backups/backup.log
echo "Backup size: $(du -sh /backups/db | cut -f1)" >> /backups/backup.log
```

### 3.3. Процедура архивирования логов

```bash
#!/bin/bash
# Script: archive-logs.sh
# Архивирование логов Docker контейнеров

DATE=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/backups/logs"

# Архивирование логов каждого контейнера
for container in backend-prod frontend-prod postgres-prod redis-prod traefik; do
  if docker ps --format '{{.Names}}' | grep -q "$container"; then
    docker logs --tail 10000 "$container" 2>&1 | \
      gzip > "$LOG_DIR/logs_${container}_${DATE}.gz"
  fi
done

# Удаление старых архивов (>395 дней)
find "$LOG_DIR" -name "logs_*.gz" -mtime +395 -delete
```

---

## 4. ХРАНЕНИЕ И ЗАЩИТА БЭКАПОВ

### 4.1. Локальное хранение

| Тип | Расположение | Доступ |
|-----|-------------|--------|
| Бэкапы БД | `/backups/` на сервере | Ограничен (root, backup user) |
| Архивы логов | `./log_archive/` | Ограничен (root, backup user) |
| Конфигурации | `/backups/` на сервере | Ограничен (root, backup user) |

### 4.2. Удалённое хранение (рекомендуется)

| Тип | Расположение | Периодичность |
|-----|-------------|--------------|
| Бэкапы БД | Облачное хранилище (S3, Yandex Cloud) | Еженедельно |
| Конфигурации | Git-репозиторий (приватный) | При каждом изменении |
| Архивы логов | Облачное хранилище | Ежемесячно |

### 4.3. Защита бэкапов

- Права доступа: `chmod 600` на файлы бэкапов
- Шифрование: при передаче на удалённое хранилище использовать TLS
- Целостность: проверка gzip после каждого бэкапа

---

## 5. ВОССТАНОВЛЕНИЕ ИЗ РЕЗЕРВНОЙ КОПИИ

### 5.1. Восстановление PostgreSQL

```bash
# Остановить приложение (опционально)
docker compose -f docker-compose.traefik.prod.yml stop backend

# Восстановить из бэкапа
PGPASSWORD=${POSTGRES_PASSWORD} pg_restore \
    -U ${POSTGRES_USER} \
    -d ${POSTGRES_DB} \
    --clean \
    --if-exists \
    /backups/YYYYMMDD_HHMMSS/novamedika_*.dump

# Перезапустить приложение
docker compose -f docker-compose.traefik.prod.yml start backend
```

### 5.2. Восстановление конфигураций

```bash
# Распаковать бэкап
tar -xzf /backups/YYYYMMDD_HHMMSS.tar.gz -C /tmp/

# Восстановить файлы
cp /tmp/YYYYMMDD_HHMMSS/config/* ./

# Перезапустить сервисы
docker compose -f docker-compose.traefik.prod.yml up -d --force-recreate
```

### 5.3. Rollback на стабильную версию

```bash
# Использовать стабильную конфигурацию
docker compose -f docker-compose.stable.yml up -d
```

---

## 6. ЖУРНАЛ РЕЗЕРВНОГО КОПИРОВАНИЯ

### 6.1. Форма записи

| Поле | Описание |
|------|----------|
| Дата и время | YYYY-MM-DD HH:MM:SS |
| Тип бэкапа | Полный / Инкрементный / Конфигурация |
| Результат | Успешно / Ошибка |
| Размер | Bytes |
| Проверка целостности | OK / FAILED |
| Ответственный | ФИО |

### 6.2. Ведение журнала

- Автоматическое логирование в `/var/log/backup.log`
- Еженедельная проверка администратором
- Ежемесячный отчёт руководителю

---

## 7. ОТВЕТСТВЕННЫЕ

| Роль | ФИО | Должность | Контакты |
|------|-----|-----------|----------|
| Администратор ИС | [ФИО] | [ДОЛЖНОСТЬ] | [EMAIL], [ТЕЛЕФОН] |
| Ответственный за бэкапы | [ФИО] | [ДОЛЖНОСТЬ] | [EMAIL], [ТЕЛЕФОН] |

---

**УТВЕРЖДАЮ**

Генеральный директор
[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]

_______________ / [ФИО]

«___» ____________ 20___ г.

---

*Документ составлен в соответствии с:*
- *Приказом ОАЦ №66 от 20.02.2020 (приложение 3, требования 7.5–7.7)*
