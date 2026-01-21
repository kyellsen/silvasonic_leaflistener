from src.database import Detection, init_db, SessionLocal
from datetime import datetime
import os

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

def test_init_db_creates_file(tmp_path, monkeypatch):
    # Test that init_db creates directory and file
    db_file = tmp_path / "subdir" / "test.sqlite"
    
    # We need to patch config to point to this new path
    monkeypatch.setattr("src.config.config.DB_PATH", str(db_file))
    
    # Mock create_engine only if we want to avoid real connection, 
    # but for this test we want to see file creation helper logic.
    # src.database.init_db() does os.makedirs
    
    # We need to force reload or just call init_db again? 
    # init_db() relies on config.DB_PATH.
    
    # We can't easily re-run init_db globally without side effects, 
    # but we can call it and ignore the returned sessionmaker.
    
    session_maker = init_db()
    
    assert db_file.parent.exists()
    assert db_file.exists()
