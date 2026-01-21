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

def test_init_db_creates_directory(tmp_path, monkeypatch):
    # Use a real temp path, don't mock makedirs
    db_file = tmp_path / "newdir" / "db.sqlite"
    
    # Needs to patch config before init_db is called? 
    # init_db() reads config.DB_PATH.
    
    # We patch the CONFIG definition if possible, or the imported module attribute.
    # Since init_db imports config, we patch `src.database.config`.
    with patch("src.database.config") as mock_conf:
        mock_conf.DB_PATH = db_file
        
        # Test directory creation
        init_db()
        
        assert db_file.parent.exists()

def test_init_db_error_handling(monkeypatch):
    # Here we mock makedirs to force error
    mock_makedirs = MagicMock(side_effect=OSError("Permission denied"))
    monkeypatch.setattr("os.makedirs", mock_makedirs)
    
    with patch("src.database.config") as mock_conf:
        # Path doesn't matter as makedirs is mocked
        mock_conf.DB_PATH = "/root/db.sqlite"
        
        import pytest
        with pytest.raises(OSError):
            init_db()
