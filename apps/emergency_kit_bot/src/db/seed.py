import asyncio
from sqlalchemy import select
from src.db.session import async_session, init_db
from src.db.models import Product

async def seed_products():
    async with async_session() as session:
        # Check if products already exist
        result = await session.execute(select(Product))
        if result.scalars().first():
            print("Products already seeded.")
            return

        products = [
            Product(
                sku="ECO72",
                title_fa="کیت آمادگی بحران اقتصادی شهری (۷۲ ساعته – یک نفره)",
                description_fa="این کیت شامل اقلام ضروری برای بقا در محیط شهری به مدت ۷۲ ساعت است. مناسب برای یک نفر.",
                price_toman=1500000,
                stock=50,
                is_active=True
            ),
            Product(
                sku="ECO72_PLUS",
                title_fa="کیت آمادگی بحران اقتصادی پلاس (۷۲ ساعته – یک نفره)",
                description_fa="نسخه پیشرفته کیت اقتصادی با اقلام اضافه و کیفیت بالاتر. مناسب برای شرایط سخت‌تر.",
                price_toman=2500000,
                stock=30,
                is_active=True
            )
        ]
        session.add_all(products)
        await session.commit()
        print("Products seeded successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(seed_products())
