from unittest.mock import patch, MagicMock
from src.main import main

@patch("src.main.WatcherService")
@patch("src.main.init_db")
def test_main_execution(mock_init_db, mock_watcher_cls):
    mock_service = mock_watcher_cls.return_value
    
    main()
    
    assert mock_init_db.called
    assert mock_watcher_cls.called
    assert mock_service.run.called

