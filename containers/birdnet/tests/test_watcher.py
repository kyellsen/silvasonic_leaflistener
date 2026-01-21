import pytest
from unittest.mock import MagicMock, patch
from src.watcher import AudioFileHandler, WatcherService

def test_audio_file_handler():
    mock_analyzer = MagicMock()
    handler = AudioFileHandler(mock_analyzer)
    
    # Test ignored events
    event_dir = MagicMock(is_directory=True)
    handler.on_closed(event_dir)
    mock_analyzer.process_file.assert_not_called()
    
    event_txt = MagicMock(is_directory=False, src_path="test.txt")
    handler.on_closed(event_txt)
    mock_analyzer.process_file.assert_not_called()
    
    # Test valid event
    event_wav = MagicMock(is_directory=False, src_path="/data/test.wav")
    
    with patch("time.sleep"): # Skip sleep
        handler.on_closed(event_wav)
        mock_analyzer.process_file.assert_called_with("/data/test.wav")

@patch("src.watcher.Observer")
@patch("src.watcher.BirdNETAnalyzer")
@patch("src.watcher.config")
def test_watcher_service_run(mock_config, mock_analyzer_cls, mock_observer_cls):
    # Mock config
    mock_config.INPUT_DIR = MagicMock()
    mock_config.INPUT_DIR.exists.return_value = True
    
    service = WatcherService()
    
    # Mock loop to break immediately
    with patch("src.watcher.time.sleep", side_effect=KeyboardInterrupt):
        service.run()
        
    # Verify observer started and scheduled
    mock_observer_instance = mock_observer_cls.return_value
    assert mock_observer_instance.start.called
    assert mock_observer_instance.schedule.called
    assert mock_observer_instance.stop.called
