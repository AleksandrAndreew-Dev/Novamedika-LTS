#!/bin/bash
# Удаление упоминаний стоимости/цен/бюджета из документов
set -e

cd "$(dirname "$0")/.."

echo "=== Удаление упоминаний стоимости из документов ==="
echo ""

# Функция для безопасного удаления строк по regex
remove_lines() {
    local file=$1
    local pattern=$2
    if [ -f "$file" ]; then
        # Удаляем строки соответствующие паттерну (используем perl для поддержки \p)
        perl -ne "print unless /$pattern/" "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
        echo "  ✓ Очищен $file (паттерн: $pattern)"
    fi
}

# 1. oac/guides/QUICK-START-SECURITY.md
echo "[1/8] oac/guides/QUICK-START-SECURITY.md"
remove_lines "oac/guides/QUICK-START-SECURITY.md" '\*\*Стоимость:\*\* \$0'
remove_lines "oac/guides/QUICK-START-SECURITY.md" '\*\*Экономия:\*\*'
remove_lines "oac/guides/QUICK-START-SECURITY.md" '\*\*Первый год:\*\*'
remove_lines "oac/guides/QUICK-START-SECURITY.md" '\*\*Последующие годы:\*\*'
remove_lines "oac/guides/QUICK-START-SECURITY.md" '\*\*Время выполнения:\*\*'

# 2. oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md
echo "[2/8] oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md"
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" 'Elastic Cloud.*\$'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '\*\*Ответ:\*\* Практически везде'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" 'Внешний penetration test раз в год:'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" 'Freelance DevOps инженеры'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" 'разов.*настройка всего стека'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '\$0 стоимость'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '\*\*Экономия:'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" 'Сравнение затрат'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '^\| (ИТОГО|\*\*ИТОГО)'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '^\| (Логирование|Backup|Антивирус|Мониторинг|Сканер|IDS|Шифрование|Pentest) \|'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS-CHEATSHEET.md" '^\* только внешний pentest'

# 3. oac/guides/OAC-FREE-SOLUTIONS.md
echo "[3/8] oac/guides/OAC-FREE-SOLUTIONS.md"
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" '\*\*Цель:\*\*'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'Платные решения \(\$'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" '^\*\*Стоимость:\*\*'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'PostgreSQL Enterprise Edition'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'AWS S3.*\$'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'Google Cloud Storage.*\$'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'Azure Blob Storage.*\$'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" '^\| .+ \| \$\d'
remove_lines "oac/guides/OAC-FREE-SOLUTIONS.md" 'ИТОГО'

# 4. oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md - удаляем раздел про экономику
echo "[4/8] oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md"
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" 'Сравнительная экономика: Open Source vs Коммерция'
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" 'TCO — Total Cost of Ownership'
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" '^\| .+ \| .+ \| \$\d'
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" '^\*\*Полный суверенитет:'
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" '^\*\*Экономию бюджета:'
remove_lines "oac/guides/OPENSOURCE-SECURITY-SOLUTIONS.md" '^\*\*Гибкость:'

# 5. oac/guides/ATTESTATION-OAC-GUIDE.md
echo "[5/8] oac/guides/ATTESTATION-OAC-GUIDE.md"
remove_lines "oac/guides/ATTESTATION-OAC-GUIDE.md" 'оплатить все расходы по проведению'
remove_lines "oac/guides/ATTESTATION-OAC-GUIDE.md" 'Сформирован бюджет на СЗИ'
remove_lines "oac/guides/ATTESTATION-OAC-GUIDE.md" 'Выбор несертифицированных СЗИ'
remove_lines "oac/guides/ATTESTATION-OAC-GUIDE.md" 'Фокус только на технике'

# 6. oac/README.md - раздел "💰 Бюджет проекта"
echo "[6/8] oac/README.md - раздел бюджет"
perl -0777 -ne 's/## 💰 Бюджет проекта\s*\n.*?(?=^## |\Z)//gs' oac/README.md > oac/README.md.tmp && mv oac/README.md.tmp oac/README.md
echo "  ✓ Удалён раздел 'Бюджет проекта'"

