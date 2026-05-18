#!/bin/bash
# ============================================================================
# Ежегодный анализ эффективности системы защиты информации (СЗИ)
# Требование: Приказ ОАЦ №66 в редакции №259 (п.12)
# Запуск: 1 января каждого года в 00:00
# ============================================================================

set -euo pipefail

# Конфигурация
REPORT_DATE=$(date +%Y-%m-%d)
REPORT_DIR="/opt/reports/security-audit"
REPORT_FILE="${REPORT_DIR}/annual-security-review-${REPORT_DATE}.md"
LOGS_DIR="/var/log/novamedika2"

# Создание директории отчетов
mkdir -p "${REPORT_DIR}"

echo "=== Начало ежегодного анализа эффективности СЗИ ==="
echo "Дата отчета: ${REPORT_DATE}"
echo "Файл отчета: ${REPORT_FILE}"

# ============================================================================
# РАЗДЕЛ 1: АКТУАЛЬНОСТЬ ПОЛИТИК И РЕГЛАМЕНТОВ ИБ
# ============================================================================
echo "[1/7] Проверка актуальности политик ИБ..."

cat > "${REPORT_FILE}" << 'EOF'
# Ежегодный анализ эффективности системы защиты информации (СЗИ)

**Информационная система:** NovaMedika2  
**Дата анализа:** DATE_PLACEHOLDER  
**Ответственный за ИБ:** [ФИО]  
**Основание:** п.12 Приказа ОАЦ №66 в редакции Приказа №259 от 10.12.2024

---

## 1. АКТУАЛЬНОСТЬ ПОЛИТИК И РЕГЛАМЕНТОВ ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ

EOF

# Замена placeholder на реальную дату
sed -i "s/DATE_PLACEHOLDER/${REPORT_DATE}/g" "${REPORT_FILE}"

