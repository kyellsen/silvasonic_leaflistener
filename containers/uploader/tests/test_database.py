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

        # Load uploader/src/database.py directly
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/database.py"))
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

        # Verify schema creation
        assert mock_conn.execute.call_count >= 1

    @patch("uploader_database.create_engine")
    def test_connect_failure(self, mock_engine: MagicMock, db: typing.Any) -> None:
        """Test connection failure handling."""
        mock_engine.side_effect = Exception("Connection Failed")
        assert db.connect() is False
        assert db.Session is None

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_log_upload_auto_connect(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test that log_upload connects if session is missing."""
        # Ensure connect() is called if Session is None
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        mock_engine.return_value.begin.return_value.__enter__.return_value = MagicMock()

        db.log_upload("file.txt", "remote/file.txt", "success")

        # Verify execution
        mock_session_inst.execute.assert_called_once()
        mock_session_inst.commit.assert_called_once()
        mock_session_inst.close.assert_called_once()

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_log_upload_rollback_on_error(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test rollback on log_upload error."""
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        db.connect()

        # Simulate execute failure
        mock_session_inst.execute.side_effect = Exception("DB Error")

        db.log_upload("file.txt", "remote/file.txt", "success")

        mock_session_inst.rollback.assert_called_once()
        mock_session_inst.close.assert_called_once()

    @patch("uploader_database.create_engine")
    @patch("uploader_database.sessionmaker")
    def test_get_uploaded_filenames(
        self, mock_sessionmaker: MagicMock, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test retrieval of uploaded filenames."""
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        db.connect()

        # Mock query result
        mock_session_inst.execute.return_value = [("file1.txt",), ("file3.txt",)]

        input_files = ["file1.txt", "file2.txt", "file3.txt"]
        result = db.get_uploaded_filenames(input_files)

        assert "file1.txt" in result
        assert "file3.txt" in result
        assert "file2.txt" not in result

    def test_get_uploaded_filenames_empty(self, db: typing.Any) -> None:
        """Test get_uploaded_filenames with empty list."""
        # Should return empty set immediately without connecting
        assert db.get_uploaded_filenames([]) == set()
        assert db.Session is None

    @patch("uploader_database.create_engine")
    def test_get_uploaded_filenames_connection_fail(
        self, mock_engine: MagicMock, db: typing.Any
    ) -> None:
        """Test get_uploaded_filenames when connection fails."""
        mock_engine.side_effect = Exception("Conn Fail")
        assert db.get_uploaded_filenames(["file.txt"]) == set()

    @patch("uploader_database.create_engine")
    def test_log_upload_connection_fail(self, mock_engine: MagicMock, db: typing.Any) -> None:
        """Test log_upload when connection fails."""
        # Ensure session is None
        db.Session = None
        mock_engine.side_effect = Exception("Conn Fail")

        # Should return without crashing
        db.log_upload("file.txt", "remote", "success")
        assert db.Session is None
