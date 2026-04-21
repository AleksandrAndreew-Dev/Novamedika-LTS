#!/usr/bin/env python3
"""
Скрипт для диагностики Telegram Bot Webhook
Проверяет статус webhook и выводит детальную информацию
"""
import os
import sys
import json
import requests
from pathlib import Path

# Добавляем путь к backend/src
backend_src = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

def check_webhook_status():
    """Проверка статуса webhook через Telegram Bot API"""
    
    # Получаем токен бота из переменных окружения
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
        print("\nДля проверки вручную выполните:")
        print('curl -s "https://api.telegram.org/bot<ВАШ_ТОКЕН>/getWebhookInfo" | python3 -m json.tool')
        return False
    
    # Формируем URL для запроса
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        print(f"🔍 Проверка статуса webhook...")
        print(f"📡 Запрос к: {api_url}\n")
        
        # Делаем запрос к Telegram Bot API
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("ok"):
            print(f"❌ Ошибка API: {data.get('description', 'Unknown error')}")
            return False
        
        webhook_info = data["result"]
        
        # Выводим информацию о webhook
        print("=" * 60)
        print("📊 ИНФОРМАЦИЯ О WEBHOOK")
        print("=" * 60)
        print(f"✅ URL: {webhook_info.get('url', 'Не установлен')}")
        print(f"🔄 Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"🔗 Max connections: {webhook_info.get('max_connections', 40)}")
        print(f"📝 Allowed updates: {webhook_info.get('allowed_updates', 'Все')}")
        
        # Проверяем наличие ошибок
        last_error_date = webhook_info.get("last_error_date")
        last_error_message = webhook_info.get("last_error_message")
        
        if last_error_date and last_error_message:
            from datetime import datetime
            error_time = datetime.fromtimestamp(last_error_date)
            print(f"\n⚠️  ПОСЛЕДНЯЯ ОШИБКА:")
            print(f"   📅 Время: {error_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   💬 Сообщение: {last_error_message}")
        else:
            print(f"\n✅ Ошибок нет")
        
        # Дополнительная информация
        print(f"\n📈 Статистика:")
        print(f"   Total updates received: {webhook_info.get('total_updates_received', 0)}")
        
        # Рекомендации
        print("\n" + "=" * 60)
        print("💡 РЕКОМЕНДАЦИИ")
        print("=" * 60)
        
        if not webhook_info.get('url'):
            print("⚠️  Webhook не установлен!")
            print("   Решение: Перезапустите backend сервис")
        elif webhook_info.get('pending_update_count', 0) > 100:
            print(f"⚠️  Большое количество pending updates: {webhook_info['pending_update_count']}")
            print("   Решение: Возможно, бот не обрабатывает обновления. Проверьте логи.")
        elif last_error_message:
            print(f"⚠️  Обнаружена ошибка webhook: {last_error_message}")
            print("   Решение: Проверьте доступность URL и SSL сертификат")
        else:
            print("✅ Webhook настроен корректно")
            print("   Если обновления не приходят, проверьте:")
            print("   1. Доступность URL из интернета")
            print("   2. Правильность настройки Traefik")
            print("   3. Логи backend на наличие входящих запросов")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_webhook_status()
    sys.exit(0 if success else 1)
