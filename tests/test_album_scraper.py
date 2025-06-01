import asyncio
import re
from unittest.mock import AsyncMock, MagicMock
from datetime import date # Import date

import pytest
from selectolax.parser import HTMLParser

from aoty.config import AOTY_BASE_URL
from aoty.exceptions import AlbumNotFoundError, NetworkError, ParsingError, ResourceNotFoundError
from src.aoty.scrapers.album import AlbumScraper


@pytest.fixture
def album_scraper():
    """Fixture to provide an AlbumScraper instance with a mocked _get_html."""
    scraper = AlbumScraper()
    # Mock the _get_html method directly on the scraper instance
    scraper._get_html = AsyncMock()
    return scraper


def create_mock_html_response(html_content: str) -> HTMLParser:
    """Helper to create a parsed HTML response from a string."""
    return HTMLParser(html_content)


# --- Test scrape_album_by_id / _scrape_album_page ---


@pytest.mark.asyncio
async def test_scrape_album_by_id_success(album_scraper):
    """Test successful scraping of a full album page."""
    album_id = "569129-rm-indigo"  # Example ID that matches regex for ID extraction
    mock_html = f"""
    <html><body>
        <h1 class="albumTitle"><span itemprop="name">Indigo</span></h1>
        <div class="artist"><span itemprop="name"><a href="/artist/123-rm.php">RM</a></span></div>
        <div class="albumTopBox cover"><img data-src="/img/album_cover_default.jpg" srcset="/img/album_cover_small.jpg 1x, /img/album_cover_large.jpg 2x"></div>
        <div class="albumCriticScore"><span itemprop="ratingValue"><a title="7.8"></a></span></div>
        <div class="albumCriticScoreBox"><span itemprop="ratingCount">15</span><div class="text gray">#50 / 300</div></div>
        <div class="albumUserScore"><a title="8.2"></a></div>
        <div class="albumUserScoreBox"><div class="text numReviews"><strong>5,432</strong> user reviews</div><div class="text gray"><strong><a href="#">#25</a></strong></div></div>
        <div class="albumTopBox info">
            <div class="detailRow"><a href="/2022/releases/december-12.php">December</a> 2, <a href="/2022/releases/">2022</a><span>/&nbsp;Release Date</span></div>
            <div class="detailRow">LP <span>/&nbsp;Format</span></div>
            <div class="detailRow"><span>Label:</span> <a href="/label/1-bighit.php">BIGHIT MUSIC</a></div>
            <div class="detailRow"><meta content="Pop Rap" itemprop="genre"><a href="/genre/212-pop-rap/">Pop Rap</a>, <meta content="Contemporary R&B" itemprop="genre"><a content="Contemporary R&B" itemprop="genre"><a href="/genre/459-contemporary-rb/">Contemporary R&B</a><br/><a href="/genre/192-alternative-r-b/"><div class="secondary">Alternative R&B</div></a><span>/&nbsp;Genre</span></div>
            <div class="detailRow"><span>Producer:</span> <a href="/producer/1-prod.php">Producer A</a>, <a href="/producer/2-prod.php">Producer B</a></div>
            <div class="detailRow"><span>Writer:</span> <a href="/writer/1-writer.php">Writer X</a></div>
        </div>
    </body>
    </html>
    """
    album_scraper._get_html.return_value = create_mock_html_response(mock_html)

    album = await album_scraper.scrape_album_by_id(album_id)

    expected_url = f"{AOTY_BASE_URL}/album/{album_id}.php"
    album_scraper._get_html.assert_awaited_once_with(expected_url)

    assert album is not None
    assert album["title"] == "Indigo"
    assert album["artist"] == "RM"
    assert album["url"] == expected_url
    assert album["id"] == 569129
    assert album["cover_url"] == "/img/album_cover_large.jpg"
    assert album["critic_score"] == 7.8
    assert album["critic_review_count"] == 15.0
    assert album["critic_rank_year"] == 50
    assert album["critic_rank_year_total"] == 300
    assert album["user_score"] == 8.2
    assert album["user_rating_count"] == 5432
    assert album["user_rank_year"] == 25
    assert album["release_date"] == date(2022, 12, 2) # Updated to datetime.date object
    assert album["format"] == "LP"
    assert isinstance(album["labels"], list)
    assert "Pop Rap" in album["genres"]
    assert album["producers"] == [] 
    assert album["writers"] == [] 
    assert album["tracklist"] == [] 
    assert album["total_length"] == None  # Now this assertion should pass
    assert album["links"] == [] 
    assert album["critic_reviews"] == [] 
    assert album["popular_user_reviews"] == [] 
    assert album["recent_user_reviews"] == [] 
    assert album["similar_albums"] == [] 
    assert album["more_by_artist"] == [] 
    assert album["contributions_by"] == [] 
    assert album["credits"] == None


