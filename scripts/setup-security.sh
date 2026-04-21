#!/bin/bash
# Script: setup-security.sh
# Description: Быстрая настройка базовой безопасности для NovaMedika2
# Usage: sudo ./setup-security.sh
# WARNING: Запускать от root или через sudo!

set -e

echo "========================================="
echo "NovaMedika2 Security Setup"
echo "========================================="
echo ""

# ==================== 1. Установка Fail2Ban ====================
echo "📦 Шаг 1/4: Установка Fail2Ban..."
if command -v fail2ban-client &> /dev/null; then
    echo "✅ Fail2Ban уже установлен"
else
    apt update
    apt install -y fail2ban
    
    # Копирование конфигурации
    cp scripts/fail2ban-jail.local /etc/fail2ban/jail.local
    
    # Перезапуск службы
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    echo "✅ Fail2Ban установлен и настроен"
fi

# Проверка статуса
echo ""
echo "Статус Fail2Ban:"
fail2ban-client status || true
echo ""

# ==================== 2. Установка ClamAV ====================
echo "📦 Шаг 2/4: Установка ClamAV (антивирус)..."
if command -v clamscan &> /dev/null; then
    echo "✅ ClamAV уже установлен"
else
    apt install -y clamav clamav-daemon
    
    # Обновление вирусных баз
    echo "   Обновление вирусных баз..."
    systemctl stop clamav-freshclam
    freshclam
    systemctl start clamav-freshclam
    systemctl enable clamav-freshclam
    
    # Запуск демона
    systemctl enable clamav-daemon
    systemctl start clamav-daemon
    
    echo "✅ ClamAV установлен"
fi

# Создание cron job для ежедневного сканирования
if ! crontab -l 2>/dev/null | grep -q "clamscan"; then
    echo "   Настройка ежедневного сканирования..."
    (crontab -l 2>/dev/null; echo "0 3 * * * clamscan -r --infected --log=/var/log/clamav/scan.log /var/lib/docker/volumes >> /var/log/clamav/scan.log 2>&1") | crontab -
    echo "✅ Сканирование настроено (ежедневно в 3:00)"
else
    echo "✅ Сканирование уже настроено"
fi

# ==================== 3. Настройка Backup ====================
echo ""
echo "📦 Шаг 3/4: Настройка автоматического backup..."

BACKUP_SCRIPT="/usr/local/bin/backup.sh"
PROJECT_DIR="/home/novamedika/novamedika2"

# Копирование скрипта backup
if [ -f "$PROJECT_DIR/scripts/backup.sh" ]; then
    cp "$PROJECT_DIR/scripts/backup.sh" "$BACKUP_SCRIPT"
    chmod +x "$BACKUP_SCRIPT"
    
    # Создание директории для backup
    mkdir -p /backups
    
    # Настройка cron job
    if ! crontab -l 2>/dev/null | grep -q "backup.sh"; then
        echo "   Настройка ежедневного backup..."
        (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT >> /backups/backup.log 2>&1") | crontab -
        echo "✅ Backup настроен (ежедневно в 2:00)"
    else
        echo "✅ Backup уже настроен"
    fi
    
    # Запуск первого backup
    echo ""
    echo "   🔄 Запуск первого backup..."
    $BACKUP_SCRIPT || echo "⚠️  Первый backup завершился с ошибками (проверьте логи)"
else
    echo "❌ WARNING: Скрипт backup.sh не найден в $PROJECT_DIR/scripts/"
    echo "   Скопируйте его вручную и настройте cron"
fi

# ==================== 4. Включение pgcrypto ====================
echo ""
echo "📦 Шаг 4/4: Проверка расширения pgcrypto в PostgreSQL..."

POSTGRES_CONTAINER="postgres-prod"

if docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
    # Проверка наличия расширения
    if docker exec $POSTGRES_CONTAINER psql -U $(docker exec $POSTGRES_CONTAINER printenv POSTGRES_USER) -d $(docker exec $POSTGRES_CONTAINER printenv POSTGRES_DB) -c "\dx" | grep -q "pgcrypto"; then
        echo "✅ Расширение pgcrypto уже установлено"
    else
        echo "   Установка расширения pgcrypto..."
        docker exec $POSTGRES_CONTAINER psql -U $(docker exec $POSTGRES_CONTAINER printenv POSTGRES_USER) -d $(docker exec $POSTGRES_CONTAINER printenv POSTGRES_DB) -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
        echo "✅ Расширение pgcrypto установлено"
    fi
else
    echo "❌ WARNING: Контейнер PostgreSQL не запущен"
    echo "   Установите pgcrypto вручную после запуска БД:"
    echo "   docker exec postgres-prod psql -U <user> -d <db> -c 'CREATE EXTENSION pgcrypto;'"
fi

# ==================== ИТОГОВАЯ ИНФОРМАЦИЯ ====================
echo ""
echo "========================================="
echo "✅ SECURITY SETUP COMPLETED"
echo "========================================="
echo ""
echo "Установленные компоненты:"
echo "  ✓ Fail2Ban - защита от brute-force"
echo "  ✓ ClamAV - антивирусная защита"
echo "  ✓ Backup script - автоматический backup"
echo "  ✓ pgcrypto - шифрование данных в БД"
echo ""
echo "Cron jobs:"
crontab -l 2>/dev/null || echo "  (нет задач)"
echo ""
echo "Следующие шаги:"
echo "  1. Проверьте статус сервисов:"
echo "     - fail2ban-client status"
echo "     - systemctl status clamav-daemon"
echo "     - ls -la /backups/"
echo ""
echo "  2. Настройте ELK Stack для централизованного логирования"
echo "     См: OAC-FREE-SOLUTIONS.md"
echo ""
echo "  3. Запустите OWASP ZAP scan:"
echo "     docker run -t owasp/zap2docker-stable zap-baseline.py \\"
echo "       -t https://api.spravka.novamedika.com"
echo ""
echo "========================================="
