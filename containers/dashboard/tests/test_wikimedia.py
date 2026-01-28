from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_dashboard.wikimedia import WikimediaService


@pytest.mark.asyncio
async def test_fetch_species_data_success():
    """Test successful fetch of species data from Wikimedia."""
    # Mock data returned by Wikipedia API
    mock_response_data = {
        "query": {
            "pages": {
                "123": {
                    "pageid": 123,
                    "title": "Turdus merula",
                    "thumbnail": {"source": "http://example.com/image.jpg"},
                    "extract": "The common blackbird is a species of true thrush.",
                    "langlinks": [{"lang": "de", "*": "Amsel"}],
                }
            }
        }
    }

    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        # __aenter__ must be awaitable
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_client.get = AsyncMock(return_value=mock_response)

        # Execute
        result = await WikimediaService.fetch_species_data("Turdus merula")

        # Verify
        assert result is not None
        assert result["scientific_name"] == "Turdus merula"
        assert result["german_name"] == "Amsel"
        assert result["image_url"] == "http://example.com/image.jpg"
        assert result["description"] == "The common blackbird is a species of true thrush."
        assert result["wikipedia_url"] == "https://en.wikipedia.org/?curid=123"


@pytest.mark.asyncio
async def test_fetch_species_data_no_german_name():
    """Test fetch where German name is missing (fallback to sci name)."""
    mock_response_data = {
        "query": {
            "pages": {
                "123": {
                    "pageid": 123,
                    "title": "Turdus merula",
                    "extract": "Description.",
                    # No langlinks
                }
            }
        }
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await WikimediaService.fetch_species_data("Turdus merula")

        assert result is not None
        assert result["german_name"] == "Turdus merula"  # Fallback


@pytest.mark.asyncio
async def test_fetch_species_data_not_found():
    """Test when Wikipedia returns -1 (page not found)."""
    mock_response_data = {
        "query": {"pages": {"-1": {"ns": 0, "title": "Unknown bird", "missing": ""}}}
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await WikimediaService.fetch_species_data("Unknown bird")

        assert result is None


@pytest.mark.asyncio
async def test_fetch_species_data_http_error():
    """Test execution when HTTP request fails."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Simulate exception
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

        result = await WikimediaService.fetch_species_data("Turdus merula")

        assert result is None
