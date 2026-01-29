from unittest.mock import patch

from silvasonic_birdnet.main import main


@patch("silvasonic_birdnet.main.db")
@patch("silvasonic_birdnet.main.BirdNETAnalyzer")
@patch("silvasonic_birdnet.main.time.sleep")
@patch("silvasonic_birdnet.main.shutdown_event")
def test_main_loop(mock_shutdown, mock_sleep, mock_analyzer_cls, mock_db):
    """Test main analysis loop."""
    # Setup mocks
    mock_db.connect.return_value = True

    # Mock shutdown to run loop once then exit
    # is_set side effect: False (start), True (end)
    mock_shutdown.is_set.side_effect = [False, True]

    # Mock pending analysis to return one item
    mock_db.get_pending_analysis.return_value = [
        {"id": 123, "path_low": "test.wav", "path_high": None}
    ]

    mock_analyzer = mock_analyzer_cls.return_value

    # Run
    main()

    # Verify
    mock_db.connect.assert_called_once()
    mock_analyzer_cls.assert_called_once()
    mock_db.get_pending_analysis.assert_called_with(limit=1)
    mock_analyzer.process_file.assert_called_with("test.wav")
    mock_db.mark_analyzed.assert_called_with(123)


@patch("silvasonic_birdnet.main.db")
@patch("silvasonic_birdnet.main.BirdNETAnalyzer")
@patch("silvasonic_birdnet.main.sys.exit")
def test_main_db_fail(mock_exit, mock_analyzer, mock_db):
    """Test main exits if DB fails."""
    mock_db.connect.return_value = False

    main()

    # mock_exit.assert_called_with(1) # sys.exit usually raises SystemExit
    # If we mocked it, it captured the call.
    mock_exit.assert_called_once_with(1)
