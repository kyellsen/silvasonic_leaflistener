import sqlalchemy
from sqlalchemy import text


def test_db_connection(db_engine):
    """Verify that we can connect to the database."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_critical_tables_exist(db_engine):
    """Verify that critical tables exist in the schema."""
    inspector = sqlalchemy.inspect(db_engine)
    tables = inspector.get_table_names()

    expected_tables = ["recordings", "detections"]
    for table in expected_tables:
        assert table in tables, f"Table '{table}' not found in database."


def test_recordings_columns(db_engine):
    """Verify that the recordings table has the expected columns."""
    inspector = sqlalchemy.inspect(db_engine)
    columns = [col["name"] for col in inspector.get_columns("recordings")]

    expected_columns = ["id", "time", "date", "filename", "duration", "sample_rate", "channels"]
    for col in expected_columns:
        assert col in columns, f"Column '{col}' not found in 'recordings' table."


def test_detections_columns(db_engine):
    """Verify that the detections table has the expected columns."""
    inspector = sqlalchemy.inspect(db_engine)
    columns = [col["name"] for col in inspector.get_columns("detections")]

    expected_columns = [
        "id",
        "time",
        "date",
        "recording_id",
        "confidence",
        "scientific_name",
        "common_name",
    ]
    for col in expected_columns:
        assert col in columns, f"Column '{col}' not found in 'detections' table."


def test_timescaledb_extension(db_engine):
    """Verify that TimescaleDB extension is installed."""
    with db_engine.connect() as conn:
        result = conn.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'timescaledb'")
        )
        assert result.scalar() == 1, "TimescaleDB extension not found."


def test_hypertables_exist(db_engine):
    """Verify that recordings and detections are hypertables."""
    # This query might vary slightly depending on TimescaleDB version, but this view is standard.
    # We check if 'recordings' and 'detections' are listed in timescaledb_information.hypertables
    with db_engine.connect() as conn:
        # Note: hypertable_name might represent the table name
        result = conn.execute(
            text("SELECT hypertable_name FROM timescaledb_information.hypertables")
        )
        hypertables = [row[0] for row in result.fetchall()]

        # Depending on schema, might need check if they are in 'public' schema or similar
        # But usually just the name is enough for this check if unique
        assert "recordings" in hypertables, "'recordings' is not a hypertable."
        assert "detections" in hypertables, "'detections' is not a hypertable."