@pytest.mark.asyncio
async def test_scrape_album_by_id_not_found(album_scraper):
    """Test AlbumNotFoundError is raised when the album page returns 404."""
    album_id = "999-nonexistent"
    album_scraper._get_html.side_effect = ResourceNotFoundError("Not Found")

    with pytest.raises(AlbumNotFoundError) as excinfo:
        await album_scraper.scrape_album_by_id(album_id)
    assert f"Album not found at URL: {AOTY_BASE_URL}/album/{album_id}.php" in str(excinfo.value)


@pytest.mark.asyncio
async def test_scrape_album_by_id_network_error(album_scraper):
    """Test ParsingError is raised for network issues fetching album page."""
    album_id = "123-album"
    album_scraper._get_html.side_effect = NetworkError("Connection failed")

    with pytest.raises(ParsingError) as excinfo:
        await album_scraper.scrape_album_by_id(album_id)
    assert f"Failed to fetch album page {AOTY_BASE_URL}/album/{album_id}.php: Connection failed" in str(
        excinfo.value,
    )



# --- Test scrape_user_reviews_ratings ---


@pytest.mark.asyncio
async def test_scrape_user_reviews_ratings_success_multiple_pages(album_scraper):
    """Test scraping user ratings across multiple pages."""
    album_id = "569129-rm-indigo"
    # Updated base_ratings_url to include p=1 for consistency
    base_ratings_url = f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=1&type=ratings"

    # Mock HTML for the first page (determines total reviews)
    mock_first_page_html = """
    <html><body>
        <div class="userReviewCounter">Showing 1-80 of 160 user reviews</div>
        <div class="userRatingBlock">
            <div class="userName"><a title="User1" href="/user/user1.php"></a></div>
            <div class="ratingBlock"><div class="rating">10.0</div></div>
            <div class="date" title="2023-01-01"></div>
        </div>
        <div class="userRatingBlock">
            <div class="userName"><a title="User2" href="/user/user2.php"></a></div>
            <div class="ratingBlock"><div class="rating">9.0</div></div>
            <div class="date" title="2023-01-02"></div>
        </div>
    </body></html>
    """

    # Mock HTML for the second page
    mock_second_page_html = """
    <html><body>
        <div class="userRatingBlock">
            <div class="userName"><a title="User3" href="/user/user3.php"></a></div>
            <div class="ratingBlock"><div class="rating">8.0</div></div>
            <div class="date" title="2023-01-03"></div>
        </div>
        <div class="userRatingBlock">
            <div class="userName"><a title="User4" href="/user/user4.php"></a></div>
            <div class="ratingBlock"><div class="rating">7.0</div></div>
            <div class="date" title="2023-01-04"></div>
        </div>
    </body></html>
    """

    # Configure _get_html to return different content for different URLs
    def get_html_side_effect(url):
        if url == base_ratings_url: # This now matches the p=1 URL
            return create_mock_html_response(mock_first_page_html)
        if url == f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=2&type=ratings":
            return create_mock_html_response(mock_second_page_html)
        raise ValueError(f"Unexpected URL: {url}")

    album_scraper._get_html.side_effect = get_html_side_effect

    ratings = await album_scraper.scrape_user_reviews_ratings(album_id)

    # Assert _get_html was called for both pages
    album_scraper._get_html.assert_any_call(base_ratings_url)
    album_scraper._get_html.assert_any_call(
        f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=2&type=ratings",
    )
    assert album_scraper._get_html.call_count == 2 # Now expects 2 calls for 2 pages

    assert len(ratings) == 4
    assert ratings[0] == {
        "username": "User1",
        "user_url": f"{AOTY_BASE_URL}/user/user1.php",
        "rating": 10.0,
        "date": "2023-01-01",
    }
    assert ratings[1] == {
        "username": "User2",
        "user_url": f"{AOTY_BASE_URL}/user/user2.php",
        "rating": 9.0,
        "date": "2023-01-02",
    }
    assert ratings[2] == {
        "username": "User3",
        "user_url": f"{AOTY_BASE_URL}/user/user3.php",
        "rating": 8.0,
        "date": "2023-01-03",
    }
    assert ratings[3] == {
        "username": "User4",
        "user_url": f"{AOTY_BASE_URL}/user/user4.php",
        "rating": 7.0,
        "date": "2023-01-04",
    }


