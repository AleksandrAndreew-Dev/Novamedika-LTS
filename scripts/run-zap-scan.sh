#!/bin/bash
# Script: run-zap-scan.sh
# Description: Запуск сканирования уязвимостей с помощью OWASP ZAP
# Usage: ./run-zap-scan.sh [baseline|full|api]
# Requirements: Docker

set -e

# ==================== КОНФИГУРАЦИЯ ====================
TARGET_API="https://api.spravka.novamedika.com"
TARGET_WEB="https://spravka.novamedika.com"
REPORT_DIR="./zap-reports"
DATE=$(date +%Y%m%d_%H%M%S)

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== ФУНКЦИИ ====================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_report_dir() {
    mkdir -p "$REPORT_DIR"
    log_info "Директория для отчетов: $REPORT_DIR"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен!"
        exit 1
    fi
    
    # Pull latest ZAP image
    log_info "Обновление образа OWASP ZAP..."
    docker pull owasp/zap2docker-stable
}

scan_baseline() {
    local REPORT_FILE="$REPORT_DIR/baseline_$DATE.html"
    
    log_info "Запуск baseline scan (быстрое сканирование)..."
    log_info "Цель: $TARGET_API"
    
    docker run -t --rm \
        -v $(pwd)/$REPORT_DIR:/zap/wrk/:rw \
        owasp/zap2docker-stable zap-baseline.py \
        -t "$TARGET_API" \
        -r "baseline_$DATE.html" \
        -I  # Игнорировать warnings
    
    log_info "Отчет сохранен: $REPORT_FILE"
    echo ""
    log_info "Откройте отчет в браузере:"
    echo "file://$(pwd)/$REPORT_FILE"
}

scan_full() {
    local REPORT_FILE="$REPORT_DIR/full_$DATE.html"
    
    log_info "Запуск full scan (полное сканирование)..."
    log_info "Цель: $TARGET_WEB"
    log_warn "Внимание: Это может занять 30-60 минут!"
    
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Сканирование отменено"
        exit 0
    fi
    
    docker run -t --rm \
        -v $(pwd)/$REPORT_DIR:/zap/wrk/:rw \
        owasp/zap2docker-stable zap-full-scan.py \
        -t "$TARGET_WEB" \
        -r "full_$DATE.html" \
        -I  # Игнорировать warnings
    
    log_info "Отчет сохранен: $REPORT_FILE"
    echo ""
    log_info "Откройте отчет в браузере:"
    echo "file://$(pwd)/$REPORT_FILE"
}

scan_api() {
    local OPENAPI_URL="$TARGET_API/openapi.json"
    local REPORT_FILE="$REPORT_DIR/api_$DATE.html"
    
    log_info "Запуск API scan (сканирование REST API)..."
    log_info "OpenAPI spec: $OPENAPI_URL"
    
    docker run -t --rm \
        -v $(pwd)/$REPORT_DIR:/zap/wrk/:rw \
        owasp/zap2docker-stable zap-api-scan.py \
        -t "$OPENAPI_URL" \
        -f openapi \
        -r "api_$DATE.html" \
        -I
    
    log_info "Отчет сохранен: $REPORT_FILE"
    echo ""
    log_info "Откройте отчет в браузере:"
    echo "file://$(pwd)/$REPORT_FILE"
}

show_summary() {
    echo ""
    log_info "==================== SCAN SUMMARY ===================="
    log_info "Дата сканирования: $DATE"
    log_info "Отчеты сохранены в: $REPORT_DIR"
    echo ""
    log_info "Последние отчеты:"
    ls -lht "$REPORT_DIR"/*.html 2>/dev/null | head -5 || echo "  Нет отчетов"
    echo ""
    log_info "Рекомендации:"
    echo "  1. Откройте HTML отчет в браузере"
    echo "  2. Изучите найденные уязвимости по уровням риска"
    echo "  3. Исправьте критические и высокие уязвимости"
    echo "  4. Запустите повторное сканирование после исправлений"
    echo ""
    log_info "Автоматизация в CI/CD:"
    echo "  Добавьте в .github/workflows/security-scan.yml"
    echo "=========================================================="
}

# ==================== ОСНОВНАЯ ЛОГИКА ====================
main() {
    echo "========================================="
    echo "OWASP ZAP Security Scanner"
    echo "========================================="
    echo ""
    
    create_report_dir
    check_docker
    
    SCAN_TYPE="${1:-baseline}"
    
    case $SCAN_TYPE in
        baseline)
            scan_baseline
            ;;
        full)
            scan_full
            ;;
        api)
            scan_api
            ;;
        all)
            scan_baseline
            echo ""
            scan_api
            echo ""
            log_warn "Full scan не запущен (требует подтверждения)"
            log_warn "Запустите вручную: ./run-zap-scan.sh full"
            ;;
        *)
            echo "Использование: $0 [baseline|full|api|all]"
            echo ""
            echo "Типы сканирования:"
            echo "  baseline - Быстрое сканирование (5-10 мин)"
            echo "  full     - Полное сканирование (30-60 мин)"
            echo "  api      - Сканирование REST API через OpenAPI"
            echo "  all      - Baseline + API (рекомендуется)"
            echo ""
            echo "Примеры:"
            echo "  $0 baseline  # Быстрая проверка"
            echo "  $0 all       # Рекомендуемый вариант"
            exit 1
            ;;
    esac
    
    show_summary
}

# Запуск
main "$@"
