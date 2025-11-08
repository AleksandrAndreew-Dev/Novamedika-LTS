#!/bin/bash

# Мониторинг изменений и автоматическая пересборка

echo "🚀 Starting development watcher..."

# Функция для перезапуска фронтенда
restart_frontend() {
    echo "🔄 Restarting frontend due to changes..."
    docker-compose -f docker-compose.traefik.dev.yml restart frontend
    echo "✅ Frontend restarted"
}

# Функция для перезапуска бэкенда
restart_backend() {
    echo "🔄 Restarting backend due to changes..."
    docker-compose -f docker-compose.traefik.dev.yml restart backend
    echo "✅ Backend restarted"
}

# Мониторим изменения в файлах
fswatch -o ./frontend/src | while read; do restart_frontend; done &
fswatch -o ./backend/src | while read; do restart_backend; done &

# Ждем Ctrl+C для остановки
echo "📡 Watching for file changes... Press Ctrl+C to stop"
wait
