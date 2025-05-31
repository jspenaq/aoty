"""
AOTY API - A Python library to access data from Album of the Year website.
"""

from aoty.client import AOTYClient
# from aoty.exceptions import AOTYError, AlbumNotFoundError, ArtistNotFoundError, ConnectionError
# from aoty.models import Album, Artist, Review, NewsArticle, ChartEntry, SearchResult

__all__ = [
    "AOTYClient",
    "AOTYError",
    "AlbumNotFoundError",
    "ArtistNotFoundError",
    "ConnectionError",
    "Album",
    "Artist",
    "Review",
    "NewsArticle",
    "ChartEntry",
    "SearchResult",
]
