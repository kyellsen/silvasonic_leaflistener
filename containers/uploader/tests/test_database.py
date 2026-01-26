from unittest.mock import MagicMock, patch

import pytest
from database import DatabaseHandler


class TestDatabaseHandler:
    @pytest.fixture
    def db(self, mock_env):
        return DatabaseHandler()

    @patch("database.create_engine")
    @patch("database.sessionmaker")
    def test_connect_success(self, mock_sessionmaker, mock_engine, db):
        mock_conn = MagicMock()
        mock_engine.return_value.begin.return_value.__enter__.return_value = mock_conn

        assert db.connect() is True
        assert db.Session is not None

        # Verify schema creation
        assert mock_conn.execute.call_count >= 1

    @patch("database.create_engine")
    def test_connect_failure(self, mock_engine, db):
        mock_engine.side_effect = Exception("Connection Failed")
        assert db.connect() is False
        assert db.Session is None

    @patch("database.create_engine")
    @patch("database.sessionmaker")
    def test_log_upload_auto_connect(self, mock_sessionmaker, mock_engine, db):
        # Ensure connect() is called if Session is None
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        mock_engine.return_value.begin.return_value.__enter__.return_value = MagicMock()

        db.log_upload("file.txt", "remote/file.txt", "success")

        # Verify execution
        mock_session_inst.execute.assert_called_once()
        mock_session_inst.commit.assert_called_once()
        mock_session_inst.close.assert_called_once()

    @patch("database.create_engine")
    @patch("database.sessionmaker")
    def test_log_upload_rollback_on_error(self, mock_sessionmaker, mock_engine, db):
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        db.connect()

        # Simulate execute failure
        mock_session_inst.execute.side_effect = Exception("DB Error")

        db.log_upload("file.txt", "remote/file.txt", "success")

        mock_session_inst.rollback.assert_called_once()
        mock_session_inst.close.assert_called_once()

    @patch("database.create_engine")
    @patch("database.sessionmaker")
    def test_get_uploaded_filenames(self, mock_sessionmaker, mock_engine, db):
        mock_session_inst = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_inst)
        db.connect()

        # Mock query result
        mock_session_inst.execute.return_value = [
            ("file1.txt",), ("file3.txt",)
        ]

        input_files = ["file1.txt", "file2.txt", "file3.txt"]
        result = db.get_uploaded_filenames(input_files)

        assert "file1.txt" in result
        assert "file3.txt" in result
        assert "file2.txt" not in result

    def test_get_uploaded_filenames_empty(self, db):
        # Should return empty set immediately without connecting
        assert db.get_uploaded_filenames([]) == set()
        assert db.Session is None

    @patch("database.create_engine")
    def test_get_uploaded_filenames_connection_fail(self, mock_engine, db):
        mock_engine.side_effect = Exception("Conn Fail")
        assert db.get_uploaded_filenames(["file.txt"]) == set()

    @patch("src.database.create_engine")
    def test_log_upload_connection_fail(self, mock_engine, db):
        # Ensure session is None
        db.Session = None
        mock_engine.side_effect = Exception("Conn Fail")

        # Should return without crashing
        db.log_upload("file.txt", "remote", "success")
        assert db.Session is None
