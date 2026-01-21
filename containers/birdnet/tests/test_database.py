from src.database import Detection, init_db, SessionLocal, Base
from datetime import datetime
import os
from unittest.mock import patch, MagicMock

def test_detection_model(db_session):
    det = Detection(
        recording_timestamp=datetime.utcnow(),
        filename="test.wav",
        start_time=0.0,
        end_time=3.0,
        scientific_name="Turdus merula",
        common_name="Blackbird",
        label="Blackbird (Turdus merula)",
        confidence=0.95
    )
    db_session.add(det)
    db_session.commit()
    
    saved = db_session.query(Detection).first()
    assert saved.common_name == "Blackbird"
    assert saved.confidence == 0.95

def test_init_db_creates_directory(monkeypatch):
    mock_makedirs = MagicMock()
    # Mock os.makedirs
    monkeypatch.setattr("os.makedirs", mock_makedirs)
    
    # Mock config path
    with patch("src.database.config") as mock_conf:
        mock_conf.DB_PATH = "/tmp/newdir/db.sqlite"
        
        # Test directory creation
        init_db()
        
        mock_makedirs.assert_called_with("/tmp/newdir", exist_ok=True)

def test_init_db_error_handling(monkeypatch):
    mock_makedirs = MagicMock(side_effect=OSError("Permission denied"))
    monkeypatch.setattr("os.makedirs", mock_makedirs)
    
    with patch("src.database.config") as mock_conf:
        mock_conf.DB_PATH = "/root/db.sqlite"
        
        # Should raise OSError as it's not caught in init_db (or should check if it is)
        # Assuming current impl doesn't catch it
        import pytest
        with pytest.raises(OSError):
            init_db()
