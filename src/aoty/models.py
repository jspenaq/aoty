from typing import List, Dict, Optional, TypedDict


class AlbumCredit(TypedDict, total=False):
    """Represents a credit (producer, writer, vocalist, etc.) for an album or song."""

    name: str
    url: Optional[str]
    role: str  # e.g., "Producer", "Writer", "Vocals", "Songwriter"


class AlbumLink(TypedDict):
    """Represents a third-party link for an album (Spotify, Apple Music, Amazon, etc.)."""

    name: str
    url: str


class Track(TypedDict):
    """Represents a single track in an album's tracklist."""

    number: int
    title: str
    url: Optional[str]
    duration: Optional[str]
    featured_artists: Optional[List[Dict[str, str]]]  # [{"name": "...", "url": "..."}]
    rating: Optional[float]
    rating_count: Optional[int]


class CriticReview(TypedDict):
    """Represents a critic review for an album."""

    publication_name: str
    publication_url: Optional[str]
    author_name: Optional[str]
    author_url: Optional[str]
    score: float
    text: Optional[str]
    url: Optional[str]
    date: Optional[str]


class Review(TypedDict):
    """Represents a user review for an album."""

    username: str
    user_url: Optional[str]
    rating: float
    text: str
    date: Optional[str]
    likes: Optional[int]
    comment_count: Optional[int]


class SongDetails(TypedDict):
    """Represents a detailed view of a song from its dedicated page."""

    title: str
    artists: List[
        Dict[str, str]
    ]  # Main artist(s) of the song, e.g., [{"name": "RM", "url": "/artist/..."}]
    album_title: Optional[str]
    album_url: Optional[str]
    cover_url: Optional[str]
    year: Optional[int]
    duration: Optional[str]
    user_score: Optional[float]
    user_rating_count: Optional[int]
    credits: Optional[List[AlbumCredit]]  # Reusing AlbumCredit for song-specific roles
    description: Optional[str]
    url: str
    id: Optional[int]
    track_number_on_album: Optional[int]  # The track number if it belongs to an album


class Album(TypedDict):
    """Represents an album."""

    title: str
    artist: str
    cover_url: Optional[str]
    year: Optional[int]
    critic_score: Optional[float]
    critic_review_count: Optional[int]
    critic_rank_year: Optional[int]
    critic_rank_year_total: Optional[int]
    user_score: Optional[float]
    user_rating_count: Optional[int]
    user_rank_year: Optional[int]
    release_date: Optional[str]
    format: Optional[str]
    labels: Optional[List[Dict[str, str]]]  # [{"name": "...", "url": "..."}]
    genres: List[str]
    producers: Optional[List[Dict[str, str]]]  # [{"name": "...", "url": "..."}]
    writers: Optional[List[Dict[str, str]]]  # [{"name": "...", "url": "..."}]
    credits: Optional[List[AlbumCredit]]
    tracklist: Optional[List[Track]]
    total_length: Optional[str]
    links: Optional[List[AlbumLink]]
    similar_albums: Optional[
        List[Dict[str, str]]
    ]  # [{"title": "...", "artist": "...", "url": "..."}]
    more_by_artist: Optional[
        List[Dict[str, str]]
    ]  # [{"title": "...", "year": ..., "url": "..."}]
    critic_reviews: Optional[List[CriticReview]]
    popular_user_reviews: Optional[List[Review]]
    recent_user_reviews: Optional[List[Review]]
    contributions_by: Optional[List[Dict[str, str]]]  # [{"name": "...", "url": "..."}]
    description: Optional[str]
    url: str
    id: Optional[int]  # Can be derived from URL


class Artist(TypedDict):
    """Represents an artist."""

    name: str
    genres: List[str]
    associated_albums: List[Dict[str, str]]  # List of {"title": "...", "url": "..."}
    url: str
    id: Optional[int]  # Can be derived from URL


class NewsArticle(TypedDict):
    """Represents a news article."""

    title: str
    url: str
    publication_date: str


class ChartEntry(TypedDict):
    """Represents an entry in a chart."""

    album_title: str
    artist: str
    score: float
    url: str


class SearchResult(TypedDict):
    """Represents search results."""

    albums: List[Album]
    artists: List[Artist]
    news_articles: List[NewsArticle]
    # Potentially add pagination info if needed
