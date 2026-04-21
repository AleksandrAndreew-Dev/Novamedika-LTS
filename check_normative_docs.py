#!/usr/bin/env python3
"""
Скрипт проверки наличия нормативных документов для проекта NovaMedika2
Проверяет наличие всех необходимых законов, указов и приказов
"""

import os
from pathlib import Path
from colorama import init, Fore, Style

# Инициализация colorama для Windows
init(autoreset=True)

# Базовый путь к проекту
BASE_DIR = Path(__file__).parent
ORIGIN_DOCS = BASE_DIR / "origin-docs"
OAC_DIR = BASE_DIR / "oac"

# Список необходимых документов
REQUIRED_DOCUMENTS = [
    {
        "name": "Закон РБ № 99-З 'О защите персональных данных'",
        "path": ORIGIN_DOCS / "zakon 99-3.pdf",
        "critical": True,
        "category": "Закон"
    },
    {
        "name": "Указ Президента РБ № 449",
        "path": ORIGIN_DOCS / "ukaz-449.pdf",
        "critical": True,
        "category": "Указ"
    },
    {
        "name": "Приказ ОАЦ № 66 (текстовая версия)",
        "path": OAC_DIR / "oac.md",
        "critical": True,
        "category": "Приказ ОАЦ"
    },
    {
        "name": "Приказ ОАЦ № 195 (PDF оригинал)",
        "path": ORIGIN_DOCS / "2021-195.pdf",
        "critical": True,
        "category": "Приказ ОАЦ"
    },
    {
        "name": "Приказ ОАЦ № 195 (альтернативная версия)",
        "path": ORIGIN_DOCS / "195-vpdf.pdf",
        "critical": False,
        "category": "Приказ ОАЦ"
    },
    {
        "name": "Чек-лист проверок операторов ПД",
        "path": ORIGIN_DOCS / "Chek_list_po_provedeniju_proverok_operatorov.docx",
        "critical": False,
        "category": "Вспомогательный"
    }
]

# Документы compliance проекта
COMPLIANCE_DOCS = [
    "01-act-class-3in.md",
    "02-structural-schema.md",
    "03-logical-schema.md",
    "04-privacy-policy.md",
    "05-infosec-policy.md",
    "06-tech-spec.md",
    "07-ib-monitoring-reglament.md",
    "08-backup-reglament.md",
    "09-data-retention-reglament.md",
    "10-encryption-policy.md",
    "11-antivirus-reglament.md",
    "12-ids-ips-reglament.md",
    "13-vuln-scan-reglament.md"
]

def check_file_exists(filepath):
    """Проверяет существование файла и возвращает размер"""
    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        return True, size_mb
    return False, 0

def print_header(text):
    """Выводит заголовок"""
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(80)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

def print_section(text):
    """Выводит раздел"""
    print(f"\n{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─'*80}{Style.RESET_ALL}\n")

