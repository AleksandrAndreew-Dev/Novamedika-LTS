#!/bin/bash
# Script: backup.sh
# Description: Автоматическое резервное копирование БД и конфигураций NovaMedika2
# Usage: ./backup.sh или через cron: 0 2 * * * /usr/local/bin/backup.sh
# Requirements: Docker, gzip, tar

set -e  # Остановка при ошибке

# ==================== КОНФИГУРАЦИЯ ====================
BACKUP_DIR="/backups"
DB_BACKUP_DIR="$BACKUP_DIR/db"
CONFIG_BACKUP_DIR="$BACKUP_DIR/configs"
RETENTION_DAYS=365  # Хранить backup 1 год (требование ОАЦ)
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup.log"

# Имена контейнеров (должны совпадать с docker-compose)
POSTGRES_CONTAINER="postgres-prod"
PROJECT_DIR="/home/novamedika/novamedika2"  # Путь к проекту на сервере

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
    
    if ! docker ps --format '{{.Names}}' | grep -q "$POSTGRES_CONTAINER"; then
        log "❌ ERROR: Контейнер $POSTGRES_CONTAINER не запущен"
        exit 1
    fi
    
    log "✅ Требования выполнены"
}

create_backup_dirs() {
    log "Создание директорий для backup..."
    mkdir -p "$DB_BACKUP_DIR"
    mkdir -p "$CONFIG_BACKUP_DIR"
    log "✅ Директории созданы"
}

backup_database() {
    local BACKUP_FILE="$DB_BACKUP_DIR/db_$DATE.sql.gz"
    
    log "📦 Начало backup PostgreSQL..."
    
    # Получаем переменные окружения из контейнера
    local POSTGRES_USER=$(docker exec $POSTGRES_CONTAINER printenv POSTGRES_USER)
    local POSTGRES_DB=$(docker exec $POSTGRES_CONTAINER printenv POSTGRES_DB)
    
    if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
        log "❌ ERROR: Не удалось получить переменные окружения БД"
        exit 1
    fi
    
    log "   Пользователь: $POSTGRES_USER"
    log "   База данных: $POSTGRES_DB"
    
    # Создаем backup с компрессией
    if docker exec $POSTGRES_CONTAINER pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | \
       gzip > "$BACKUP_FILE"; then
        
        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "✅ Backup создан: $BACKUP_FILE ($SIZE)"
        
        # Проверка целостности
        if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
            log "✅ Целостность backup подтверждена"
        else
            log "❌ WARNING: Backup может быть поврежден!"
            rm -f "$BACKUP_FILE"
            exit 1
        fi
    else
        log "❌ ERROR: Ошибка создания backup БД"
        exit 1
    fi
}

backup_configs() {
    local BACKUP_FILE="$CONFIG_BACKUP_DIR/configs_$DATE.tar.gz"
    
    log "📦 Начало backup конфигураций..."
    
    cd "$PROJECT_DIR" || exit 1
    
    # Список файлов для backup
    local FILES_TO_BACKUP=(
        ".env"
        "docker-compose.traefik.prod.yml"
        "docker-compose.stable.yml"
        "traefic/acme.json"
    )
    
    # Проверяем существование файлов
    local EXISTING_FILES=()
    for file in "${FILES_TO_BACKUP[@]}"; do
        if [ -f "$file" ]; then
            EXISTING_FILES+=("$file")
        else
            log "   ⚠️  Файл не найден: $file"
        fi
    done
    
    if [ ${#EXISTING_FILES[@]} -eq 0 ]; then
        log "❌ WARNING: Нет файлов для backup конфигураций"
        return 0
    fi
    
    # Создаем архив
    if tar czf "$BACKUP_FILE" "${EXISTING_FILES[@]}" 2>/dev/null; then
        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log "✅ Backup конфигураций создан: $BACKUP_FILE ($SIZE)"
    else
        log "❌ ERROR: Ошибка создания backup конфигураций"
        exit 1
    fi
}

cleanup_old_backups() {
    log "🧹 Очистка старых backup (> $RETENTION_DAYS дней)..."
    
    local DB_DELETED=$(find "$DB_BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    local CONFIG_DELETED=$(find "$CONFIG_BACKUP_DIR" -name "configs_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    
    log "   Удалено backup БД: $DB_DELETED"
    log "   Удалено backup конфигов: $CONFIG_DELETED"
    log "✅ Очистка завершена"
}

show_summary() {
    log ""
    log "==================== SUMMARY ===================="
    log "Дата backup: $DATE"
    log ""
    log "Backup БД:"
    ls -lh "$DB_BACKUP_DIR"/db_*.sql.gz 2>/dev/null | tail -5 | while read line; do
        log "   $line"
    done
    log ""
    log "Backup конфигов:"
    ls -lh "$CONFIG_BACKUP_DIR"/configs_*.tar.gz 2>/dev/null | tail -5 | while read line; do
        log "   $line"
    done
    log ""
    log "Общий размер backup:"
    du -sh "$BACKUP_DIR" | while read line; do
        log "   $line"
    done
    log "=================================================="
}

# ==================== ОСНОВНАЯ ЛОГИКА ====================
main() {
    log "========================================="
    log "START: NovaMedika2 Backup Process"
    log "========================================="
    
    check_requirements
    create_backup_dirs
    backup_database
    backup_configs
    cleanup_old_backups
    show_summary
    
    log "========================================="
    log "SUCCESS: Backup completed"
    log "========================================="
}

# Запуск
main "$@"
