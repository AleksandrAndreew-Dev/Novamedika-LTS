#!/usr/bin/env python3
import asyncio
import os
from bot.core import bot_manager

async def main():
    await bot_manager.initialize()
    result = await set_webhook()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
