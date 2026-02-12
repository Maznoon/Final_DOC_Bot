from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    from src.db.models import Base
    async with engine.begin() as conn:
        # For MVP, we can use create_all. For production, use Alembic.
        await conn.run_sync(Base.metadata.create_all)
