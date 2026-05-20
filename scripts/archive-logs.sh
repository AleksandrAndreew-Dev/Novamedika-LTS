#!/bin/bash
# Script: archive-logs.sh
# Description: Архивирование логов Docker контейнеров NovaMedika2
# Usage: Запускается через cron каждые 6 часов: 0 */6 * * * /usr/local/bin/archive-logs.sh
# Requirements: Docker, gzip

set -e  # Остановка при ошибке

# ==================== КОНФИГУРАЦИЯ ====================
BACKUP_DIR="/backups"
LOG_ARCHIVE_DIR="$BACKUP_DIR/logs"
RETENTION_DAYS=395  # Хранить архивы логов >1 года (требование ОАЦ)
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/archive-logs.log"

# Список контейнеров для архивирования
CONTAINERS=(
    "backend-prod"
    "frontend-prod"
    "postgres-prod"
    "redis-prod"
    "traefik-prod"
    "celery-worker"
    "loki"
    "promtail"
    "prometheus"
)

# ==================== ФУНКЦИИ ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    log "Проверка требований..."
    
    if ! command -v docker &> /dev/null; then
        log "❌ ERROR: Docker не установлен"
        exit 1
    fi
    
    log "✅ Требования выполнены"
}

create_backup_dirs() {
    log "Создание директорий для архивов логов..."
    mkdir -p "$LOG_ARCHIVE_DIR"
    log "✅ Директории созданы"
}

archive_container_logs() {
    local container=$1
    local ARCHIVE_FILE="$LOG_ARCHIVE_DIR/logs_${container}_${DATE}.gz"
    
    # Проверяем, запущен ли контейнер
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log "   ⚠️  Контейнер $container не запущен, пропускаем"
        return 0
    fi
    
    log "   📦 Архивирование логов контейнера $container..."
    
    # Получаем последние 10000 строк лога и сжимаем
    if docker logs --tail 10000 "$container" 2>&1 | gzip > "$ARCHIVE_FILE"; then
        local SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)
        log "   ✅ Архив создан: $ARCHIVE_FILE ($SIZE)"
        
        # Проверка целостности
        if gunzip -t "$ARCHIVE_FILE" 2>/dev/null; then
            log "   ✅ Целостность архива подтверждена"
        else
            log "   ❌ WARNING: Архив может быть поврежден!"
            rm -f "$ARCHIVE_FILE"
            return 1
        fi
    else
        log "   ❌ ERROR: Ошибка архивирования логов $container"
        rm -f "$ARCHIVE_FILE"
        return 1
    fi
}

cleanup_old_archives() {
    log "🧹 Очистка старых архивов логов (> $RETENTION_DAYS дней)..."
    
    local DELETED=$(find "$LOG_ARCHIVE_DIR" -name "logs_*.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    log "   Удалено старых архивов: $DELETED"
    log "✅ Очистка завершена"
}

show_summary() {
    log ""
    log "==================== SUMMARY ===================="
    log "Дата архивирования: $DATE"
    log ""
    log "Последние архивы логов:"
    ls -lh "$LOG_ARCHIVE_DIR"/logs_*.gz 2>/dev/null | tail -10 | while read line; do
        log "   $line"
    done
    log ""
    log "Общий размер архивов:"
    du -sh "$LOG_ARCHIVE_DIR" | while read line; do
        log "   $line"
    done
    log "=================================================="
}

# ==================== ОСНОВНАЯ ЛОГИКА ====================
main() {
    log "========================================="
    log "START: NovaMedika2 Log Archiving Process"
    log "========================================="
    
    check_requirements
    create_backup_dirs
    
    local SUCCESS_COUNT=0
    local FAIL_COUNT=0
    
    for container in "${CONTAINERS[@]}"; do
        if archive_container_logs "$container"; then
            ((SUCCESS_COUNT++))
        else
            ((FAIL_COUNT++))
        fi
    done
    
    cleanup_old_archives
    show_summary
    
    log ""
    log "Результат: Успешно=$SUCCESS_COUNT, Ошибки=$FAIL_COUNT"
    
    if [ $FAIL_COUNT -gt 0 ]; then
        log "⚠️  WARNING: Некоторые контейнеры не удалось заархивировать"
    fi
    
    log "========================================="
    log "SUCCESS: Log archiving completed"
    log "========================================="
}

# Запуск
main "$@"
