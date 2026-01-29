import os

import httpx
import pytest
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration with defaults for local testing
DB_URL = os.getenv("DB_URL", "postgresql://silvasonic:silvasonic@localhost:5432/silvasonic")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")


@pytest.fixture(scope="module")
def db_engine():
    """Yields a SQLAlchemy engine connected to the test DB."""
    engine = create_engine(DB_URL)
    try:
        connection = engine.connect()
        connection.close()
        yield engine
    except Exception as e:
        pytest.skip(f"Database unavailable at {DB_URL}: {e}")


@pytest.fixture(scope="module")
def db_session(db_engine):
    """Yields a SQLAlchemy session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def redis_client():
    """Yields a Redis client."""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    try:
        client.ping()
        yield client
    except redis.ConnectionError as e:
        pytest.skip(f"Redis unavailable at {REDIS_HOST}:{REDIS_PORT}: {e}")
    finally:
        client.close()


@pytest.fixture(scope="module")
def gateway_client():
    """Yields an HTTP client for the Gateway."""
    client = httpx.Client(base_url=GATEWAY_URL)
    yield client
    client.close()
