from aoty.models import Album
from aoty.scrapers.album import AlbumScraper


class AOTYClient:
    """
    Main client for the AOTY API, providing high-level functions to retrieve data.
    """

    def __init__(self) -> None:
        """
        Initializes the AOTYClient.
        """
        self._album_scraper = AlbumScraper()

    async def get_album_by_id(self, album_id: str) -> Album | None:
        """
        Retrieves album data by album ID (REQ-001).
        """
        return await self._album_scraper.scrape_album_by_id(album_id)

    async def close(self) -> None:
        """
        Closes the underlying HTTP client sessions for all scrapers.
        """
        await self._album_scraper.close()
