from unittest.mock import MagicMock, patch

from silvasonic_birdnet.main import main, setup_logging


@patch("silvasonic_birdnet.main.WatcherService")
@patch("silvasonic_birdnet.main.setup_logging")
def test_main(mock_logging, mock_watcher_cls):
    """Test main entrypoint."""
    mock_service = MagicMock()
    mock_watcher_cls.return_value = mock_service

    main()

    mock_logging.assert_called_once()
    mock_watcher_cls.assert_called_once()
    mock_service.run.assert_called_once()


@patch("silvasonic_birdnet.main.logging.basicConfig")
@patch("silvasonic_birdnet.main.logging.handlers.TimedRotatingFileHandler")
@patch("silvasonic_birdnet.main.os.makedirs")
def test_setup_logging(mock_makedirs, mock_handler, mock_basic_config):
    """Test logging setup."""
    setup_logging()
    mock_makedirs.assert_called_with("/var/log/silvasonic", exist_ok=True)
    mock_basic_config.assert_called_once()
