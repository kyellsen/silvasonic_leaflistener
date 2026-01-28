import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_dashboard.services.birdnet import BirdNetService


@pytest.mark.asyncio
async def test_get_recent_detections_triggers_enrichment():
    """Test that fetching recent detections triggers enrichment for species with missing images."""

    # Mock DB Result
    mock_conn = AsyncMock()

    # 1. First query: detections
    mock_det_row = MagicMock()
    mock_det_row._mapping = {
        "filepath": "/rec/bird.wav",
        "start_time": 0,
        "end_time": 1,
        "confidence": 0.9,
        "com_name": "Blackbird",
        "sci_name": "Turdus merula",
        "timestamp": datetime.datetime(2023, 1, 1, 12, 0, 0),
        "filename": "bird.wav",
        "clip_path": None,
        "german_name": None,
        "image_url": None,  # Missing image!
        "description": None,
    }

    # execute() returns a ResultProxy which is iterable
    mock_result = MagicMock()
    mock_result.__iter__.return_value = [mock_det_row]
    mock_conn.execute.return_value = mock_result

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_ctx = mock_db_ctx.return_value
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        # Mock enrich_species_data to return enriched data
        enriched_info = {
            "sci_name": "Turdus merula",
            "com_name": "Blackbird",
            "image_url": "enriched.jpg",
            "description": "Enriched desc",
            "german_name": "Amsel",
        }

        with patch(
            "silvasonic_dashboard.services.birdnet.BirdNetService.enrich_species_data",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = enriched_info

            detections = await BirdNetService.get_recent_detections(limit=1)

            # Verify enrichment was called
            mock_enrich.assert_awaited_once()
            args, _ = mock_enrich.call_args
            assert args[0]["sci_name"] == "Turdus merula"

            # Verify the returned detection has the NEW data
            assert len(detections) == 1
            d = detections[0]
            assert d["image_url"] == "enriched.jpg"
            assert d["description"] == "Enriched desc"
            assert d["german_name"] == "Amsel"


@pytest.mark.asyncio
async def test_get_all_species_triggers_enrichment():
    """Test that get_all_species triggers enrichment for missing images."""

    mock_conn = AsyncMock()

    # Mock row
    mock_row = MagicMock()
    mock_row._mapping = {
        "com_name": "Blackbird",
        "sci_name": "Turdus merula",
        "count": 10,
        "last_seen": datetime.datetime(2023, 1, 1),
        "first_seen": datetime.datetime(2023, 1, 1),
        "avg_conf": 0.9,
        "image_url": None,  # Missing!
        "german_name": None,
    }

    mock_result = MagicMock()
    mock_result.__iter__.return_value = [mock_row]
    mock_conn.execute.return_value = mock_result

    with patch("silvasonic_dashboard.services.birdnet.db.get_connection") as mock_db_ctx:
        mock_ctx = mock_db_ctx.return_value
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        # Mock enrich_species_data
        # Mock enrich_species_data

        with patch(
            "silvasonic_dashboard.services.birdnet.BirdNetService.enrich_species_data",
            new_callable=AsyncMock,
        ) as mock_enrich:
            species_list = await BirdNetService.get_all_species()

            # Verify enrichment called
            mock_enrich.assert_awaited_once()

            # In get_all_species, the enrichment happens in background/parallel (asyncio.gather),
            # but it doesn't strictly update the returned list 'species' in place with the result of gather
            # UNLESS it modifies the dicts in 'to_enrich' list which are references to dicts in 'species' list.
            # Wait, let's check code:
            # to_enrich.append(d) -> d is from species.append(d). So yes, references needed.
            # Code: await asyncio.gather(*[BirdNetService.enrich_species_data(sp) for sp in to_enrich])
            # enrich_species_data modifies 'sp' in place?
            # Code:
            # def enrich_species_data(info): ... info["german_name"] = ... return info
            # Yes, it modifies 'info' (which is 'sp') in place.

            # BUT: our mock needs to modify the input dictionary to simulate this side effect!
            # Mock return_value doesn't do that automatically.

            # We need side_effect
            async def side_effect(info):
                info["image_url"] = "enriched_side_effect.jpg"
                return info

            mock_enrich.side_effect = side_effect

            species_list = await BirdNetService.get_all_species()

            assert len(species_list) == 1
            assert species_list[0]["image_url"] == "enriched_side_effect.jpg"
