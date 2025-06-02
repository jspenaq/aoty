"""
This package contains individual scraper modules for different sections
of the Album of the Year website.
"""

from aoty.scrapers.album import AlbumScraper
from aoty.scrapers.artist import ArtistScraper
from aoty.scrapers.news import NewsScraper

__all__ = [
    "AlbumScraper",
    "ArtistScraper",
    "NewsScraper",
]