echo "" >> "${REPORT_FILE}"
echo "### 1.1. Статус документов по ИБ" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# Проверка даты последнего изменения документов
for doc in /app/oac/docs/*.md; do
    if [ -f "$doc" ]; then
        DOC_NAME=$(basename "$doc")
        LAST_MOD=$(stat -c %y "$doc" 2>/dev/null | cut -d' ' -f1 || echo "недоступно")
        FILE_SIZE=$(stat -c %s "$doc" 2>/dev/null || echo "0")
        
        # Определение статуса актуальности
        MOD_EPOCH=$(date -d "$LAST_MOD" +%s 2>/dev/null || echo "0")
        CURRENT_EPOCH=$(date +%s)
        DAYS_OLD=$(( (CURRENT_EPOCH - MOD_EPOCH) / 86400 ))
        
        if [ $DAYS_OLD -lt 365 ]; then
            STATUS="✅ Актуален"
        elif [ $DAYS_OLD -lt 730 ]; then
            STATUS="⚠️ Требует проверки"
        else
            STATUS="❌ Устарел"
        fi
        
        echo "- **${DOC_NAME}**: последнее изменение ${LAST_MOD} (${DAYS_OLD} дней назад) — ${STATUS}" >> "${REPORT_FILE}"
        echo "  - Размер файла: ${FILE_SIZE} байт" >> "${REPORT_FILE}"
    fi
done

echo "" >> "${REPORT_FILE}"

# ============================================================================
# РАЗДЕЛ 2: СТАТИСТИКА ИНЦИДЕНТОВ ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ
# ============================================================================
echo "[2/7] Анализ инцидентов ИБ за год..."

cat >> "${REPORT_FILE}" << 'EOF'
## 2. СТАТИСТИКА ИНЦИДЕНТОВ ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ

### 2.1. Общая статистика событий

EOF

# Подсчет событий из Docker логов
if command -v docker &> /dev/null; then
    ERROR_COUNT=$(docker logs backend-prod --since 365d 2>&1 | grep -ci "error\|critical\|alert" || echo "0")
    AUTH_FAIL_COUNT=$(docker logs backend-prod --since 365d 2>&1 | grep -ci "authentication failed\|unauthorized" || echo "0")
    
    echo "- Всего критических событий (ERROR/CRITICAL/ALERT): **${ERROR_COUNT}**" >> "${REPORT_FILE}"
    echo "- Неудачных попыток аутентификации: **${AUTH_FAIL_COUNT}**" >> "${REPORT_FILE}"
else
    echo "- Docker не установлен или контейнер недоступен" >> "${REPORT_FILE}"
fi

echo "" >> "${REPORT_FILE}"

# Анализ Fail2ban логов
if [ -f "/var/log/fail2ban.log" ]; then
    BAN_COUNT=$(grep -c "Ban " /var/log/fail2ban.log 2>/dev/null || echo "0")
    UNBAN_COUNT=$(grep -c "Unban " /var/log/fail2ban.log 2>/dev/null || echo "0")
    
    cat >> "${REPORT_FILE}" << EOF
### 2.2. Статистика Fail2ban

- Всего блокировок IP: **${BAN_COUNT}**
- Всего разблокировок: **${UNBAN_COUNT}**
- Активных банов: **$((BAN_COUNT - UNBAN_COUNT))**

EOF
else
    echo "### 2.2. Статистика Fail2ban" >> "${REPORT_FILE}"
    echo "- Логи Fail2ban недоступны" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
fi

# ============================================================================
# РАЗДЕЛ 3: СТАТУС ОБНОВЛЕНИЙ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ
# ============================================================================
echo "[3/7] Проверка обновлений ПО..."

cat >> "${REPORT_FILE}" << 'EOF'
## 3. СТАТУС ОБНОВЛЕНИЙ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ

### 3.1. Версии Docker образов

EOF

if command -v docker &> /dev/null; then
    docker images --format "{{.Repository}}:{{.Tag}} | {{.CreatedAt}} | {{.Size}}" >> "${REPORT_FILE}" 2>/dev/null || echo "- Невозможно получить информацию об образах" >> "${REPORT_FILE}"
else
    echo "- Docker не установлен" >> "${REPORT_FILE}"
fi

echo "" >> "${REPORT_FILE}"

# Проверка зависимостей Python
if [ -f "/app/backend/requirements.txt" ]; then
    echo "### 3.2. Python зависимости (backend)" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    echo "\`\`\`" >> "${REPORT_FILE}"
    head -20 /app/backend/requirements.txt >> "${REPORT_FILE}" 2>/dev/null || echo "Файл requirements.txt недоступен" >> "${REPORT_FILE}"
    echo "\`\`\`" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
fi

# ============================================================================
# РАЗДЕЛ 4: РЕЗЕРВНОЕ КОПИРОВАНИЕ
# ============================================================================
echo "[4/7] Проверка резервного копирования..."

cat >> "${REPORT_FILE}" << 'EOF'
## 4. РЕЗЕРВНОЕ КОПИРОВАНИЕ И ВОССТАНОВЛЕНИЕ ДАННЫХ

### 4.1. Последние резервные копии PostgreSQL

EOF

BACKUP_DIR="/backups"
if [ -d "${BACKUP_DIR}" ]; then
    echo "Директория бэкапов: \`${BACKUP_DIR}\`" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | tail -10 >> "${REPORT_FILE}" || echo "- Резервные копии не найдены" >> "${REPORT_FILE}"
    
    # Проверка целостности последнего бэкапа
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)
    if [ -n "${LATEST_BACKUP}" ] && command -v sha256sum &> /dev/null; then
        CHECKSUM=$(sha256sum "${LATEST_BACKUP}" | awk '{print $1}')
        echo "" >> "${REPORT_FILE}"
        echo "**SHA-256 последнего бэкапа:** \`${CHECKSUM}\`" >> "${REPORT_FILE}"
    fi
else
    echo "- Директория резервных копий не найдена: ${BACKUP_DIR}" >> "${REPORT_FILE}"
fi

echo "" >> "${REPORT_FILE}"

# ============================================================================
# РАЗДЕЛ 5: СКАНИРОВАНИЕ УЯЗВИМОСТЕЙ (OpenVAS)
# ============================================================================
echo "[5/7] Анализ результатов сканирования уязвимостей..."

cat >> "${REPORT_FILE}" << 'EOF'
## 5. РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ УЯЗВИМОСТЕЙ (OpenVAS/Greenbone)

### 5.1. Последние отчеты OpenVAS

EOF

OPENVAS_REPORTS_DIR="/opt/reports/openvas"
if [ -d "${OPENVAS_REPORTS_DIR}" ]; then
    REPORT_COUNT=$(ls -1 "${OPENVAS_REPORTS_DIR}"/*.pdf 2>/dev/null | wc -l || echo "0")
    echo "Всего отчетов: **${REPORT_COUNT}**" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    
    ls -lh "${OPENVAS_REPORTS_DIR}"/*.pdf 2>/dev/null | tail -5 >> "${REPORT_FILE}" || echo "- Отчеты не найдены" >> "${REPORT_FILE}"
else
    echo "- Директория отчетов OpenVAS не найдена" >> "${REPORT_FILE}"
    echo "- Рекомендуется настроить регулярное сканирование уязвимостей" >> "${REPORT_FILE}"
fi

echo "" >> "${REPORT_FILE}"

# ============================================================================
# РАЗДЕЛ 6: МОНИТОРИНГ И ЛОГИРОВАНИЕ
# ============================================================================
echo "[6/7] Проверка системы мониторинга..."

cat >> "${REPORT_FILE}" << 'EOF'
## 6. МОНИТОРИНГ И ЦЕНТРАЛИЗОВАННОЕ ЛОГИРОВАНИЕ

### 6.1. Статус компонентов мониторинга

EOF

# Проверка Loki
if curl -s http://localhost:3100/ready &>/dev/null; then
    echo "- **Loki**: ✅ Работает (http://localhost:3100)" >> "${REPORT_FILE}"
else
    echo "- **Loki**: ❌ Недоступен" >> "${REPORT_FILE}"
fi

# Проверка Grafana
if curl -s http://localhost:3000/api/health &>/dev/null; then
    echo "- **Grafana**: ✅ Работает (http://localhost:3000)" >> "${REPORT_FILE}"
else
    echo "- **Grafana**: ❌ Недоступен" >> "${REPORT_FILE}"
fi

# Проверка Promtail
if pgrep -x "promtail" > /dev/null; then
    echo "- **Promtail**: ✅ Работает" >> "${REPORT_FILE}"
else
    echo "- **Promtail**: ❌ Не запущен" >> "${REPORT_FILE}"
fi

echo "" >> "${REPORT_FILE}"

# Объем хранимых логов
LOKI_DATA_DIR="/var/lib/docker/volumes/loki-data"
if [ -d "${LOKI_DATA_DIR}" ]; then
    LOG_SIZE=$(du -sh "${LOKI_DATA_DIR}" 2>/dev/null | awk '{print $1}' || echo "неизвестно")
    echo "### 6.2. Объем хранимых логов" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    echo "- Loki data directory: **${LOG_SIZE}**" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
fi

# ============================================================================
# РАЗДЕЛ 7: РЕКОМЕНДАЦИИ И ПЛАН МЕРОПРИЯТИЙ
# ============================================================================
echo "[7/7] Формирование рекомендаций..."

cat >> "${REPORT_FILE}" << 'EOF'
## 7. РЕКОМЕНДАЦИИ И ПЛАН МЕРОПРИЯТИЙ НА СЛЕДУЮЩИЙ ГОД

### 7.1. Критические задачи (выполнить в течение 1 квартала)

- [ ] Обновить все политики и регламенты ИБ (если помечены как "❌ Устарел")
- [ ] Провести внеплановое сканирование уязвимостей через OpenVAS
- [ ] Проверить работоспособность резервного копирования (тестовое восстановление)
- [ ] Обновить сигнатуры антивируса ClamAV и правила ModSecurity WAF

### 7.2. Плановые задачи (выполнить в течение года)

- [ ] Провести обучение персонала по ИБ (инструктаж + фишинговые учения)
- [ ] Выполнить тестирование на проникновение (pentest)
- [ ] Актуализировать структурные и логические схемы ИС
- [ ] Провести аудит соответствия требованиям ОАЦ (внутренний)

### 7.3. Долгосрочные улучшения

- [ ] Рассмотреть возможность внедрения полноценной SIEM системы (Wazuh) при расширении инфраструктуры
- [ ] Внедрить систему управления инцидентами (incident management)
- [ ] Разработать план реагирования на инциденты ИБ (incident response plan)
- [ ] Автоматизировать процесс уведомления НЦЗПД при утечках ПД

---

## ЗАКЛЮЧЕНИЕ

Настоящий отчет составлен в соответствии с требованием п.12 Приказа ОАЦ №66 
в редакции Приказа №259 от 10.12.2024 г. о необходимости ежегодного анализа 
эффективности системы защиты информации.

Отчет утвержден:

**Ответственный за ИБ:** _______________ / [ФИО]  
**Дата утверждения:** «___» ____________ 20__ г.

---

*Документ сгенерирован автоматически: TIMESTAMP_PLACEHOLDER*
EOF

# Замена timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
sed -i "s/TIMESTAMP_PLACEHOLDER/${TIMESTAMP}/g" "${REPORT_FILE}"

echo ""
echo "=== Анализ завершен ==="
echo "Отчет сохранен: ${REPORT_FILE}"
echo ""

# Отправка отчета по email (если настроен mail)
if command -v mail &> /dev/null; then
    echo "Отправка отчета на admin@novamedika.com..."
    mail -s "Ежегодный отчет СЗИ NovaMedika2 - ${REPORT_DATE}" admin@novamedika.com < "${REPORT_FILE}"
    echo "Отчет отправлен."
else
    echo "⚠️ Команда 'mail' не найдена. Отправка по email пропущена."
    echo "   Пожалуйста, отправьте отчет вручную: ${REPORT_FILE}"
fi

echo ""
echo "=== Конец скрипта ==="
