import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

logger = logging.getLogger("app.database")

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

db_available = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session with proper cleanup."""
    if not db_available:
        raise RuntimeError("Database not available")
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")