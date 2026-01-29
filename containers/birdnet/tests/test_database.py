from unittest.mock import MagicMock, patch

import pytest
from silvasonic_birdnet.database import DatabaseHandler
from silvasonic_birdnet.models import BirdDetection, Watchlist
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine, select


@pytest.fixture
def test_db():
    """Fixture for an in-memory database."""
    with patch("silvasonic_birdnet.database.time.sleep"):
        handler = DatabaseHandler()
        handler.db_url = "sqlite:///:memory:"

        # We need to interfere with the connection context manager to suppress the CREATE SCHEMA call
        # but allow SQLModel.metadata.create_all to work.
        # It's tricky because they use the same engine.

        # Let's mock create_engine to return a real engine,
        # but we wrap it to suppress specific execute calls?
        # Maybe easier: Just let it fail the first execute ("CREATE SCHEMA"), catch it, and proceed?
        # But the code catches Exception and returns False.
        # So connect() returns False.

        # So we must prevent it from failing.
        # We can mock `sqlalchemy.text` to return something benign?
        # Or patch handler.connect to skip schema creation? (Best approach for unit test)

        def testing_connect():
            handler.engine = create_engine(handler.db_url)

            # ATTACH DATABASE for SQLite schema support
            with handler.engine.connect() as connection:
                from sqlalchemy import text

                connection.execute(text("ATTACH DATABASE ':memory:' AS birdnet"))
                connection.commit()

            # SKIPPING SCHEMA CREATION for SQLite
            SQLModel.metadata.create_all(handler.engine)
            return True

        handler.connect = testing_connect
        handler.connect()
        return handler


def test_connect_creates_tables(test_db):
    """Test that connect creates the necessary tables."""
    assert test_db.engine is not None
    # Verify table existence by inspecting metadata or trying a query
    with Session(test_db.engine) as session:
        # Should not raise error
        results = session.exec(select(Watchlist)).all()
        assert results == []


def test_watchlist_crud(test_db):
    """Test Create, Read, Update, Check operations for Watchlist."""
    # 1. Update (Create)
    test_db.update_watchlist("Turdus merula", "Blackbird", enabled=True)

    # 2. Check
    assert test_db.is_watched("Turdus merula") is True
    assert test_db.is_watched("Passer domesticus") is False

    # 3. Read All
    items = test_db.get_watchlist()
    assert len(items) == 1
    assert items[0].scientific_name == "Turdus merula"

    # 4. Update (Disable)
    test_db.update_watchlist("Turdus merula", "Blackbird", enabled=False)
    assert test_db.is_watched("Turdus merula") is False

    # 5. Read operations (should filter enabled=1)
    items = test_db.get_watchlist()
    assert len(items) == 0


def test_save_detection(test_db):
    """Test saving a detection."""
    detection = BirdDetection(
        filename="test.wav",
        filepath="/tmp/test.wav",
        scientific_name="Turdus merula",
        common_name="Blackbird",
        confidence=0.95,
        start_time=0.0,
        end_time=3.0,
    )

    test_db.save_detection(detection)

    with Session(test_db.engine) as session:
        saved = session.exec(select(BirdDetection)).first()
        assert saved is not None
        assert saved.scientific_name == "Turdus merula"
        assert saved.confidence == 0.95
        assert saved.timestamp is not None  # Factory worked


def test_log_processed_file(test_db):
    """Test logging processed file stats."""
    test_db.log_processed_file("test.wav", duration=10.0, processing_time=0.5, file_size=1024)

    # Verification (requires inspecting the ProcessedFile table, which we assume exists)
    # We need to import ProcessedFile to query it
    from silvasonic_birdnet.models import ProcessedFile

    with Session(test_db.engine) as session:
        log = session.exec(select(ProcessedFile)).first()
        assert log is not None
        assert log.filename == "test.wav"
        assert log.audio_duration_sec == 10.0


@patch("silvasonic_birdnet.database.time.sleep")
@patch("silvasonic_birdnet.database.create_engine")
def test_connection_failure(mock_create, mock_sleep):
    """Test graceful handling of connection failures."""
    handler = DatabaseHandler()

    # Mock engine.connect() to raise OperationalError
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("Connection refused", params=None, orig=None)
    mock_create.return_value = mock_engine

    handler.db_url = "postgresql://invalid:invalid@localhost:5432/invalid"

    # We allow it to loop 10 times
    assert handler.connect() is False
    assert mock_sleep.call_count == 10


def test_pending_analysis_logic(test_db):
    """Test getting pending analysis and marking as done."""
    # We need to manually insert a recording into the table
    # Since we don't have the Recording model definition in this test file's imports typically,
    # we can use raw SQL or define a dummy model if needed.
    # But wait, BirdNET container doesn't OWN the Recordings table model completely?
    # It queries it. The models.py in birdnet might not have it.
    # Let's check imports.
    # We need to ensure the 'recordings' table exists in our in-memory DB.
    # The 'init' SQL script usually creates it. Our test_db setup runs create_all for SQLModel.
    # Does BirdNET's SQLModel metadata include 'recordings'?
    # If not, we can't test it easily without defining it here.

    # Assuming we might need to mock the query execution if the table doesn't exist in metadata.
    # But let's try defining a partial model for the test or raw execute.

    with Session(test_db.engine) as session:
        from sqlalchemy import text

        session.exec(
            text(
                "CREATE TABLE IF NOT EXISTS recordings (id INTEGER PRIMARY KEY, path_low TEXT, path_high TEXT, analyzed_bird BOOLEAN, time TIMESTAMP)"
            )
        )
        session.exec(
            text(
                "INSERT INTO recordings (id, path_low, path_high, analyzed_bird) VALUES (1, 'low.wav', 'high.wav', 0)"
            )
        )
        session.commit()

    # Test Get
    pending = test_db.get_pending_analysis(limit=1)
    assert len(pending) == 1
    assert pending[0]["id"] == 1
    assert pending[0]["path_low"] == "low.wav"

    # Test Mark
    test_db.mark_analyzed(1)

    with Session(test_db.engine) as session:
        from sqlalchemy import text

        res = session.exec(text("SELECT analyzed_bird FROM recordings WHERE id=1")).first()
        assert res[0] is not None  # In sqlite boolean might be 1/0
        assert res[0] != 0  # True
