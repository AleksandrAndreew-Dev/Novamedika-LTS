#!/bin/bash
# ============================================================================
# Скрипт управления ресурсами для запуска OpenVAS
# Оптимизация для сервера 4 CPU / 8 GB RAM
# ============================================================================

set -euo pipefail

OPENVAS_CONTAINER="openvas-temp"
MONITORING_SERVICES=("grafana-local" "loki" "promtail")

# Загрузка переменных окружения из .env файла (если существует)
if [ -f /opt/novamedika-prod/.env ]; then
    source /opt/novamedika-prod/.env
fi

# Использование пароля из .env или значение по умолчанию (только для backward compatibility)
OPENVAS_PASSWORD="${OPENVAS_PASSWORD:-OpenVASTempPass123!}"

usage() {
    echo "Использование: $0 {start-scanning|stop-scanning}"
    echo ""
    echo "Команды:"
    echo "  start-scanning  - Остановить мониторинг, запустить OpenVAS"
    echo "  stop-scanning   - Остановить OpenVAS, восстановить мониторинг"
    exit 1
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

start_scanning() {
    log "=== Начало подготовки к сканированию уязвимостей ==="
    
    # Проверка доступной памяти
    AVAILABLE_MEM=$(free -m | awk '/^Mem:/ {print $7}')
    log "Доступно памяти: ${AVAILABLE_MEM} MB"
    
    if [ "${AVAILABLE_MEM}" -lt 2000 ]; then
        log "⚠️ Недостаточно свободной памяти (< 2 GB)"
        log "Остановка сервисов мониторинга..."
        
        for service in "${MONITORING_SERVICES[@]}"; do
            if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
                log "Остановка ${service}..."
                docker stop "${service}" || true
            fi
        done
        
        sleep 5
    fi
    
    # Запуск OpenVAS
    log "Запуск контейнера OpenVAS..."
    docker run -d \
        --name "${OPENVAS_CONTAINER}" \
        --network novamedika2_backend-network \
        -e PASSWORD="${OPENVAS_PASSWORD}" \
        -v openvas-data:/data \
        --memory=3g \
        --cpus=2.0 \
        greenbone/gvm:stable || {
            log "❌ Ошибка запуска OpenVAS"
            exit 1
        }
    
    log "✅ OpenVAS запущен"
    log "🔐 Пароль GSA: ${OPENVAS_PASSWORD}"
    log "🌐 Доступ: http://<server-ip>:9392 (username: admin)"
    log "Ожидание инициализации (5 минут)..."
    sleep 300
    
    # Запуск сканирования backend
    log "Запуск сканирования backend-сервиса..."
    docker exec "${OPENVAS_CONTAINER}" gvm-cli socket \
        --xml "<start_scan><target><hosts>backend</hosts></target></start_scan>" || {
            log "⚠️ Ошибка запуска сканирования"
        }
    
    log "Сканирование запущено. Мониторинг прогресса..."
    log "Для просмотра статуса: docker logs ${OPENVAS_CONTAINER}"
    log "Для остановки: $0 stop-scanning"
}

stop_scanning() {
    log "=== Остановка сканирования и восстановление мониторинга ==="
    
    # Экспорт отчета перед остановкой
    if docker ps --format '{{.Names}}' | grep -q "^${OPENVAS_CONTAINER}$"; then
        log "Экспорт отчета OpenVAS..."
        REPORT_DATE=$(date +%Y%m%d)
        REPORT_FILE="/opt/reports/openvas/openvas-report-${REPORT_DATE}.pdf"
        
        mkdir -p /opt/reports/openvas
        
        docker exec "${OPENVAS_CONTAINER}" gvm-cli socket \
            --xml "<get_reports format_id='c1645568-627a-11e3-a660-406186ea4fc5'/>" \
            > "${REPORT_FILE}" 2>/dev/null || {
                log "⚠️ Ошибка экспорта отчета"
            }
        
        if [ -f "${REPORT_FILE}" ]; then
            log "✅ Отчет сохранен: ${REPORT_FILE}"
        fi
        
        # Остановка и удаление контейнера
        log "Остановка OpenVAS..."
        docker stop "${OPENVAS_CONTAINER}" || true
        docker rm "${OPENVAS_CONTAINER}" || true
        log "✅ OpenVAS остановлен"
    else
        log "⚠️ Контейнер OpenVAS не запущен"
    fi
    
    # Восстановление сервисов мониторинга
    log "Восстановление сервисов мониторинга..."
    for service in "${MONITORING_SERVICES[@]}"; do
        if ! docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            log "Запуск ${service}..."
            cd /app && docker-compose -f docker-compose.monitoring.yml up -d "${service}" || {
                log "⚠️ Ошибка запуска ${service}"
            }
        fi
    done
    
    log "✅ Все сервисы восстановлены"
}

# Основная логика
case "${1:-}" in
    start-scanning)
        start_scanning
        ;;
    stop-scanning)
        stop_scanning
        ;;
    *)
        usage
        ;;
esac
