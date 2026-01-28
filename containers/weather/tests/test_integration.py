import logging
from collections.abc import Generator

import pytest
from silvasonic_weather import analysis, main
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

# Configure logging to see output during tests if -s is used
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Spin up a Postgres container for the duration of the module.
    """
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def db_url(postgres_container: PostgresContainer) -> str:
    """
    Get valid DB URL from container.
    """
    return postgres_container.get_connection_url()


@pytest.fixture(autouse=True)
def override_settings(db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Override global settings to point to the test container.
    """
    # We need to patch the computed_field or the underlying attributes?
    # Settings defines database_url as a computed field based on components.
    # It might be easier to patch 'main.engine' and 'analysis.engine' directly
    # OR patch the attributes of settings if possible.
    # Since 'database_url' is computed, we can't simple set it unless we assume
    # the container url can be parsed back into user/pass/host/port.
    #
    # Testcontainers URL format: postgresql://test:test@localhost:32145/test
    #
    # Let's try to parse it or monkeypatch the property.

    # Simpler: Patch the engines in main/analysis to use a new engine connected to our test DB.
    # But main.py creates 'engine' at module level.
    # So we must patch silvasonic_weather.main.engine and silvasonic_weather.analysis.engine

    test_engine = create_engine(db_url)

    monkeypatch.setattr("silvasonic_weather.main.engine", test_engine)
    monkeypatch.setattr("silvasonic_weather.analysis.engine", test_engine)

    # Also patch settings.get_location to a known value if we want stable weather queries?
    # Or let it use default (Berlin). Berlin is fine.


def test_e2e_weather_flow() -> None:
    """
    Full end-to-end test:
    1. Initialize DB schema (in the test container).
    2. Fetch REAL weather data from DWD (requires internet).
    3. Verify data is in DB.
    4. Run analysis.
    5. Verify stats are generated.
    """
    logger.info("Step 1: Initializing DB...")
    main.init_db()

    logger.info("Step 2: Fetching Weather...")
    # This calls the real DWD API.
    # If it fails due to network, the test fails, which is what we want (verification).
    main.fetch_weather()

    logger.info("Step 3: Verifying Measurements...")
    # Check DB
    with main.get_db_connection() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM weather.measurements")).scalar()
        logger.info(f"Rows in weather.measurements: {result}")
        assert result > 0, "No weather measurements stored!"

        # Check specific column to ensure mapping worked
        row = conn.execute(text("SELECT * FROM weather.measurements LIMIT 1")).fetchone()
        logger.info(f"Sample Row: {row}")
        # Assuming row is accessible by key or index. SQLAlchemy rows are tuple-like but likely named tuples.
        # Let's just check it's not empty.
        assert row is not None

    logger.info("Step 4: Running Analysis...")
    analysis.init_analysis_db()
    analysis.run_analysis()

    logger.info("Step 5: Verifying Analysis...")
    with analysis.get_connection() as conn:
        stats_count = conn.execute(text("SELECT COUNT(*) FROM weather.bird_stats")).scalar()
        logger.info(f"Rows in weather.bird_stats: {stats_count}")

        # Note: bird_stats might be 0 if 'birdnet.detections' table is missing or empty!
        # The complex query joins with birdnet.detections.
        # "LEFT JOIN b_stats" -> if b_stats is empty, we still get w_stats rows if we have weather data.
        # So we expect > 0 rows if we have weather data.
        assert stats_count > 0, "No analysis stats generated!"
