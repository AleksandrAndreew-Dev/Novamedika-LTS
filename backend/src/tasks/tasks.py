# app/tasks.py (обновляем для использования новой задачи)
from tasks_increment import process_csv_incremental

# Оставляем старую задачу для обратной совместимости
# или заменяем на новую
process_csv_task = process_csv_incremental
