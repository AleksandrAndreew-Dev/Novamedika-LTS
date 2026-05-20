#!/bin/bash
# Script: emergency-disk-cleanup.sh
# Description: Экстренная очистка дискового пространства на production сервере
# Usage: sudo ./emergency-disk-cleanup.sh
# WARNING: Этот скрипт удаляет данные! Используйте с осторожностью.

set -e

echo "========================================="
echo "⚠️  EMERGENCY DISK CLEANUP"
echo "========================================="
echo ""
echo "Текущее состояние диска:"
df -h /
echo ""

# ==================== ШАГ 1: Docker cleanup ====================
echo "🐳 Шаг 1: Очистка Docker (безопасная)..."
echo ""

# 1.1 Удалить stopped containers
echo "Удаление остановленных контейнеров..."
STOPPED=$(docker ps -aq --filter "status=exited" | wc -l)
if [ "$STOPPED" -gt 0 ]; then
    docker container prune -f
    echo "✅ Удалено $STOPPED остановленных контейнеров"
else
    echo "ℹ️  Нет остановленных контейнеров"
fi
echo ""

# 1.2 Удалить unused images старше 7 дней
echo "Удаление неиспользуемых образов старше 7 дней..."
docker image prune -a --force --filter "until=168h" || true
echo "✅ Unused images удалены"
echo ""

# 1.3 Удалить build cache
echo "Очистка build cache..."
docker builder prune --force || true
echo "✅ Build cache очищен"
echo ""

# 1.4 Показать статистику
echo "Docker system df после очистки:"
docker system df
echo ""

# ==================== ШАГ 2: Очистка системных логов ====================
echo "📋 Шаг 2: Очистка системных логов..."

# Очистить journal logs старше 3 дней
if command -v journalctl &> /dev/null; then
    echo "Очистка journal logs старше 3 дней..."
    journalctl --vacuum-time=3d 2>/dev/null || true
    echo "✅ Journal logs очищены"
fi
echo ""

# ==================== ШАГ 3: Поиск больших файлов ====================
echo "🔍 Шаг 3: Поиск больших файлов (>100MB) в /var/log..."
find /var/log -type f -size +100M -exec ls -lh {} \; 2>/dev/null | head -10 || echo "  Большие файлы не найдены"
echo ""

# ==================== ШАГ 4: Очистка tmp ====================
echo "🗑️  Шаг 4: Очистка временных файлов..."
if [ -d /tmp ]; then
    find /tmp -type f -atime +7 -delete 2>/dev/null || true
    echo "✅ Временные файлы старше 7 дней удалены"
fi
echo ""

# ==================== ШАГ 5: Проверка результата ====================
echo "========================================="
echo "📊 РЕЗУЛЬТАТ ОЧИСТКИ"
echo "========================================="
echo ""
echo "Состояние диска после очистки:"
df -h /
echo ""

USED_PERCENT=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
echo "Использовано: ${USED_PERCENT}%"
echo ""

if [ "$USED_PERCENT" -lt 80 ]; then
    echo "✅ Отлично! Дисковое пространство в норме (<80%)"
elif [ "$USED_PERCENT" -lt 90 ]; then
    echo "⚠️  WARNING: Диск заполнен на ${USED_PERCENT}%. Рекомендуется настроить remote backup и увеличить диск."
else
    echo "❌ CRITICAL: Диск заполнен на ${USED_PERCENT}%! Требуется немедленное вмешательство!"
    echo "   Рекомендации:"
    echo "   1. Увеличить диск до 50-100GB"
    echo "   2. Настроить rotation для Loki/Prometheus"
    echo "   3. Перенести бэкапы на external storage"
fi
echo ""

# ==================== ШАГ 6: Рекомендации ====================
echo "💡 РЕКОМЕНДАЦИИ:"
echo ""
echo "1. Настроить retention policy для Loki:"
echo "   Редактировать: ./config/loki-config.yaml"
echo "   Добавить: limits_config.retention_period: 395d"
echo ""
echo "2. Настроить retention для Prometheus (уже настроено на 395 дней):"
echo "   Проверить: docker-compose.traefik.prod.yml"
echo ""
echo "3. Настроить remote backup (S3/Yandex Cloud) для хранения бэкапов"
echo ""
echo "4. Мониторить disk space регулярно:"
echo "   df -h /opt/novamedika-prod"
echo "   docker system df"
echo ""
echo "5. Рассмотреть увеличение диска до 50-100GB"
echo ""
