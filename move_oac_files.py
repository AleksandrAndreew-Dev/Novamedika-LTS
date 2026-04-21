#!/usr/bin/env python3
"""
Скрипт для перемещения файлов ОАЦ в правильные папки согласно правилам организации
"""

import shutil
from pathlib import Path
from colorama import init, Fore, Style

# Инициализация colorama
init(autoreset=True)

BASE_DIR = Path(__file__).parent

# Определение правил перемещения
FILES_TO_MOVE = {
    # Файлы нормативных документов -> origin-docs/
    "REQUIRED-DOCUMENTS-FOR-COMPLIANCE.md": "origin-docs/",
    "OAC-COMPLIANCE-STATUS-REPORT.md": "origin-docs/",
    
    # Скрипты проверки -> oac/ (вспомогательные инструменты)
    "check_normative_docs.py": "oac/",
    "read_pdf_195.py": "oac/tools/",  # Создадим подпапку для инструментов
    
    # Документация по шифрованию -> oac/docs/ (как дополнение к политике шифрования)
    "PRODUCTION-DEPLOYMENT-ENCRYPTION.md": "oac/docs/",
    "ENCRYPTION-IMPLEMENTATION-GUIDE.md": "oac/guides/",
}

def move_file(src: Path, dst: Path) -> bool:
    """Безопасное перемещение файла с проверками"""
    try:
        # Создаем целевую директорию если не существует
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        # Проверяем не существует ли уже файл
        if dst.exists():
            print(f"{Fore.YELLOW}⚠️  Файл уже существует: {dst.relative_to(BASE_DIR)}{Style.RESET_ALL}")
            print(f"   Пропускаем перемещение{Style.RESET_ALL}")
            return False
        
        # Перемещаем файл
        shutil.move(str(src), str(dst))
        print(f"{Fore.GREEN}✅ Перемещен:{Style.RESET_ALL} {src.relative_to(BASE_DIR)} → {dst.relative_to(BASE_DIR)}")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка при перемещении {src.name}: {e}{Style.RESET_ALL}")
        return False

def main():
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}ПЕРЕМЕЩЕНИЕ ФАЙЛОВ ОАЦ В ПРАВИЛЬНЫЕ ПАПКИ{Style.RESET_ALL}".center(80))
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    moved_count = 0
    skipped_count = 0
    errors = []
    
    for filename, target_dir in FILES_TO_MOVE.items():
        src = BASE_DIR / filename
        dst = BASE_DIR / target_dir / filename
        
        # Проверяем существование источника
        if not src.exists():
            print(f"{Fore.YELLOW}⚠️  Файл не найден: {filename}{Style.RESET_ALL}")
            continue
        
        # Перемещаем файл
        if move_file(src, dst):
            moved_count += 1
        else:
            skipped_count += 1
    
    # Итоговая статистика
    print(f"\n{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}СТАТИСТИКА:{Style.RESET_ALL}")
    print(f"  ✅ Перемещено: {moved_count} файлов")
    print(f"  ⚠️  Пропущено: {skipped_count} файлов")
    print(f"  ❌ Ошибок: {len(errors)}")
    print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}\n")
    
    if moved_count > 0:
        print(f"{Fore.GREEN}✓ Перемещение завершено успешно!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Не забудьте сделать коммит изменений:{Style.RESET_ALL}")
        print("  git add -A")
        print('  git commit -m "refactor: переместить файлы ОАЦ в правильные папки согласно правилам организации"')
        print()
    else:
        print(f"{Fore.YELLOW}⚠️  Файлы не были перемещены{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
