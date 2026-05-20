#!/bin/bash
# Script: setup-backup-system.sh
# Description: Настройка полной системы резервного копирования NovaMedika2
# Usage: sudo ./setup-backup-system.sh (запускать от root или с sudo)
# Requirements: Docker, cron, gzip, tar

set -e  # Остановка при ошибке

# ==================== КОНФИГУРАЦИЯ ====================
PROJECT_DIR="/opt/novamedika-prod"
BACKUP_DIR="/backups"
DB_BACKUP_DIR="$BACKUP_DIR/db"
CONFIG_BACKUP_DIR="$BACKUP_DIR/configs"
LOG_ARCHIVE_DIR="$BACKUP_DIR/logs"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

echo "========================================="
echo "NovaMedika2 Backup System Setup"
echo "========================================="
echo ""

# ==================== ШАГ 1: Создание директорий ====================
echo "📁 Шаг 1: Создание директорий для бэкапов..."
mkdir -p "$DB_BACKUP_DIR"
mkdir -p "$CONFIG_BACKUP_DIR"
mkdir -p "$LOG_ARCHIVE_DIR"
chmod 750 "$BACKUP_DIR"
chmod 750 "$DB_BACKUP_DIR"
chmod 750 "$CONFIG_BACKUP_DIR"
chmod 750 "$LOG_ARCHIVE_DIR"
echo "✅ Директории созданы: $BACKUP_DIR"
echo ""

# ==================== ШАГ 2: Копирование скриптов ====================
echo "📋 Шаг 2: Установка скриптов бэкапа..."

if [ -f "$SCRIPTS_DIR/backup.sh" ]; then
    cp "$SCRIPTS_DIR/backup.sh" /usr/local/bin/backup.sh
    chmod +x /usr/local/bin/backup.sh
    echo "✅ backup.sh установлен в /usr/local/bin/"
else
    echo "❌ ERROR: backup.sh не найден в $SCRIPTS_DIR"
    exit 1
fi

if [ -f "$SCRIPTS_DIR/archive-logs.sh" ]; then
    cp "$SCRIPTS_DIR/archive-logs.sh" /usr/local/bin/archive-logs.sh
    chmod +x /usr/local/bin/archive-logs.sh
    echo "✅ archive-logs.sh установлен в /usr/local/bin/"
else
    echo "❌ ERROR: archive-logs.sh не найден в $SCRIPTS_DIR"
    exit 1
fi
echo ""

# ==================== ШАГ 3: Настройка Cron Jobs ====================
echo "⏰ Шаг 3: Настройка cron задач..."

# Создаем временный файл для cron
CRON_TEMP=$(mktemp)

# Получаем текущие cron задачи
crontab -l 2>/dev/null > "$CRON_TEMP" || true

# Проверяем и добавляем задачи если их нет
if ! grep -q "backup.sh" "$CRON_TEMP"; then
    echo "# NovaMedika2 - Ежедневный backup БД и конфигураций (02:00)" >> "$CRON_TEMP"
    echo "0 2 * * * /usr/local/bin/backup.sh >> /var/log/novamedika-backup.log 2>&1" >> "$CRON_TEMP"
    echo "✅ Добавлен daily backup (02:00)"
else
    echo "⚠️  Daily backup уже настроен"
fi

if ! grep -q "archive-logs.sh" "$CRON_TEMP"; then
    echo "# NovaMedika2 - Архивирование логов каждые 6 часов" >> "$CRON_TEMP"
    echo "0 */6 * * * /usr/local/bin/archive-logs.sh >> /var/log/novamedika-archive.log 2>&1" >> "$CRON_TEMP"
    echo "✅ Добавлен log archiving (каждые 6 часов)"
else
    echo "⚠️  Log archiving уже настроен"
fi

# Устанавливаем обновленные cron задачи
crontab "$CRON_TEMP"
rm -f "$CRON_TEMP"

echo ""
echo "Текущие cron задачи:"
crontab -l | grep -E "(backup|archive)" || echo "  (нет задач)"
echo ""

# ==================== ШАГ 4: Тестовый запуск ====================
echo "🧪 Шаг 4: Тестовый запуск backup.sh..."
echo "Запускаем первый бэкап для проверки..."

if /usr/local/bin/backup.sh; then
    echo "✅ Тестовый backup выполнен успешно!"
else
    echo "❌ ERROR: Тестовый backup завершился с ошибкой"
    echo "Проверьте логи: tail -f /backups/backup.log"
    exit 1
fi
echo ""

echo "🧪 Шаг 5: Тестовый запуск archive-logs.sh..."
if /usr/local/bin/archive-logs.sh; then
    echo "✅ Тестовое архивирование логов выполнено успешно!"
else
    echo "❌ WARNING: Архивирование логов завершилось с ошибками"
    echo "Проверьте логи: tail -f /backups/archive-logs.log"
fi
echo ""

# ==================== ШАГ 6: Проверка результатов ====================
echo "📊 Шаг 6: Проверка созданных бэкапов..."
echo ""
echo "Backup БД:"
ls -lh "$DB_BACKUP_DIR"/db_*.sql.gz 2>/dev/null | tail -3 || echo "  (пусто)"
echo ""
echo "Backup конфигураций:"
ls -lh "$CONFIG_BACKUP_DIR"/configs_*.tar.gz 2>/dev/null | tail -3 || echo "  (пусто)"
echo ""
echo "Архивы логов:"
ls -lh "$LOG_ARCHIVE_DIR"/logs_*.gz 2>/dev/null | tail -5 || echo "  (пусто)"
echo ""

# ==================== ШАГ 7: Мониторинг дискового пространства ====================
echo "💾 Шаг 7: Проверка дискового пространства..."
df -h "$BACKUP_DIR"
echo ""
echo "Размер директории бэкапов:"
du -sh "$BACKUP_DIR"
echo ""

# ==================== ШАГ 8: Рекомендации ====================
echo "========================================="
echo "✅ SETUP COMPLETED SUCCESSFULLY"
echo "========================================="
echo ""
echo "Настроено:"
echo "  ✅ Daily backup БД и конфигов (каждый день в 02:00)"
echo "  ✅ Архивирование логов (каждые 6 часов)"
echo "  ✅ Retention policy: 365 дней для БД, 395 дней для логов"
echo "  ✅ Автоматическая очистка старых бэкапов"
echo ""
echo "Расположение бэкапов:"
echo "  📁 Бэкапы БД: $DB_BACKUP_DIR"
echo "  📁 Бэкапы конфигов: $CONFIG_BACKUP_DIR"
echo "  📁 Архивы логов: $LOG_ARCHIVE_DIR"
echo ""
echo "Логи выполнения:"
echo "  📄 /backups/backup.log"
echo "  📄 /backups/archive-logs.log"
echo ""
echo "Следующие шаги:"
echo "  1. Проверьте расписание: crontab -l"
echo "  2. Мониторьте дисковое пространство: df -h"
echo "  3. Настройте remote backup (S3/Yandex Cloud) для надежности"
echo "  4. Протестируйте восстановление из бэкапа"
echo ""
echo "Для ручного запуска:"
echo "  sudo /usr/local/bin/backup.sh"
echo "  sudo /usr/local/bin/archive-logs.sh"
echo ""
