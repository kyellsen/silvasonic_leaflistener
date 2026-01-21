import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from src.analyzer import BirdNETAnalyzer
from src.database import Detection

@pytest.fixture
def analyzer():
    return BirdNETAnalyzer()

def test_parse_timestamp(analyzer):
    # Test valid formats
    dt1 = analyzer._parse_timestamp("silvasonic_2024-01-21_12-00-00.flac")
    assert dt1 == datetime(2024, 1, 21, 12, 0, 0)
    
    dt2 = analyzer._parse_timestamp("20240121_120000.wav")
    assert dt2 == datetime(2024, 1, 21, 12, 0, 0)
    
    # Test invalid
    assert analyzer._parse_timestamp("random_file.wav") is None

@patch("src.analyzer.bn_analyze")
@patch("src.analyzer.os.symlink")
@patch("src.analyzer.Path.exists")
@patch("src.analyzer.Path.mkdir")
def test_process_file_success(mock_mkdir, mock_exists, mock_symlink, mock_bn_analyze, analyzer, db_session):
    # Setup mocks
    mock_exists.return_value = True # File exists
    
    # Mock BN return
    # Dictionary format: {(start, end): [prediction_list]}
    mock_bn_analyze.return_value = {
        (0.0, 3.0): [
            {'common_name': 'Blackbird', 'scientific_name': 'Turdus merula', 'confidence': 0.95, 'label': 'Blackbird (Turdus)'},
            {'common_name': 'Robin', 'scientific_name': 'Erithacus rubecula', 'confidence': 0.1} # low conf
        ]
    }
    
    # Patch SessionLocal to return our test db_session
    with patch("src.analyzer.SessionLocal", return_value=db_session):
        analyzer.process_file("/data/input/silvasonic_2024-01-21_12-00-00.flac")
        
        # Verify DB interactions
        det = db_session.query(Detection).first()
        assert det is not None
        assert det.common_name == "Blackbird"
        assert det.confidence == 0.95
        
        # Ensure low confidence one was skipped (config default 0.7)
        assert db_session.query(Detection).count() == 1

def test_process_file_not_found(analyzer):
    with patch("src.analyzer.Path.exists", return_value=False):
        # Should just return log error, no crash
        analyzer.process_file("/data/missing.wav")

def test_process_file_exception_handling(analyzer):
    with patch("src.analyzer.Path.exists", return_value=True):
        with patch("src.analyzer.bn_analyze", side_effect=Exception("BnError")):
             # Should log error and not crash
             analyzer.process_file("/data/broken.wav")
