from unittest.mock import AsyncMock

import pytest

from aoty.client import AOTYClient
from aoty.exceptions import AlbumNotFoundError, NetworkError


@pytest.fixture
def aoty_client():
    """Fixture to provide an AOTYClient instance with a mocked AlbumScraper."""
    client = AOTYClient()
    client._album_scraper = AsyncMock()  # Mock the album_scraper
    return client


@pytest.mark.asyncio
async def test_get_album_by_id_success(aoty_client):
    """Test successful retrieval of album data by ID."""
    # Arrange
    album_id = "123-test-album"
    expected_album = {"title": "Test Album", "artist": "Test Artist"}
    aoty_client._album_scraper.scrape_album_by_id.return_value = expected_album

    # Act
    album = await aoty_client.get_album_by_id(album_id)

    # Assert
    aoty_client._album_scraper.scrape_album_by_id.assert_called_once_with(album_id)
    assert album == expected_album


@pytest.mark.asyncio
async def test_get_album_by_id_not_found(aoty_client):
    """Test AlbumNotFoundError is raised when the album is not found."""
    # Arrange
    album_id = "999-not-found"
    aoty_client._album_scraper.scrape_album_by_id.side_effect = AlbumNotFoundError(
        "Album not found",
    )

    # Act & Assert
    with pytest.raises(AlbumNotFoundError) as excinfo:
        await aoty_client.get_album_by_id(album_id)
    assert "Album not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_album_by_id_network_error(aoty_client):
    """Test ParsingError is raised for network issues."""
    # Arrange
    album_id = "123-network-error"
    aoty_client._album_scraper.scrape_album_by_id.side_effect = NetworkError("Network error")

    # Act & Assert
    with pytest.raises(NetworkError) as excinfo:
        await aoty_client.get_album_by_id(album_id)
    assert "Network error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_album_by_id_invalid_id(aoty_client):
    """Test with an invalid album ID."""
    # Arrange
    album_id = "invalid-id"
    aoty_client._album_scraper.scrape_album_by_id.return_value = None

    # Act
    album = await aoty_client.get_album_by_id(album_id)

    # Assert
    aoty_client._album_scraper.scrape_album_by_id.assert_called_once_with(album_id)
    assert album is None


@pytest.mark.asyncio
async def test_close(aoty_client):
    """Test that the close method calls the album scraper's close method."""
    # Act
    await aoty_client.close()

    # Assert
    aoty_client._album_scraper.close.assert_called_once()
