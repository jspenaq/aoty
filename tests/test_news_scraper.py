from unittest.mock import AsyncMock

import pytest
from selectolax.parser import HTMLParser

from aoty.config import AOTY_BASE_URL
from aoty.exceptions import NetworkError, ParsingError, ResourceNotFoundError
from aoty.scrapers.news import NewsScraper


@pytest.fixture
def news_scraper():
    """Fixture to provide a NewsScraper instance with a mocked _get_html."""
    scraper = NewsScraper()
    scraper._get_html = AsyncMock()
    return scraper


def create_mock_html_response(html_content: str) -> HTMLParser:
    """Helper to create a parsed HTML response from a string."""
    return HTMLParser(html_content)


@pytest.mark.asyncio
async def test_scrape_news_articles_success(news_scraper):
    """Test successful scraping of news articles."""
    mock_html = """
    <html><body>
        <div class="mediaContainer">
            <div class="content">
                <div class="title"><a href="/news/123-test-article.php">Test Article Title</a></div>
                <div class="sourceRow">
                    <div class="postDate">Jan 01, 2025</div>
                </div>
            </div>
        </div>
    </body></html>
    """
    news_scraper._get_html.return_value = create_mock_html_response(mock_html)

    articles = await news_scraper.scrape_news_articles(max_pages=1)

    news_scraper._get_html.assert_awaited_once_with(f"{AOTY_BASE_URL}/l/newsworthy/")

    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article Title"
    assert articles[0]["url"] == f"{AOTY_BASE_URL}/news/123-test-article.php"
    assert articles[0]["publication_date"] == "Jan 01, 2025"


@pytest.mark.asyncio
async def test_scrape_news_articles_pagination(news_scraper):
    """Test successful scraping of news articles across multiple pages."""
    mock_html_page1 = """
    <html><body>
        <div class="mediaContainer">
            <div class="content">
                <div class="title"><a href="/news/123-test-article.php">Test Article 1</a></div>
                <div class="sourceRow">
                    <div class="postDate">Jan 01, 2025</div>
                </div>
            </div>
        </div>
    </body></html>
    """
    mock_html_page2 = """
    <html><body>
        <div class="mediaContainer">
            <div class="content">
                <div class="title"><a href="/news/456-test-article.php">Test Article 2</a></div>
                <div class="sourceRow">
                    <div class="postDate">Jan 02, 2025</div>
                </div>
            </div>
        </div>
    </body></html>
    """

    async def get_html_side_effect(url):
        if url == f"{AOTY_BASE_URL}/l/newsworthy/":
            return create_mock_html_response(mock_html_page1)
        if url == f"{AOTY_BASE_URL}/l/newsworthy/2/":
            return create_mock_html_response(mock_html_page2)
        return None

    news_scraper._get_html.side_effect = get_html_side_effect

    articles = await news_scraper.scrape_news_articles(max_pages=2)

    assert len(articles) == 2
    assert articles[0]["title"] == "Test Article 1"
    assert articles[0]["url"] == f"{AOTY_BASE_URL}/news/123-test-article.php"
    assert articles[0]["publication_date"] == "Jan 01, 2025"
    assert articles[1]["title"] == "Test Article 2"
    assert articles[1]["url"] == f"{AOTY_BASE_URL}/news/456-test-article.php"
    assert articles[1]["publication_date"] == "Jan 02, 2025"


@pytest.mark.asyncio
async def test_scrape_news_articles_no_articles(news_scraper):
    """Test scenario when no news articles are found."""
    mock_html = "<html><body></body></html>"
    news_scraper._get_html.return_value = create_mock_html_response(mock_html)

    articles = await news_scraper.scrape_news_articles()

    news_scraper._get_html.assert_awaited_once_with(f"{AOTY_BASE_URL}/l/newsworthy/")
    assert len(articles) == 0


@pytest.mark.asyncio
async def test_scrape_news_articles_resource_not_found(news_scraper):
    """Test ResourceNotFoundError is raised when the news page returns 404."""
    news_scraper._get_html.side_effect = ResourceNotFoundError("Not Found")

    with pytest.raises(ResourceNotFoundError) as excinfo:
        await news_scraper.scrape_news_articles()
    assert f"Resource not found while scraping news page 1 ({AOTY_BASE_URL}/l/newsworthy/)" in str(
        excinfo.value,
    )


@pytest.mark.asyncio
async def test_scrape_news_articles_network_error(news_scraper):
    """Test NetworkError is raised for network issues fetching news page."""
    news_scraper._get_html.side_effect = NetworkError("Connection failed")

    with pytest.raises(NetworkError) as excinfo:
        await news_scraper.scrape_news_articles()
    assert (
        f"Network error while scraping news page 1 ({AOTY_BASE_URL}/l/newsworthy/): Connection failed"
        in str(
            excinfo.value,
        )
    )


@pytest.mark.asyncio
async def test_scrape_news_articles_parsing_error(news_scraper):
    """Test ParsingError is raised for malformed HTML on news pages."""
    news_scraper._get_html.side_effect = ParsingError("Malformed HTML")

    with pytest.raises(ParsingError) as excinfo:
        await news_scraper.scrape_news_articles()
    assert (
        f"Parsing error while scraping news page 1 ({AOTY_BASE_URL}/l/newsworthy/): Malformed HTML"
        in str(
            excinfo.value,
        )
    )