# 7. oac/planning/ - несколько файлов
echo "[7/8] oac/planning/*"
remove_lines "oac/planning/README.md" 'Единовременные затраты:'
remove_lines "oac/planning/README.md" 'Ежегодные затраты:'
remove_lines "oac/planning/README.md" 'Экономия vs платные решения'
remove_lines "oac/planning/README.md" '^\d+\. \*\*Бюджет\*\*'
remove_lines "oac/planning/README.md" 'Потрачено: \$'
remove_lines "oac/planning/README.md" 'Осталось: \$'
remove_lines "oac/planning/README.md" 'Отклонение:'
remove_lines "oac/planning/README.md" 'Контролировать бюджет'
remove_lines "oac/planning/README.md" '^\| Pentest \(внешний'
remove_lines "oac/planning/README.md" '^\| Время команды'
remove_lines "oac/planning/README.md" '^\| Поддержка инфраструктуры'
remove_lines "oac/planning/README.md" '^\| Доп. ресурсы'

# OAC-VISUAL-PROGRESS.md - удаляем раздел бюджета
perl -0777 -ne 's/## 💰 Бюджет\s*\n.*?(?=^## |\Z)//gs' oac/planning/OAC-VISUAL-PROGRESS.md > oac/planning/OAC-VISUAL-PROGRESS.md.tmp && mv oac/planning/OAC-VISUAL-PROGRESS.md.tmp oac/planning/OAC-VISUAL-PROGRESS.md
echo "  ✓ Удалён раздел 'Бюджет' из OAC-VISUAL-PROGRESS.md"

remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" '^\$0\s+\$5k\s+\$10k'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Стоимость каждого процента'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'План: \$'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Факт: \$'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Потрачено бюджета'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Первые 50%.*\$0'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Следующие 30%.*\$'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Последние 20%.*\$'
remove_lines "oac/planning/OAC-VISUAL-PROGRESS.md" 'Бюджетное соответствие'

remove_lines "oac/planning/oac-compliance-checklist.md" '^\- \[ \] \*\*Бюджет:\*\* \$'
remove_lines "oac/planning/oac-compliance-checklist.md" 'Бюджет'

# 8. oac/audits/README.md, oac/dop/, oac/docs/, docs/
echo "[8/8] oac/audits/, oac/dop/, oac/docs/, docs/"

# oac/audits/README.md
remove_lines "oac/audits/README.md" 'Бюджет: \$'
remove_lines "oac/audits/README.md" '^\| \*\*Бюджет'
remove_lines "oac/audits/README.md" 'уточнен'

# oac/dop/PRIKAZY-OTVETSTVENNYE-IB.md
remove_lines "oac/dop/PRIKAZY-OTVETSTVENNYE-IB.md" 'Планирование бюджета на средства защиты'

# oac/docs/14-personal-data-processing-architecture.md
remove_lines "oac/docs/14-personal-data-processing-architecture.md" 'Внешний аудит \(\$'

# oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" '\*\*Стоимость:\*\*'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Вариант B: Легковесное решение'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'за ресурсы'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" '^\- Стоимость: \$'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" '^\- Время: \d'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Вариант A: \$\d'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Вариант B: \$0,'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Минимальная стоимость:'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Рекомендуемая стоимость:'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" '^\| (Шифрование БД|Логирование \(Вариант|Pentest \(Вариант)'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Оценка трудозатрат'
remove_lines "oac/dop/OAC-COMPLIANCE-STATUS-REPORT.md" 'Открытые порты'

# docs/CONFIGURATION-SUMMARY.md
remove_lines "docs/CONFIGURATION-SUMMARY.md" '~\$60-90 USD'
remove_lines "docs/CONFIGURATION-SUMMARY.md" '\$60-90 USD'
remove_lines "docs/CONFIGURATION-SUMMARY.md" '\$\d+-\d+ USD'

# docs/AI-OPTIMIZATION-GUIDE.md
remove_lines "docs/AI-OPTIMIZATION-GUIDE.md" '~\$60-90 USD'
remove_lines "docs/AI-OPTIMIZATION-GUIDE.md" '\$60-90 USD'
remove_lines "docs/AI-OPTIMIZATION-GUIDE.md" '\$\d+-\d+ USD'

# docs/SECURITY-IMPLEMENTATION-GUIDE.md
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" '\*\*Стоимость:\*\*'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" 'Grafana Cloud Free Tier'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" '^\| (SIEM|Сканер уязвимостей|WAF|Антивирус) \|'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" '^\| \*\*Итого\*\*'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" '\*\*Фактические затраты'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" 'Серверные ресурсы: уже оплачены'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" 'Grafana Cloud: \$0'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" 'Итого: \$0/мес'
remove_lines "docs/SECURITY-IMPLEMENTATION-GUIDE.md" 'Open Source \+ Grafana'

echo ""
echo "=== Готово! ==="
echo ""
echo "Проверьте результат:"
echo "  grep -r '💰' oac/ docs/ --include='*.md'"
echo "  grep -rn '\$\d' oac/ docs/ --include='*.md' | head -20"
