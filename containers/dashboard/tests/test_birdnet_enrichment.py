from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_dashboard.services.birdnet import BirdNetService


@pytest.mark.asyncio
async def test_enrich_species_data_cache_hit():
    """Test that enrichment uses DB cache if available."""

    info = {"sci_name": "Turdus merula", "com_name": "Blackbird"}

    # Mock DB Connection
    mock_conn = AsyncMock()
    mock_row = MagicMock()
    mock_row._mapping = {
        "scientific_name": "Turdus merula",
        "german_name": "Amsel",
        "image_url": "cached.jpg",
        "description": "Cached desc",
        "wikipedia_url": "cached_url",
    }
    # execute is async (AsyncMock), so calling it returns a coroutine.
    # The return_value of that AsyncMock is the ResultProxy (synchronous).
    mock_result_proxy = MagicMock()
    mock_result_proxy.fetchone.return_value = mock_row
    mock_conn.execute.return_value = mock_result_proxy

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        # db.get_connection() returns a Context Manager.
        # async with db.get_connection() as conn:
        # So __aenter__ must be async (or return awaitable) and return conn.
        mock_ctx = mock_db_ctx.return_value
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        # We also mock WikimediaService to ensure it's NOT called
        with patch(
            "silvasonic_dashboard.wikimedia.WikimediaService.fetch_species_data",
            new_callable=AsyncMock,
        ) as mock_fetch:
            result = await BirdNetService.enrich_species_data(info)

            # Verify result matches cache
            assert result["german_name"] == "Amsel"
            assert result["image_url"] == "cached.jpg"

            # Verify DB was queried
            assert mock_conn.execute.call_count >= 1  # At least the SELECT

            # Verify External API was NOT called
            mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_species_data_cache_miss_success():
    """Test that enrichment fetches from Wikimedia on cache miss and updates DB."""

    info = {"sci_name": "Turdus merula", "com_name": "Blackbird"}

    # Mock DB: First fetch returns None, then we expect an INSERT/UPSERT
    mock_conn = AsyncMock()
    mock_result_proxy = MagicMock()
    mock_result_proxy.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result_proxy

    # Mock Wikimedia result
    wiki_data = {
        "scientific_name": "Turdus merula",
        "german_name": "Amsel",
        "image_url": "new.jpg",
        "description": "New desc",
        "wikipedia_url": "new_url",
        "family": None,
    }

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_ctx = mock_db_ctx.return_value
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "silvasonic_dashboard.wikimedia.WikimediaService.fetch_species_data",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = wiki_data

            result = await BirdNetService.enrich_species_data(info)

            # Verify result updated from wiki data
            assert result["german_name"] == "Amsel"
            assert result["image_url"] == "new.jpg"

            # Verify Wikimedia called
            mock_fetch.assert_called_with("Turdus merula")

            # Verify DB Insert/Upsert called
            # We expect 2 calls: 1 SELECT, 1 INSERT/UPSERT
            assert mock_conn.execute.call_count == 2

            # Basic check if COMMIT was called
            mock_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrich_species_data_cache_miss_fetch_fail():
    """Test behavior when both cache and external fetch fail."""

    info = {"sci_name": "Unknown", "com_name": "Unknown"}

    mock_conn = AsyncMock()
    mock_result_proxy = MagicMock()
    mock_result_proxy.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result_proxy

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_ctx = mock_db_ctx.return_value
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        # Mock fetch returning None
        with patch(
            "silvasonic_dashboard.wikimedia.WikimediaService.fetch_species_data",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = None

            result = await BirdNetService.enrich_species_data(info)

            # Verify info updated with None (Negative Cache)
            assert result["image_url"] is None
            assert result["description"] is None

            mock_fetch.assert_called()
            # Insert should happen (Negative Cache)
            assert mock_conn.execute.call_count == 2
            mock_conn.commit.assert_awaited_once()
