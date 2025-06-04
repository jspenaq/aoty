from aoty.models import Album, Artist
from aoty.scrapers.album import AlbumScraper
from aoty.scrapers.artist import ArtistScraper


class AOTYClient:
    """
    Main client for the AOTY API, providing high-level functions to retrieve data.
    """

    def __init__(self) -> None:
        """
        Initializes the AOTYClient.
        """
        self._album_scraper = AlbumScraper()
        self._artist_scraper = ArtistScraper()

    async def get_album_by_id(self, album_id: str) -> Album | None:
        """
        Retrieves album data by album ID (REQ-001).
        """
        return await self._album_scraper.scrape_album_by_id(album_id)

    async def get_artist(self, artist_id: str) -> Artist | None:
        """
        Retrieves artist data by artist ID.
        """
        return await self._artist_scraper.scrape_artist_by_id(artist_id)

    async def close(self) -> None:
        """
        Closes the underlying HTTP client sessions for all scrapers.
        """
        await self._album_scraper.close()
        await self._artist_scraper.close()
