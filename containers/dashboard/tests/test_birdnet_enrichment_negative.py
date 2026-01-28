from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_dashboard.services.birdnet import BirdNetService


@pytest.mark.asyncio
async def test_enrich_species_data_negative_caching() -> None:
    """Test that a failed fetch results in a negative cache entry (DB insert with None)."""

    info = {"sci_name": "Ghost bird", "com_name": "Ghost"}

    mock_conn = AsyncMock()
    # First fetch: Cache Miss
    # Return a MagicMock (synchronous) for the result so fetchone() is not async
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_db_ctx.return_value.__aenter__.return_value = mock_conn

        # Mock fetch returning None (Not Found)
        with patch(
            "silvasonic_dashboard.wikimedia.WikimediaService.fetch_species_data", return_value=None
        ) as mock_fetch:
            result = await BirdNetService.enrich_species_data(info)

            # 1. External Fetch should be called
            mock_fetch.assert_called_once_with("Ghost bird")

            # 2. DB should receive an UPSERT with None values
            assert mock_conn.execute.call_count == 2  # 1 SELECT, 1 UPSERT

            # Get the kwargs of the second execute call (the upsert)
            args, _ = mock_conn.execute.call_args
            # args[1] is the params dict
            inserted_data = args[1]

            assert inserted_data["scientific_name"] == "Ghost bird"
            assert inserted_data["image_url"] is None
            assert inserted_data["description"] is None

            # 3. Result should be unchanged (no enrichment)
            assert result.get("image_url") is None


@pytest.mark.asyncio
async def test_enrich_species_data_hits_negative_cache() -> None:
    """Test that an existing negative cache entry PREVENTS external fetch."""

    info = {"sci_name": "Ghost bird", "com_name": "Ghost"}

    mock_conn = AsyncMock()
    # Cache HIT, but with empty image (Negative Cache)
    mock_row = MagicMock()
    mock_row.image_url = None
    # SQLAlchemy Row mapping
    mock_row._mapping = {
        "scientific_name": "Ghost bird",
        "image_url": None,
        "description": None,
        "last_updated": "2024-01-01",
    }

    # Return a MagicMock (sync) for the result
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_conn.execute.return_value = mock_result

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_db_ctx.return_value.__aenter__.return_value = mock_conn

        with patch(
            "silvasonic_dashboard.wikimedia.WikimediaService.fetch_species_data"
        ) as mock_fetch:
            await BirdNetService.enrich_species_data(info)

            # CRITICAL: Fetch should NOT be called
            mock_fetch.assert_not_called()
