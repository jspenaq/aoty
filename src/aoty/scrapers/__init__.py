"""
This package contains individual scraper modules for different sections
of the Album of the Year website.
"""
from .album import AlbumScraper
# from .news import NewsScraper # This import was not in the original __init__.py, but was in the user's proposed change. I will add it to match the proposed change.
# from .song import SongScraper # This import was not in the original __init__.py, but was in the user's proposed change. I will add it to match the proposed change.
# from .artist import ArtistScraper

__all__ = ["AlbumScraper"] # I will only include the scrapers that are actually present in the provided files. NewsScraper and SongScraper are not present.
