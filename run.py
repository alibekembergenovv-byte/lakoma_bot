import asyncio
import logging
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import load_config
from bot.database.db import init_db
from bot.handlers.start import start_router
from bot.handlers.registration import registration_router
from bot.handlers.report import report_router
from bot.handlers.admin import admin_router

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    config = load_config()
    if not config.bot_token:
        logger.error("BOT_TOKEN is not configured! Please specify it in your .env file.")
        return

    logger.info("Initializing SQLite database...")
    await init_db(config.db_path)
    logger.info(f"Database ready at: {config.db_path}")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register workflow routers
    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(report_router)
    dp.include_router(admin_router)

    # Inject global config
    dp["config"] = config

    logger.info("Starting Lakoma Catering Bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
