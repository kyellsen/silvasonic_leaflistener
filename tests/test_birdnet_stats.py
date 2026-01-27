import pytest
import datetime
from sqlalchemy import text
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.birdnet_stats import BirdNetStatsService

@pytest.mark.asyncio
async def test_get_advanced_stats_defaults():
    # Mocking the database connection and execution
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    
    # Mock daily results
    row_daily = MagicMock()
    row_daily.date = datetime.date(2023, 1, 1)
    row_daily.count = 10
    mock_result.__iter__.return_value = [row_daily]

    mock_conn.execute.return_value = mock_result

    with patch("src.services.database.db.get_connection", return_value=mock_conn):
        stats = await BirdNetStatsService.get_advanced_stats()
        
        assert "period" in stats
        assert "daily" in stats
        assert "hourly" in stats
        assert "top_species" in stats
        assert "rarest" in stats

        # Verify defaults (last 30 days)
        today = datetime.date.today()
        expected_start = (today - datetime.timedelta(days=30)).isoformat()
        assert stats["period"]["start"] == expected_start
        assert stats["period"]["end"] == today.isoformat()

@pytest.mark.asyncio
async def test_get_advanced_stats_with_dates():
    mock_conn = AsyncMock()
    # Setup minimal mocks for all queries
    mock_conn.execute.return_value = MagicMock() # Generic result

    start = datetime.date(2023, 1, 1)
    end = datetime.date(2023, 1, 7)

    with patch("src.services.database.db.get_connection", return_value=mock_conn):
        stats = await BirdNetStatsService.get_advanced_stats(start, end)
        
        assert stats["period"]["start"] == start.isoformat()
        assert stats["period"]["end"] == end.isoformat()
