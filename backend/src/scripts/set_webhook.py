#!/usr/bin/env python3
import asyncio
from bot.core import bot_manager

async def main():
    bot, dp = await bot_manager.initialize()
    if bot:
        # Установка webhook будет происходить в main.py при запуске
        print("Bot initialized successfully")
    else:
        print("Failed to initialize bot")

if __name__ == "__main__":
    asyncio.run(main())
