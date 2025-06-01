from typing import TypedDict


class AlbumCredit(TypedDict, total=False):
    """Represents a credit (producer, writer, vocalist, etc.) for an album or song."""

    name: str
    url: str | None
    role: str  # e.g., "Producer", "Writer", "Vocals", "Songwriter"


class AlbumLink(TypedDict):
    """Represents a third-party link for an album (Spotify, Apple Music, Amazon, etc.)."""

    name: str
    url: str


class Track(TypedDict):
    """Represents a single track in an album's tracklist."""

    number: int
    title: str
    url: str | None
    duration: str | None
    featured_artists: list[dict[str, str]] | None  # [{"name": "...", "url": "..."}]
    rating: float | None
    rating_count: int | None


class CriticReview(TypedDict):
    """Represents a critic review for an album."""

    publication_name: str
    publication_url: str | None
    author_name: str | None
    author_url: str | None
    score: float
    text: str | None
    url: str | None
    date: str | None


class Review(TypedDict):
    """Represents a user review for an album."""

    username: str
    user_url: str | None
    rating: float
    text: str
    date: str | None
    likes: int | None
    comment_count: int | None


class UserRating(TypedDict):
    """Represents a user's rating for an album (without a full review text)."""

    username: str
    user_url: str | None
    rating: float
    date: str | None


class SongDetails(TypedDict):
    """Represents a detailed view of a song from its dedicated page."""

    title: str
    artists: list[
        dict[str, str]
    ]  # Main artist(s) of the song, e.g., [{"name": "RM", "url": "/artist/..."}]
    album_title: str | None
    album_url: str | None
    cover_url: str | None
    year: int | None
    duration: str | None
    user_score: float | None
    user_rating_count: int | None
    credits: list[AlbumCredit] | None  # Reusing AlbumCredit for song-specific roles
    url: str
    id: int | None
    track_number_on_album: int | None  # The track number if it belongs to an album


class Album(TypedDict):
    """Represents an album."""

    title: str
    artist: str
    cover_url: str | None
    year: int | None
    critic_score: float | None
    critic_review_count: int | None
    critic_rank_year: int | None
    critic_rank_year_total: int | None
    user_score: float | None
    user_rating_count: int | None
    user_rank_year: int | None
    release_date: str | None
    format: str | None
    labels: list[dict[str, str]] | None  # [{"name": "...", "url": "..."}]
    genres: list[str]
    producers: list[dict[str, str]] | None  # [{"name": "...", "url": "..."}]
    writers: list[dict[str, str]] | None  # [{"name": "...", "url": "..."}]
    credits: list[AlbumCredit] | None
    tracklist: list[Track] | None
    total_length: str | None
    links: list[AlbumLink] | None
    similar_albums: list[dict[str, str]] | None  # [{"title": "...", "artist": "...", "url": "..."}]
    more_by_artist: list[dict[str, str]] | None  # [{"title": "...", "year": ..., "url": "..."}]
    critic_reviews: list[CriticReview] | None
    popular_user_reviews: list[Review] | None
    recent_user_reviews: list[Review] | None
    contributions_by: list[dict[str, str]] | None  # [{"name": "...", "url": "..."}]
    url: str
    id: int | None  # Can be derived from URL


class Artist(TypedDict):
    """Represents an artist."""

    name: str
    genres: list[str]
    associated_albums: list[dict[str, str]]  # List of {"title": "...", "url": "..."}
    url: str
    id: int | None  # Can be derived from URL


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

    albums: list[Album]
    artists: list[Artist]
    news_articles: list[NewsArticle]
    # Potentially add pagination info if needed
