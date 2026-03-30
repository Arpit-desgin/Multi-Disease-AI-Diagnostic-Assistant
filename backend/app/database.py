from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

db_available = True


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    if not db_available:
        yield None
        return
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception:
        yield None
