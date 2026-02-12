from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User

async def get_or_create_user(session: AsyncSession, telegram_id: int, full_name: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_user_id == telegram_id))
    user = result.scalars().first()

    if not user:
        user = User(telegram_user_id=telegram_id, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user
