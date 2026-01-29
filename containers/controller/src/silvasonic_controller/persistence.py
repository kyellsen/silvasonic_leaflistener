import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger("Persistence")


class DatabaseClient:
    """Async Postgres Client for Configuration Reading."""

    def __init__(self) -> None:
        # Standard Postgres Env Vars
        user = os.environ.get("POSTGRES_USER", "silvasonic")
        password = os.environ.get("POSTGRES_PASSWORD", "silvasonic")
        host = os.environ.get("POSTGRES_HOST", "db")
        db_name = os.environ.get("POSTGRES_DB", "silvasonic")
        port = os.environ.get("POSTGRES_PORT", "5432")

        self.url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        self.engine = create_async_engine(self.url, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.connected = False

    async def check_connection(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            self.connected = True
            return True
        except Exception:
            self.connected = False
            return False

    async def get_service_config(self) -> dict[str, bool]:
        """
        Fetch service state configuration.
        Returns dict: {service_name: enabled}
        """
        try:
            async with self.session_maker() as session:
                # Ensure table exists (Idempotent for dev, usually handled by Init)
                # We do NOT create table here to avoid race conditions.
                # Just read. IF it fails, returns empty.
                try:
                    stmt = text("SELECT service_name, enabled FROM service_state")
                    result = await session.execute(stmt)
                    rows = result.fetchall()
                    return {row[0]: bool(row[1]) for row in rows}
                except Exception:
                    # Table might not exist yet
                    return {}
        except Exception as e:
            logger.error(f"DB Config Read Failed: {e}")
            return {}
