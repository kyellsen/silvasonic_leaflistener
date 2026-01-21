from unittest.mock import patch, MagicMock
from src.main import main

@patch("src.main.WatcherService")
@patch("src.main.init_db")
def test_main(mock_init_db, mock_watcher_cls):
    mock_service_instance = mock_watcher_cls.return_value
    
    main()
    
    assert mock_init_db.called
    assert mock_service_instance.run.called
