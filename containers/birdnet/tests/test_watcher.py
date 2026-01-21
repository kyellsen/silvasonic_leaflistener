import pytest
import time
from unittest.mock import MagicMock, patch
from src.watcher import AudioFileHandler, WatcherService

class TestAudioFileHandler:
    @pytest.fixture
    def handler(self):
        self.mock_analyzer = MagicMock()
        return AudioFileHandler(self.mock_analyzer)

    def test_ignore_directories(self, handler):
        event = MagicMock(is_directory=True)
        handler.on_closed(event)
        handler.analyzer.process_file.assert_not_called()

    def test_ignore_non_audio(self, handler):
        event = MagicMock(is_directory=False, src_path="test.txt")
        handler.on_closed(event)
        handler.analyzer.process_file.assert_not_called()

    def test_process_valid_file(self, handler):
        event = MagicMock(is_directory=False, src_path="/data/test.wav")
        # Mock time.sleep to run instantly
        with patch("time.sleep"):
            handler.on_closed(event)
        handler.analyzer.process_file.assert_called_with("/data/test.wav")

class TestWatcherService:
    @patch("src.watcher.Observer")
    @patch("src.watcher.BirdNETAnalyzer")
    @patch("src.watcher.config")
    def test_service_lifecycle(self, mock_config, mock_analyzer_cls, mock_observer_cls):
        # Setup mocks
        mock_config.INPUT_DIR = "/data/input"
        mock_config.RECURSIVE_WATCH = False
        
        # Mock observer instance
        mock_observer = mock_observer_cls.return_value
        
        service = WatcherService()
        
        # Test successful start and interrupt
        with patch("src.watcher.time.sleep", side_effect=[None, KeyboardInterrupt]):
            service.run()
            
        mock_observer.schedule.assert_called()
        # Verify args to schedule
        args, kwargs = mock_observer.schedule.call_args
        # args[0] is handler, args[1] is path
        assert args[1] == "/data/input"
        assert kwargs['recursive'] is False
        
        assert mock_observer.start.called
        assert mock_observer.stop.called
        assert mock_observer.join.called

    @patch("src.watcher.Observer")
    @patch("src.watcher.config")
    def test_service_recursive_config(self, mock_config, mock_observer_cls):
        mock_config.RECURSIVE_WATCH = True
        service = WatcherService()
        
        # Use simple mock to just check schedule call
        with patch("src.watcher.time.sleep", side_effect=KeyboardInterrupt):
            service.run()
            
        _, kwargs = mock_observer_cls.return_value.schedule.call_args
        assert kwargs['recursive'] is True

