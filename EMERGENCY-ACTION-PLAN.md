# 🚨 СРОЧНЫЕ ДЕЙСТВИЯ ДЛЯ PRODUCTION СЕРВЕРА

**Дата:** 2026-05-20  
**Сервер:** aleksandr@server-uxqgoe:/opt/novamedika-prod  
**Статус:** ⚠️ **КРИТИЧЕСКИЙ** - Нет бэкапов, диск заполнен на 86%

---

## 📊 ТЕКУЩАЯ СИТУАЦИЯ

### ❌ Критические проблемы:

1. **БЭКАПЫ НЕ РАБОТАЮТ**
   - Директория `/backups/` не существует
   - Cron jobs для backup.sh не настроены
   - Скрипт `archive-logs.sh` отсутствовал (сейчас создан)
   - **Нет ни одного бэкапа БД или конфигураций!**

2. **ДИСК ЗАПОЛНЕН НА 86%**
   ```
   /dev/sda1: 25GB использовано из 30GB
   Доступно: всего 4.2GB
   ```
   - При текущих темпах роста это критический уровень
   - Логи Docker могут заполнить оставшееся место за несколько дней

3. **Docker volumes занимают 2.698GB**
   - postgres_data: основной объем данных
   - loki-data: растущий объем логов
   - prometheus-data: метрики за ~395 дней

### ✅ Что работает:

- ✅ Loki запущен и работает (retention policy настроен на 395 дней)
- ✅ Prometheus запущен (healthy, retention 395 дней)
- ✅ Promtail собирает логи
- ✅ Docker log rotation настроен (max-size: 10m, max-file: 3)

---

## 🔧 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ

### **ШАГ 1: Экстренная очистка диска** (освободить ~3-5GB)

Выполните на сервере:

```bash
cd /opt/novamedika-prod

# Сделать скрипт исполняемым
chmod +x scripts/emergency-disk-cleanup.sh

# Запустить очистку
sudo ./scripts/emergency-disk-cleanup.sh
```

**Что сделает скрипт:**
- Удалит stopped containers
- Удалит unused Docker images старше 7 дней (~2.7GB)
- Очистит build cache
- Очистит старые system logs
- Покажет результат

**Ожидаемый результат:** Освобождение 3-5GB дискового пространства

---

### **ШАГ 2: Настройка системы бэкапов**

```bash
cd /opt/novamedika-prod

# Сделать скрипт исполняемым
chmod +x scripts/setup-backup-system.sh

# Запустить настройку (требует sudo)
sudo ./scripts/setup-backup-system.sh
```

**Что сделает скрипт:**
1. ✅ Создаст директории: `/backups/db`, `/backups/configs`, `/backups/logs`
2. ✅ Установит скрипты в `/usr/local/bin/`:
   - `backup.sh` - ежедневный backup БД и конфигов
   - `archive-logs.sh` - архивирование логов каждые 6 часов
3. ✅ Настроит cron jobs:
   - Daily backup в 02:00
   - Log archiving каждые 6 часов
4. ✅ Выполнит тестовый запуск обоих скриптов
5. ✅ Проверит созданные бэкапы

**Результат после выполнения:**
- Первый бэкап БД будет создан в `/backups/db/`
- Первый backup конфигураций в `/backups/configs/`
- Первые архивы логов в `/backups/logs/`
- Cron jobs будут активны

---

### **ШАГ 3: Проверка результата**

```bash
# 1. Проверить cron jobs
crontab -l

# Ожидаемый вывод:
# 0 2 * * * /usr/local/bin/backup.sh >> /var/log/novamedika-backup.log 2>&1
# 0 */6 * * * /usr/local/bin/archive-logs.sh >> /var/log/novamedika-archive.log 2>&1

# 2. Проверить бэкапы
ls -lh /backups/db/
ls -lh /backups/configs/
ls -lh /backups/logs/

# 3. Проверить логи выполнения
tail -20 /backups/backup.log
tail -20 /backups/archive-logs.log

# 4. Проверить дисковое пространство
df -h /
docker system df

# 5. Проверить состояние сервисов
docker ps | grep -E "(loki|prometheus|promtail)"
```

---

## 📋 РАСПИСАНИЕ БЭКАПОВ (ПОСЛЕ НАСТРОЙКИ)

| Задача | Частота | Время | Что делает |
|--------|---------|-------|------------|
| **Backup БД** | Ежедневно | 02:00 | pg_dump + gzip → `/backups/db/` |
| **Backup конфигов** | Ежедневно | 02:00 | tar.gz → `/backups/configs/` |
| **Архив логов** | Каждые 6 часов | 00:00, 06:00, 12:00, 18:00 | docker logs + gzip → `/backups/logs/` |
| **Очистка старых бэкапов** | Автоматически | При каждом запуске | Удаляет старше 365/395 дней |

---

## 💾 ХРАНЕНИЕ ДАННЫХ (ПОСЛЕ НАСТРОЙКИ)

