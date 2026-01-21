import sys
from unittest.mock import MagicMock

# Mock dependencies that might be missing in the test env
sys.modules["soundfile"] = MagicMock()
sys.modules["birdnet_analyzer"] = MagicMock()
sys.modules["birdnet_analyzer.analyze"] = MagicMock()

import pytest
import os
import datetime
import numpy as np
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
    @patch("src.analyzer.subprocess.run")
    @patch("src.analyzer.Path.exists")
    @patch("src.analyzer.Path.mkdir")
    @patch("src.analyzer.Path.unlink")
    @patch("src.analyzer.sf.read")
    @patch("src.analyzer.sf.info")
    def test_process_file_success(self, mock_sf_info, mock_sf_read, mock_unlink, mock_mkdir, mock_exists, mock_run, mock_bn_analyze, analyzer, db_session):
        # Setup mocks
        mock_exists.return_value = True
        mock_sf_read.return_value = (np.zeros(48000), 48000) # data, rate
        mock_sf_info.return_value = MagicMock(samplerate=48000, channels=1, duration=10.0, format='WAV')
        
        # Mock BN return - NOW it's a function on the module
        mock_bn_analyze.analyze.return_value = {
            (0.0, 3.0): [
                {'common_name': 'Blackbird', 'scientific_name': 'Turdus merula', 'confidence': 0.95, 'label': 'Blackbird (Turdus)'},
                {'common_name': 'Robin', 'scientific_name': 'Erithacus rubecula', 'confidence': 0.1} # low conf, should be ignored
            ]
        }
    
        with patch("src.analyzer.SessionLocal", return_value=db_session), \
             patch.object(analyzer, '_export_to_csv') as mock_export:
            
            analyzer.process_file("/data/input/silvasonic_2024-01-21_12-00-00.flac")
    
            # Verify DB interactions
            det = db_session.query(Detection).first()
            assert det is not None
            assert det.common_name == "Blackbird"
            assert det.confidence == 0.95
            assert db_session.query(Detection).count() == 1
            
            # Verify cleanups and export
            assert mock_unlink.called
            assert mock_run.called
            assert mock_export.called # Verify CSV was exported
            # Verify API called correctly
            mock_bn_analyze.analyze.assert_called_once()

    def test_process_file_not_found(self, analyzer):
        with patch("src.analyzer.Path.exists", return_value=False):
            # Should just return log error, no crash
            analyzer.process_file("/data/missing.wav")

    def test_process_file_exception_handling(self, analyzer):
        with patch("src.analyzer.Path.exists", return_value=True):
             with patch("src.analyzer.subprocess.run", side_effect=Exception("FFmpeg error")):
                 # Should log error and not crash
                 analyzer.process_file("/data/broken.wav")

    @patch("src.analyzer.bn_analyze")
    @patch("src.analyzer.subprocess.run")
    @patch("src.analyzer.Path.exists")
    @patch("src.analyzer.Path.mkdir")
    @patch("src.analyzer.Path.unlink")
    @patch("src.analyzer.sf.read")
    @patch("src.analyzer.sf.info")
    def test_process_file_save_error(self, mock_sf_info, mock_sf_read, mock_unlink, mock_mkdir, mock_exists, mock_run, mock_bn_analyze, analyzer):
        mock_exists.return_value = True
        mock_sf_read.return_value = (np.zeros(48000), 48000)
        mock_sf_info.return_value = MagicMock(samplerate=48000, channels=1, duration=10.0, format='WAV')

        mock_bn_analyze.analyze.return_value = {}
        
        # Simulate DB error
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("DB Error")
        
        with patch("src.analyzer.SessionLocal", return_value=mock_session), \
             patch.object(analyzer, '_export_to_csv'):
            
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