def main():
    print_header("ПРОВЕРКА НАЛИЧИЯ НОРМАТИВНЫХ ДОКУМЕНТОВ\nNovaMedika2 Project")
    
    # Проверка нормативных документов
    print_section("1. НОРМАТИВНЫЕ ДОКУМЕНТЫ (Законы, Указы, Приказы)")
    
    present_count = 0
    missing_critical = []
    
    for doc in REQUIRED_DOCUMENTS:
        exists, size_mb = check_file_exists(doc["path"])
        
        if exists:
            present_count += 1
            status = f"{Fore.GREEN}✅ ЕСТЬ{Style.RESET_ALL}"
            size_info = f"({size_mb:.2f} MB)"
        else:
            if doc["critical"]:
                status = f"{Fore.RED}❌ ОТСУТСТВУЕТ (КРИТИЧНО){Style.RESET_ALL}"
                missing_critical.append(doc["name"])
            else:
                status = f"{Fore.YELLOW}⚠️  ОТСУТСТВУЕТ{Style.RESET_ALL}"
            size_info = ""
        
        print(f"{status:40} {doc['name']}")
        print(f"{'':40} Путь: {doc['path'].relative_to(BASE_DIR)} {size_info}")
        print()
    
    # Проверка документов compliance
    print_section("2. ДОКУМЕНТЫ COMPLIANCE ПРОЕКТА (oac/docs/)")
    
    docs_dir = OAC_DIR / "docs"
    compliance_present = 0
    
    for doc_name in COMPLIANCE_DOCS:
        doc_path = docs_dir / doc_name
        exists, size_kb = check_file_exists(doc_path)
        
        if exists:
            compliance_present += 1
            status = f"{Fore.GREEN}✅{Style.RESET_ALL}"
            size_info = f"({size_kb*1024:.1f} KB)"
        else:
            status = f"{Fore.RED}❌{Style.RESET_ALL}"
            size_info = ""
        
        print(f"{status} {doc_name:40} {size_info}")
    
    # Сводная статистика
    print_section("3. СВОДНАЯ СТАТИСТИКА")
    
    total_normative = len(REQUIRED_DOCUMENTS)
    normative_percent = (present_count / total_normative) * 100
    
    total_compliance = len(COMPLIANCE_DOCS)
    compliance_percent = (compliance_present / total_compliance) * 100
    
    print(f"{Fore.CYAN}Нормативные документы:{Style.RESET_ALL}")
    print(f"  Найдено: {Fore.GREEN}{present_count}{Style.RESET_ALL} из {total_normative} ({normative_percent:.0f}%)")
    
    print(f"\n{Fore.CYAN}Документы compliance:{Style.RESET_ALL}")
    print(f"  Создано: {Fore.GREEN}{compliance_present}{Style.RESET_ALL} из {total_compliance} ({compliance_percent:.0f}%)")
    
    # Критические проблемы
    if missing_critical:
        print(f"\n{Fore.RED}{'!'*80}{Style.RESET_ALL}")
        print(f"{Fore.RED}КРИТИЧЕСКИ ОТСУТСТВУЮТ:{Style.RESET_ALL}")
        for i, doc_name in enumerate(missing_critical, 1):
            print(f"{Fore.RED}  {i}. {doc_name}{Style.RESET_ALL}")
        print(f"{Fore.RED}{'!'*80}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}РЕКОМЕНДАЦИИ:{Style.RESET_ALL}")
        print("  1. Скачать Указ Президента № 449 с pravo.by или etalonline.by")
        print("  2. Изучить Приказ ОАЦ № 195 (файлы уже есть в origin-docs/)")
        print("  3. Заполнить шаблон анализа: origin-docs/PRIKAZ-195-ANALYSIS-TEMPLATE.md")
    
    # Общий статус
    print_section("ОБЩИЙ СТАТУС ГОТОВНОСТИ")
    
    overall_score = ((present_count + compliance_present) / (total_normative + total_compliance)) * 100
    
    if overall_score >= 90:
        color = Fore.GREEN
        message = "ОТЛИЧНО ✅"
    elif overall_score >= 70:
        color = Fore.YELLOW
        message = "ХОРОШО ⚠️"
    else:
        color = Fore.RED
        message = "ТРЕБУЕТСЯ РАБОТА ❌"
    
    print(f"\n{color}Общий уровень готовности: {overall_score:.1f}% - {message}{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}Полный реестр: origin-docs/NORMATIVNYE-DOKUMENTY-REGISTER.md{Style.RESET_ALL}")
    print()

if __name__ == "__main__":
    try:
        from colorama import init, Fore, Style
        main()
    except ImportError:
        print("Установите colorama: pip install colorama")
        print("\nЗапуск без цветового оформления:\n")
        # Fallback без colorama
        import sys
        sys.path.insert(0, str(BASE_DIR))
        # Простой вывод без цветов
        for doc in REQUIRED_DOCUMENTS:
            exists = doc["path"].exists()
            status = "✅ ЕСТЬ" if exists else "❌ ОТСУТСТВУЕТ"
            print(f"{status} {doc['name']}")
