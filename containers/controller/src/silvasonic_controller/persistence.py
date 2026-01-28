import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import aiosqlite
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger("Persistence")

# Default paths
DATA_DIR = os.environ.get("SILVASONIC_DATA_DIR", "/mnt/data/services/silvasonic")
LOCAL_QUEUE_DB = os.path.join(DATA_DIR, "status", "controller_queue.db")


@dataclass
class ControllerEvent:
    event_type: str
    payload: dict[str, Any]
    timestamp: float


class LocalQueue:
    """Persistent local queue using SQLite."""

    def __init__(self, db_path: str = LOCAL_QUEUE_DB):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS event_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp REAL NOT NULL,
                created_at REAL DEFAULT (unixepoch())
            )
            """
        )
        await self._db.commit()

    async def enqueue(self, event: ControllerEvent) -> None:
        if not self._db:
            return
        try:
            await self._db.execute(
                "INSERT INTO event_queue (event_type, payload, timestamp) VALUES (?, ?, ?)",
                (event.event_type, json.dumps(event.payload), event.timestamp),
            )
            await self._db.commit()
        except Exception as e:
            logger.error(f"Failed to enqueue event: {e}")

    async def peek_batch(self, limit: int = 50) -> list[tuple[int, ControllerEvent]]:
        """Returns list of (id, event)."""
        if not self._db:
            return []
        try:
            cursor = await self._db.execute(
                "SELECT id, event_type, payload, timestamp FROM event_queue ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                try:
                    event = ControllerEvent(
                        event_type=row[1], payload=json.loads(row[2]), timestamp=row[3]
                    )
                    results.append((row[0], event))
                except Exception:
                    logger.exception(f"Corrupt event in queue (ID {row[0]}), skipping")
            return results
        except Exception as e:
            logger.error(f"Failed to peek queue: {e}")
            return []

    async def ack_batch(self, ids: list[int]) -> None:
        """Remove processed events."""
        if not self._db or not ids:
            return
        try:
            placeholders = ",".join("?" for _ in ids)
            await self._db.execute(
                f"DELETE FROM event_queue WHERE id IN ({placeholders})", tuple(ids)
            )
            await self._db.commit()
        except Exception as e:
            logger.error(f"Failed to ack batch: {e}")

    async def close(self) -> None:
        if self._db:
            await self._db.close()


class DatabaseClient:
    """Async Postgres Client."""

    def __init__(self) -> None:
        # Standard Postgres Env Vars
        user = os.environ.get("POSTGRES_USER", "silvasonic")
        password = os.environ.get("POSTGRES_PASSWORD", "silvasonic")
        host = os.environ.get("POSTGRES_HOST", "db")  # Default hostname in compose
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

    async def insert_events(self, events: list[ControllerEvent]) -> bool:
        """
        Batch insert events into Postgres.
        Assumes existence of table 'controller_events' or generic 'events'.
        For now, we'll try to insert into a 'system_events' table if it exists,
        or create it if we are the authority.
        """
        # Minimal Schema: id, type, payload, timestamp

        try:
            async with self.session_maker() as session:
                # Ensure table exists (Idempotent, quick check)
                # In production, use migrations. Here, for robustness:
                await session.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS controller_events (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(255) NOT NULL,
                        payload JSONB NOT NULL,
                        timestamp FLOAT NOT NULL,
                        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )

                # Bulk Insert
                # SQLAlchemy Core or ORM. Core is faster for batch.
                vals = [
                    {
                        "event_type": e.event_type,
                        "payload": json.dumps(
                            e.payload
                        ),  # asyncpg handles jsonb but explicit string often safer w/ text()
                        "timestamp": e.timestamp,
                    }
                    for e in events
                ]

                stmt = text("""
                    INSERT INTO controller_events (event_type, payload, timestamp)
                    VALUES (:event_type, :payload, :timestamp)
                """)

                await session.execute(stmt, vals)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"DB Insert Failed: {e}")
            return False


class PersistenceManager:
    def __init__(self) -> None:
        self.queue = LocalQueue()
        self.db = DatabaseClient()
        self.running = True

    async def start(self) -> None:
        await self.queue.init()
        logger.info(f"Persistence initialized. Local Queue: {self.queue.db_path}")

    async def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget logging to local queue."""
        event = ControllerEvent(event_type=event_type, payload=payload, timestamp=time.time())
        await self.queue.enqueue(event)

    async def sync_loop(self) -> None:
        """Background task to flush queue to DB."""
        logger.info("Starting Sync Loop...")
        backoff = 1

        while self.running:
            try:
                # 1. Peek Queue
                batch = await self.queue.peek_batch(limit=50)
                if not batch:
                    # Queue empty, verify connection leisurely
                    await asyncio.sleep(5)
                    continue

                # 2. Check DB Connection
                # If we consider 'batch exists', we aggressively try to connect
                if not await self.db.check_connection():
                    logger.debug("DB offline, buffering locally...")
                    await asyncio.sleep(5)
                    continue

                # 3. Flush to DB
                events = [item[1] for item in batch]
                ids = [item[0] for item in batch]

                success = await self.db.insert_events(events)

                if success:
                    # 4. Ack Local Queue
                    await self.queue.ack_batch(ids)
                    logger.info(f"Synced {len(events)} events to DB.")
                    backoff = 1
                else:
                    # DB Error during insert
                    await asyncio.sleep(backoff)
                    backoff = min(60, backoff * 2)

            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        self.running = False
        await self.queue.close()
