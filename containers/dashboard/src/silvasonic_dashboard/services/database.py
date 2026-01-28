import os

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker


class DatabaseHandler:
    def __init__(self) -> None:
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")

        self.db_url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.engine = create_async_engine(self.db_url, pool_pre_ping=True)
        self.async_session_maker = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    def get_connection(self) -> AsyncConnection:
        return self.engine.connect()

    async def get_db(self):
        async with self.async_session_maker() as session:
            yield session


db = DatabaseHandler()
