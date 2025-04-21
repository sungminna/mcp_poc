from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import DATABASE_URL

# Use create_async_engine
engine = create_async_engine(
    DATABASE_URL, 
    # connect_args={"check_same_thread": False} # Not needed/applicable for asyncpg
    echo=True # Optional: Log SQL queries, helpful for debugging
)

# Use async_sessionmaker and AsyncSession
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False, 
    autocommit=False, 
    autoflush=False
)

Base = declarative_base()

# Async dependency to get DB session
async def get_db() -> AsyncSession: # Type hint return value
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback() # Rollback on error
            raise e
        finally:
            await session.close() # Ensure session is closed 