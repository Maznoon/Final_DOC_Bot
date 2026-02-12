import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.config.config import settings
from src.db.session import init_db
from src.utils.db_middleware import DbSessionMiddleware
from src.utils.throttling import ThrottlingMiddleware
from src.handlers import common, products, order_wizard, payment, admin, support

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Initialize DB
    await init_db()

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    # Register routers
    dp.include_router(common.router)
    dp.include_router(products.router)
    dp.include_router(order_wizard.router)
    dp.include_router(payment.router)
    dp.include_router(admin.router)
    dp.include_router(support.router)

    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
