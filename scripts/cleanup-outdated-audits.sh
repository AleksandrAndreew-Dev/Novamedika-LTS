#!/bin/bash
# Script: cleanup-outdated-audits.sh
# Description: Быстрая очистка устаревших документов аудита ОАЦ (без архивации)
# Usage: ./cleanup-outdated-audits.sh [--dry-run] [--force]
# 
# Опции:
#   --dry-run  Показать что будет удалено, но не удалять
#   --force    Не запрашивать подтверждение
#
# Дата: 4 мая 2026 г.

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Проверка что мы в правильной директории
if [ ! -f "oac/audits/README.md" ]; then
    echo -e "${RED}❌ ERROR: Запустите скрипт из корня проекта Novamedika2${NC}"
    exit 1
fi

AUDITS_DIR="oac/audits"

# Флаги
DRY_RUN=false
FORCE=false

# Парсинг аргументов
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $arg${NC}"
            echo "Usage: $0 [--dry-run] [--force]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Очистка устаревших документов аудита ОАЦ${NC}"
echo -e "${BLUE}  Дата: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Список файлов для удаления (дубликаты и устаревшие)
FILES_TO_DELETE=(
    "$AUDITS_DIR/oac-audit.md"
    "$AUDITS_DIR/oac-audit-summary.md"
    "$AUDITS_DIR/SERVER-LOGS-AUDIT-2026-04-21.md"
    "$AUDITS_DIR/SERVER-LOGS-AUDIT-2026-04-21-UPDATE2.md"
    "$AUDITS_DIR/SERVER-LOGS-AUDIT-2026-04-21-FINAL.md"
    "$AUDITS_DIR/PRIVACY-POLICY-AUDIT.md"
    "$AUDITS_DIR/OAC-ENCRYPTION-ANALYSIS.md"
    "$AUDITS_DIR/EXTERNAL-LINKS-ANALYSIS.md"
)

# Проверка существования файлов
echo -e "${YELLOW}📋 Проверка файлов...${NC}"
echo ""

MISSING_FILES=()
for file in "${FILES_TO_DELETE[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Следующие файлы не найдены (возможно уже удалены):${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo -e "   - $file"
    done
    echo ""
fi

# Вывод плана действий
echo -e "${RED}🗑️  Будут УДАЛЕНЫ следующие файлы (без архивации):${NC}"
echo ""

TOTAL_SIZE=0
DELETE_COUNT=0

for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(du -h "$file" | cut -f1)
        SIZE_BYTES=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        TOTAL_SIZE=$((TOTAL_SIZE + SIZE_BYTES))
        DELETE_COUNT=$((DELETE_COUNT + 1))
        echo -e "   ❌ $file (${SIZE})"
    fi
done

echo ""

TOTAL_SIZE_MB=$(echo "scale=2; $TOTAL_SIZE / 1024 / 1024" | bc 2>/dev/null || echo "N/A")

echo -e "${BLUE}💾 Освобождаемое место: ~${TOTAL_SIZE_MB} MB${NC}"
echo -e "${BLUE}📊 Количество файлов к удалению: ${DELETE_COUNT}${NC}"
echo ""

# Dry run режим
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  DRY RUN MODE - никаких изменений не будет внесено${NC}"
    echo ""
    echo -e "${GREEN}✅ Для реального выполнения запустите:${NC}"
    echo -e "   bash scripts/cleanup-outdated-audits.sh"
    echo ""
    exit 0
fi

# Запрос подтверждения
if [ "$FORCE" = false ]; then
    echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Это действие необратимо!${NC}"
    echo -e "${YELLOW}   - ${DELETE_COUNT} файлов будут удалены БЕЗ ВОЗМОЖНОСТИ ВОССТАНОВЛЕНИЯ${NC}"
    echo -e "${YELLOW}   - Архивация НЕ выполняется${NC}"
    echo ""
    read -p "Продолжить? (y/n): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Операция отменена пользователем${NC}"
        exit 0
    fi
fi

# Удаление файлов
echo -e "${RED}🗑️  Удаление устаревших файлов...${NC}"
DELETED_COUNT=0
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        rm -v "$file"
        DELETED_COUNT=$((DELETED_COUNT + 1))
        echo -e "   ✅ Удален: $file"
    else
        echo -e "   ⚠️  Пропущен (не найден): $file"
    fi
done
echo ""

# Итоговый отчет
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ ОПЕРАЦИЯ ЗАВЕРШЕНА${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "📊 Статистика:"
echo -e "   - Удалено файлов: ${DELETED_COUNT}"
echo -e "   - Освобождено места: ~${TOTAL_SIZE_MB} MB"
echo ""
echo -e "${GREEN}✅ Актуальные документы оставлены:${NC}"
echo -e "   - OAC-COMPLIANCE-AUDIT-2026-05-04.md ⭐"
echo -e "   - OAC-COMPLIANCE-AUDIT-SUMMARY-EN-2026-05-04.md ⭐"
echo -e "   - OAC-COMPLIANCE-ACTION-CHECKLIST.md ⭐"
echo -e "   - OAC-COMPLIANCE-PROGRESS-TRACKER.md ⭐"
echo -e "   - README.md (обновлен)"
echo ""
echo -e "${BLUE}Следующие шаги:${NC}"
echo -e "1. Проверьте результат: ls -la $AUDITS_DIR/"
echo -e "2. Закоммитьте изменения: git add oac/audits/ && git commit -m 'docs: remove outdated audit documents'"
echo ""