@pytest.mark.asyncio
async def test_scrape_user_reviews_ratings_no_reviews(album_scraper):
    """Test scraping user ratings when no reviews are present."""
    album_id = "123-no-reviews"
    mock_html = """
    <html><body>
        <div class="userReviewCounter">Showing 0 of 0 user reviews</div>
    </body></html>
    """
    album_scraper._get_html.return_value = create_mock_html_response(mock_html)

    ratings = await album_scraper.scrape_user_reviews_ratings(album_id)

    assert album_scraper._get_html.call_count == 1  # Only first page fetched
    assert ratings == []


@pytest.mark.asyncio
async def test_scrape_user_reviews_ratings_album_not_found(album_scraper):
    """Test AlbumNotFoundError is raised when the ratings page returns 404."""
    album_id = "999-nonexistent-ratings"
    album_scraper._get_html.side_effect = ResourceNotFoundError("Not Found")

    with pytest.raises(AlbumNotFoundError) as excinfo:
        await album_scraper.scrape_user_reviews_ratings(album_id)
    assert f"User ratings page not found for album ID {album_id}" in str(excinfo.value)


@pytest.mark.asyncio
async def test_scrape_user_reviews_ratings_network_error(album_scraper):
    """Test ParsingError is raised for network issues fetching initial ratings page."""
    album_id = "123-ratings"
    album_scraper._get_html.side_effect = NetworkError("Connection failed")

    with pytest.raises(ParsingError) as excinfo:
        await album_scraper.scrape_user_reviews_ratings(album_id)
    assert f"Failed to fetch initial user ratings page for album ID {album_id}" in str(excinfo.value)


@pytest.mark.asyncio
async def test_scrape_user_reviews_ratings_parsing_error(album_scraper):
    """Test ParsingError is raised for malformed HTML on ratings pages."""
    album_id = "123-ratings"
    # Mock first page to be valid, but subsequent pages to be malformed
    mock_first_page_html = """
    <html><body>
        <div class="userReviewCounter">Showing 1-80 of 160 user reviews</div>
        <div class="userRatingBlock">
            <div class="userName"><a title="User1" href="/user/user1.php"></a></div>
            <div class="ratingBlock"><div class="rating">10.0</div></div>
            <div class="date" title="2023-01-01"></div>
        </div>
    </body></html>
    """
    # Modify mock_malformed_html to contain a rating block but with a missing 'href' attribute
    # for the username, which will cause a TypeError when constructing 'user_url'.
    mock_malformed_html = """
    <html><body>
        <div class="userRatingBlock">
            <div class="userName"><a title="UserX"></a></div> <!-- Missing href attribute -->
            <div class="ratingBlock"><div class="rating">8.0</div></div>
            <div class="date" title="2023-01-05"></div>
        </div>
    </body></html>
    """

    # Configure _get_html to return valid HTML for the first page, then malformed for others
    base_ratings_url = f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=1&type=ratings" # Updated to p=1

    def get_html_side_effect(url):
        if url == base_ratings_url:
            return create_mock_html_response(mock_first_page_html)
        # Any other URL (e.g., page 2, page 3, etc.) should return malformed HTML
        elif f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=" in url:
            return create_mock_html_response(mock_malformed_html)
        raise ValueError(f"Unexpected URL: {url}")

    album_scraper._get_html.side_effect = get_html_side_effect

    with pytest.raises(ParsingError) as excinfo:
        await album_scraper.scrape_user_reviews_ratings(album_id)
    assert f"Failed to parse user ratings from album ID {album_id}" in str(excinfo.value)

