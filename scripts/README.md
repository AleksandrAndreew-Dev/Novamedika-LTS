# Scripts - Скрипты автоматизации NovaMedika2

Эта папка содержит скрипты для автоматизации настройки безопасности, backup и обслуживания системы.

---

## 📋 Доступные скрипты

### 1. `setup-security.sh` - Быстрая настройка безопасности ⚡

**Назначение:** Автоматическая установка и настройка всех базовых средств защиты

**Что делает:**
- ✅ Устанавливает Fail2Ban (защита от brute-force)
- ✅ Устанавливает ClamAV (антивирус)
- ✅ Настраивает автоматический backup БД и конфигураций
- ✅ Включает расширение pgcrypto в PostgreSQL
- ✅ Настраивает cron jobs для регулярных задач

**Использование:**
```bash
# На сервере (Ubuntu/Debian)
cd /home/novamedika/novamedika2
sudo ./scripts/setup-security.sh
```

**Время выполнения:** ~5-10 минут  
**Требуется:** root/sudo доступ

---

### 2. `backup.sh` - Резервное копирование 💾

**Назначение:** Создание backup базы данных и конфигурационных файлов

**Что делает:**
- Создает backup PostgreSQL с компрессией (gzip)
- Архивирует конфигурационные файлы (.env, docker-compose.yml, сертификаты)
- Проверяет целостность backup
- Удаляет старые backup (> 365 дней)
- Ведет лог всех операций

**Использование:**

**Ручной запуск:**
```bash
./scripts/backup.sh
```

**Через cron (автоматически ежедневно в 2:00):**
```bash
# Добавить в crontab
crontab -e
0 2 * * * /usr/local/bin/backup.sh >> /backups/backup.log 2>&1
```

**Где хранятся backup:**
- БД: `/backups/db/db_YYYYMMDD_HHMMSS.sql.gz`
- Конфиги: `/backups/configs/configs_YYYYMMDD_HHMMSS.tar.gz`
- Логи: `/backups/backup.log`

**Требования:**
- Docker должен быть запущен
- Контейнер `postgres-prod` должен работать

---

### 3. `fail2ban-jail.local` - Конфигурация Fail2Ban 🛡️

**Назначение:** Правила защиты от brute-force атак

**Защищает:**
- SSH (макс. 3 попытки, бан на 24 часа)
- Traefik/Web auth (макс. 5 попыток, бан на 1 час)
- Nginx bot search (макс. 2 попытки, бан на 24 часа)
- Рецидивисты (3 бана = бан на 1 неделю)

**Установка:**
```bash
# Копирование конфигурации
sudo cp scripts/fail2ban-jail.local /etc/fail2ban/jail.local

# Перезапуск Fail2Ban
sudo systemctl restart fail2ban

# Проверка статуса
sudo fail2ban-client status
```

**Проверка забаненных IP:**
```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status traefik-auth
```

**Разбанить IP:**
```bash
sudo fail2ban-client set sshd unbanip 192.168.1.100
```

---

## 🚀 Быстрый старт (Quick Start)

### Для нового сервера:

```bash
# 1. Клонируйте репозиторий
git clone <repo-url>
cd novamedika2

# 2. Запустите автоматическую настройку безопасности
sudo ./scripts/setup-security.sh

# 3. Проверьте статус сервисов
sudo fail2ban-client status
sudo systemctl status clamav-daemon
ls -la /backups/

# 4. Готово! Система защищена ✓
```

### Для существующего сервера:

```bash
# 1. Обновите репозиторий
git pull

# 2. Скопируйте новые скрипты
sudo cp scripts/backup.sh /usr/local/bin/backup.sh
sudo chmod +x /usr/local/bin/backup.sh

# 3. Обновите конфигурацию Fail2Ban
sudo cp scripts/fail2ban-jail.local /etc/fail2ban/jail.local
sudo systemctl restart fail2ban

# 4. Запустите backup вручную
sudo /usr/local/bin/backup.sh
```

---

## 📊 Мониторинг и обслуживание

### Проверка статуса backup:

```bash
# Последние backup
ls -lht /backups/db/ | head -5
ls -lht /backups/configs/ | head -5

# Размер всех backup
du -sh /backups/

# Логи backup
tail -50 /backups/backup.log
```

### Проверка Fail2Ban:

```bash
# Общий статус
sudo fail2ban-client status

# Статус отдельных jails
sudo fail2ban-client status sshd
sudo fail2ban-client status traefik-auth

# Логи Fail2Ban
sudo tail -50 /var/log/fail2ban.log
```

### Проверка ClamAV:

```bash
# Статус демона
sudo systemctl status clamav-daemon

# Последнее сканирование
sudo cat /var/log/clamav/scan.log | tail -20

# Ручное сканирование
sudo clamscan -r --infected /var/lib/docker/volumes
```

---

## 🔧 Troubleshooting

### Backup не работает:

**Проблема:** "Контейнер postgres-prod не найден"
```bash
# Решение: Проверьте имя контейнера
docker ps --format '{{.Names}}'

# Исправьте в backup.sh переменную POSTGRES_CONTAINER
```

**Проблема:** "Нет места на диске"
```bash
# Проверьте место
df -h

# Очистите старые backup вручную
find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

### Fail2Ban не запускается:

**Проблема:** "Job for fail2ban.service failed"
```bash
# Проверьте логи
sudo journalctl -u fail2ban -n 50

# Проверьте синтаксис конфигурации
sudo fail2ban-client -d

# Исправьте ошибки в /etc/fail2ban/jail.local
```

### ClamAV не обновляется:

**Проблема:** "freshclam error"
```bash
# Остановите службу
sudo systemctl stop clamav-freshclam

# Обновите вручную
sudo freshclam

# Запустите службу
sudo systemctl start clamav-freshclam
```

---

## 📅 Расписание задач (Cron Jobs)

После выполнения `setup-security.sh` будут настроены следующие задачи:

| Время | Задача | Команда |
|-------|--------|---------|
| Ежедневно 2:00 | Backup БД и конфигов | `/usr/local/bin/backup.sh` |
| Ежедневно 3:00 | Сканирование на вирусы | `clamscan -r /var/lib/docker/volumes` |

**Проверка cron:**
```bash
crontab -l
```

---

## 🔐 Безопасность скриптов

### Права доступа:

```bash
# Скрипты должны быть исполняемыми
chmod +x scripts/*.sh

# Backup script при копировании в /usr/local/bin
sudo chmod 755 /usr/local/bin/backup.sh
sudo chown root:root /usr/local/bin/backup.sh
```

### Хранение паролей:

⚠️ **ВАЖНО:** Скрипт `backup.sh` получает пароли из переменных окружения Docker контейнеров. Никогда не хардкодьте пароли в скриптах!

---

## 📚 Дополнительные ресурсы

- [OAC-FREE-SOLUTIONS.md](../OAC-FREE-SOLUTIONS.md) - Полное руководство по бесплатным инструментам
- [OAC-FREE-SOLUTIONS-CHEATSHEET.md](../OAC-FREE-SOLUTIONS-CHEATSHEET.md) - Краткая шпаргалка
- [Fail2Ban Documentation](https://www.fail2ban.org/)
- [ClamAV Documentation](https://docs.clamav.net/)

---

## 🤝 Contributing

Если вы хотите улучшить скрипты:

1. Протестируйте изменения в dev окружении
2. Добавьте комментарии к новым функциям
3. Обновите этот README
4. Создайте Pull Request

---

**Последнее обновление:** 21 апреля 2026 г.  
**Версия:** 1.0
