import PyPDF2
import os

# Базовая директория для файлов
base_dir = r'C:\Users\37525\Desktop\upwork\projects\Novamedika2\origin-docs'

# Пробуем оба файла
files_to_try = [
    os.path.join(base_dir, '2021-195.pdf'),
    os.path.join(base_dir, '195-vpdf.pdf')
]

for pdf_path in files_to_try:
    print(f"\n{'='*80}")
    print(f"ПЫТАЕМСЯ ПРОЧИТАТЬ: {pdf_path}")
    print("="*80)
    
    if not os.path.exists(pdf_path):
        print(f"Файл не найден: {pdf_path}")
        continue
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            print(f"Страниц: {len(reader.pages)}")
            
            # Пробуем первые 3 страницы
            for i in range(min(3, len(reader.pages))):
                page = reader.pages[i]
                text = page.extract_text()
                
                if text and len(text.strip()) > 50:
                    print(f"\n--- Страница {i+1} ({len(text)} символов) ---")
                    print(text[:1000])
                    if len(text) > 1000:
                        print("...")
                else:
                    print(f"\n--- Страница {i+1}: Текст не извлечен или пустой ---")
                    
    except Exception as e:
        print(f"Ошибка: {e}")