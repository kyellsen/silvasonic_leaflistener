import typing
from unittest.mock import MagicMock, patch

import pytest


class TestDatabaseHandler:
    """Tests for DatabaseHandler."""

    @pytest.fixture
    def db(self, mock_env: None) -> typing.Any:
        """Fixture for DatabaseHandler."""
        import importlib.util
        import os
        import sys

        # Load uploader/src/silvasonic_uploader/database.py directly
        db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../src/silvasonic_uploader/database.py")
        )
        spec = importlib.util.spec_from_file_location("uploader_database", db_path)
        assert spec is not None
        uploader_database = importlib.util.module_from_spec(spec)
        sys.modules["uploader_database"] = uploader_database
        assert spec is not None
        assert spec.loader is not None
        assert uploader_database is not None
        spec.loader.exec_module(uploader_database)

        return uploader_database.DatabaseHandler()

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_connect_success(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test successful connection and database initialization."""
        mock_conn = MagicMock()
        mock_engine.return_value.begin.return_value.__enter__.return_value = mock_conn

        assert db.connect() is True
        assert db.Session is not None

        # Verify successful initialization (executed implicitly via engine.begin())
        assert mock_engine.return_value.begin.called

    @patch("uploader_database.create_engine")
    def test_connect_failure(self, mock_engine: MagicMock, db: typing.Any) -> None:
        """Test connection failure handling."""
        mock_engine.side_effect = Exception("Connection Failed")
        assert db.connect() is False
        assert db.Session is None

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_get_pending_recordings(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test retrieval of pending recordings."""
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)

        # Mock valid result with path_high
        mock_session_inst.execute.return_value = [
            ("req_id_1", "path/to/high.wav"),
            ("req_id_2", "path/to/another.wav"),
        ]

        results = db.get_pending_recordings(limit=10)
        assert len(results) == 2
        assert results[0]["id"] == "req_id_1"
        assert results[0]["path"] == "path/to/high.wav"

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_mark_recording_uploaded(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test marking a recording as uploaded."""
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)

        db.mark_recording_uploaded("req_id_1")

        # Verify execute called with UPDATE
        mock_session_inst.execute.assert_called_once()
        args = mock_session_inst.execute.call_args[0][0]
        assert "UPDATE recordings" in str(args)
        assert "uploaded = true" in str(args)
