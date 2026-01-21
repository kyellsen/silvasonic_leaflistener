import pytest
import os
import datetime
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
from src.analyzer import BirdNETAnalyzer
from src.database import Detection

@pytest.fixture
def analyzer():
    return BirdNETAnalyzer()

class TestTimestampParsing:
    def test_parse_timestamp_valid_standard(self, analyzer):
        dt = analyzer._parse_timestamp("silvasonic_2024-01-21_12-00-00.flac")
        assert dt == datetime.datetime(2024, 1, 21, 12, 0, 0)
    
    def test_parse_timestamp_valid_compact(self, analyzer):
        dt = analyzer._parse_timestamp("20240121_120000.wav")
        assert dt == datetime.datetime(2024, 1, 21, 12, 0, 0)
        
    def test_parse_timestamp_invalid(self, analyzer):
        assert analyzer._parse_timestamp("random_file.wav") is None

class TestProcessFile:
    @patch("src.analyzer.bn_analyze")
    @patch("src.analyzer.os.symlink")
    @patch("src.analyzer.Path.exists")
    @patch("src.analyzer.Path.mkdir")
    @patch("src.analyzer.Path.unlink")
    def test_process_file_success(self, mock_unlink, mock_mkdir, mock_exists, mock_symlink, mock_bn_analyze, analyzer, db_session):
        # Setup mocks
        # Path.exists is called for:
        # 1. input file check (True)
        # 2. symlink target check (False initially)
        # 3. cleanup symlink check (True)
        # 4. cleanup param file check (False)
        mock_exists.side_effect = [True, False, True, False]
        
        # Mock BN return
        mock_bn_analyze.return_value = {
            (0.0, 3.0): [
                {'common_name': 'Blackbird', 'scientific_name': 'Turdus merula', 'confidence': 0.95, 'label': 'Blackbird (Turdus)'},
                {'common_name': 'Robin', 'scientific_name': 'Erithacus rubecula', 'confidence': 0.1} # low conf, should be ignored
            ]
        }
        
        with patch("src.analyzer.SessionLocal", return_value=db_session):
            analyzer.process_file("/data/input/silvasonic_2024-01-21_12-00-00.flac")
            
            # Verify DB interactions
            det = db_session.query(Detection).first()
            assert det is not None
            assert det.common_name == "Blackbird"
            assert det.confidence == 0.95
            assert db_session.query(Detection).count() == 1
            
            # Verify cleanups
            assert mock_unlink.called

    def test_process_file_not_found(self, analyzer):
        with patch("src.analyzer.Path.exists", return_value=False):
            # Should just return log error, no crash
            analyzer.process_file("/data/missing.wav")

    def test_process_file_exception_handling(self, analyzer):
        with patch("src.analyzer.Path.exists", return_value=True):
             with patch("src.analyzer.os.symlink", side_effect=Exception("Symlink error")):
                 # Should log error and not crash
                 analyzer.process_file("/data/broken.wav")

    @patch("src.analyzer.bn_analyze")
    @patch("src.analyzer.os.symlink")
    @patch("src.analyzer.Path.exists")
    @patch("src.analyzer.Path.mkdir")
    def test_process_file_save_error(self, mock_mkdir, mock_exists, mock_symlink, mock_bn_analyze, analyzer):
        mock_exists.return_value = True
        mock_bn_analyze.return_value = {}
        
        # Simulate DB error
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("DB Error")
        
        with patch("src.analyzer.SessionLocal", return_value=mock_session):
            analyzer.process_file("/data/input/test.wav")
            # Should fallback to rollback
            assert mock_session.rollback.called
            assert mock_session.close.called

    def test_save_detections_various_formats(self, analyzer, db_session):
        # Test handling of different prediction formats
        # 1. Dictionary format
        detections_dict = {
            (0.0, 3.0): [{'common_name': 'A', 'scientific_name': 'B', 'confidence': 0.9, 'label': 'A (B)'}]
        }
        with patch("src.analyzer.SessionLocal", return_value=db_session):
            analyzer._save_detections(detections_dict, "file.wav", datetime.datetime.utcnow())
            assert db_session.query(Detection).count() == 1
            db_session.query(Detection).delete() # clean up
            
        # 2. Tuple format (Label, Conf)
        detections_tuple = {
            (0.0, 3.0): [('Common_Scientific', 0.85)]
        }
        with patch("src.analyzer.SessionLocal", return_value=db_session):
            analyzer._save_detections(detections_tuple, "file.wav", datetime.datetime.utcnow())
            det = db_session.query(Detection).one()
            assert det.common_name == "Common"
            assert det.scientific_name == "Scientific"
            assert det.confidence == 0.85