| Тип данных | Расположение | Срок хранения | Размер (примерно) |
|-----------|--------------|---------------|-------------------|
| **Бэкапы БД** | `/backups/db/` | 365 дней | ~50-100 MB каждый |
| **Бэкапы конфигов** | `/backups/configs/` | 365 дней | ~1-5 MB каждый |
| **Архивы логов** | `/backups/logs/` | 395 дней | ~10-50 MB каждый |
| **Loki logs** | Docker volume `loki-data` | 395 дней | Зависит от нагрузки |
| **Prometheus metrics** | Docker volume `prometheus-data` | 395 дней | Зависит от метрик |
| **Docker container logs** | `/var/lib/docker/containers/` | ~30 MB max | Rotation при достижении лимита |

---

## ⚠️ ВАЖНЫЕ РЕКОМЕНДАЦИИ

### **1. Мониторинг дискового пространства**

Добавьте в crontab еженедельную проверку:

```bash
crontab -e

# Добавить строку:
0 9 * * 1 df -h / >> /var/log/disk-space-monitor.log 2>&1
```

Или используйте существующий скрипт мониторинга:
```bash
./agent/diagnostics.sh --all
```

### **2. Remote Backup (КРИТИЧНО!)**

**Проблема:** Все бэкапы хранятся локально на том же сервере. При потере сервера теряются и бэкапы.

**Рекомендация:** Настроить синхронизацию с облачным хранилищем:

```bash
# Пример для Yandex Cloud Object Storage (S3-compatible)
# Установить s3cmd или awscli
sudo apt install s3cmd

# Настроить доступ
s3cmd --configure

# Добавить в backup.sh после создания бэкапа:
s3cmd put /backups/db/db_*.sql.gz s3://novamedika-backups/db/
s3cmd put /backups/configs/configs_*.tar.gz s3://novamedika-backups/configs/
```

### **3. Тестирование восстановления**

Раз в месяц проверяйте возможность восстановления:

```bash
# 1. Посмотреть доступные бэкапы
ls -lt /backups/db/ | head -5

# 2. Восстановить БД (на тестовом окружении!)
gunzip -c /backups/db/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB

# 3. Проверить целостность данных
docker exec postgres-prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT count(*) FROM users;"
```

### **4. Увеличение диска**

**Текущий диск:** 30GB (заполнен на 86%)  
**Рекомендуемый размер:** 50-100GB

Причины:
- Бэкапы за год: ~36GB (БД) + ~7GB (логи) = ~43GB
- Docker volumes: ~3-5GB
- Система и приложения: ~5GB
- Reserve для роста: ~10GB

---

## 📞 КОНТАКТЫ И ЭСКАЛАЦИЯ

Если возникнут проблемы:

1. **Проверить логи:**
   ```bash
   tail -f /backups/backup.log
   tail -f /backups/archive-logs.log
   ```

2. **Проверить статус сервисов:**
   ```bash
   docker ps
   systemctl status cron
   ```

3. **Запустить диагностику:**
   ```bash
   ./agent/diagnostics.sh --all
   ```

4. **Проверить disk space:**
   ```bash
   df -h
   du -sh /backups/*
   docker system df
   ```

---

## ✅ CHECKLIST ВЫПОЛНЕНИЯ

- [ ] Шаг 1: Запустить emergency-disk-cleanup.sh
- [ ] Проверить освобождение места: `df -h` (цель: <80%)
- [ ] Шаг 2: Запустить setup-backup-system.sh
- [ ] Проверить создание директорий: `ls -la /backups/`
- [ ] Проверить cron jobs: `crontab -l`
- [ ] Проверить первый backup: `ls -lh /backups/db/`
- [ ] Проверить первый archive logs: `ls -lh /backups/logs/`
- [ ] Проверить логи: `tail /backups/backup.log`
- [ ] Задокументировать результат
- [ ] Настроить remote backup (план на следующую неделю)
- [ ] Добавить мониторинг disk space в weekly check

---

## 📝 ПРИМЕЧАНИЯ

### **Соответствие требованиям ОАЦ:**

✅ **Пункт 1.2:** Обеспечение сбора и хранения сведений о событиях ИБ ≥ 1 года
- Реализовано через archive-logs.sh (каждые 6 часов, хранение 395 дней)

✅ **Пункт 4.3:** Резервное копирование данных
- Реализовано через backup.sh (ежедневно, хранение 365 дней)

✅ **Пункт 5.1:** Мониторинг состояния системы
- Реализовано через Prometheus + Loki + Grafana

⚠️ **Требуется доработка:**
- Remote backup для защиты от потери сервера
- Регулярное тестирование восстановления
- Alerting при неудачных бэкапах

---

**Созданные файлы:**
- ✅ [`scripts/archive-logs.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\archive-logs.sh) - новый скрипт
- ✅ [`scripts/setup-backup-system.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\setup-backup-system.sh) - новый скрипт
- ✅ [`scripts/emergency-disk-cleanup.sh`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\scripts\emergency-disk-cleanup.sh) - новый скрипт
- ✅ [`EMERGENCY-ACTION-PLAN.md`](file://c:\Users\37525\Desktop\upwork\projects\Novamedika2\EMERGENCY-ACTION-PLAN.md) - этот документ

**Следующие шаги:**
1. Загрузить новые скрипты на сервер (`git pull`)
2. Выполнить ШАГ 1 и ШАГ 2 из инструкции выше
3. Проверить результат
4. Запланировать настройку remote backup
