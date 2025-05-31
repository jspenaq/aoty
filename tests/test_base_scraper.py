import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from selectolax.parser import HTMLParser

from src.aoty.scrapers.base import BaseScraper
from aoty.exceptions import AlbumNotFoundError # Although not directly raised by BaseScraper, it's good to be aware of related exceptions


@pytest.fixture
def base_scraper():
    """Fixture to provide a BaseScraper instance with a mocked client."""
    scraper = BaseScraper()
    scraper._client = AsyncMock()  # Mock the rnet.Client
    return scraper


@pytest.mark.asyncio
async def test_get_html_success(base_scraper):
    """Test successful HTML retrieval."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><body><h1>Test</h1></body></html>")
    base_scraper._client.get.return_value = mock_response

    html_parser = await base_scraper._get_html("http://example.com")

    assert isinstance(html_parser, HTMLParser)
    assert html_parser.css_first("h1").text(strip=True) == "Test"
    base_scraper._client.get.assert_awaited_once_with("http://example.com")


@pytest.mark.asyncio
async def test_get_html_404_error(base_scraper):
    """Test 404 error handling in _get_html."""
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status = 404
    mock_response.text = AsyncMock(return_value="Not Found")
    base_scraper._client.get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        await base_scraper._get_html("http://example.com/nonexistent")
    assert "Resource not found at http://example.com/nonexistent (Status: 404)" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_html_other_http_error(base_scraper):
    """Test other HTTP error handling in _get_html."""
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    base_scraper._client.get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        await base_scraper._get_html("http://example.com/error")
    assert "Failed to fetch http://example.com/error (Status: 500)" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_html_connection_error(base_scraper):
    """Test general connection error handling in _get_html."""
    base_scraper._client.get.side_effect = ConnectionError("Failed to connect")

    with pytest.raises(Exception) as excinfo:
        await base_scraper._get_html("http://example.com/bad-connection")
    assert "Failed to connect" in str(excinfo.value)


def test_parse_text_success(base_scraper):
    """Test successful text parsing."""
    html = HTMLParser("<div><p>Hello World</p></div>")
    result = base_scraper._parse_text(html, "p")
    assert result == "Hello World"


def test_parse_text_not_found(base_scraper):
    """Test text parsing when selector is not found."""
    html = HTMLParser("<div><span>No text here</span></div>")
    result = base_scraper._parse_text(html, "p")
    assert result is None


def test_parse_text_with_default(base_scraper):
    """Test text parsing with a default value when selector is not found."""
    html = HTMLParser("<div><span>No text here</span></div>")
    result = base_scraper._parse_text(html, "p", default="Default Text")
    assert result == "Default Text"


def test_parse_text_empty_content(base_scraper):
    """Test text parsing when element has empty content."""
    html = HTMLParser("<div><p></p></div>")
    result = base_scraper._parse_text(html, "p")
    assert result == ""


def test_parse_float_from_text_success(base_scraper):
    """Test successful float parsing from element text."""
    html = HTMLParser("<div><span class='score'>9.5</span></div>")
    result = base_scraper._parse_float(html, ".score")
    assert result == 9.5


def test_parse_float_from_attribute_success(base_scraper):
    """Test successful float parsing from element attribute."""
    html = HTMLParser("<div data-value='7.8'>10</div>")
    result = base_scraper._parse_float(html, "div", attribute="data-value")
    assert result == 7.8


def test_parse_float_direct_node_text(base_scraper):
    """Test successful float parsing directly from a node's text."""
    node = HTMLParser("<span>100.0</span>").css_first("span")
    result = base_scraper._parse_float(node)
    assert result == 100.0


def test_parse_float_direct_node_attribute(base_scraper):
    """Test successful float parsing directly from a node's attribute."""
    node = HTMLParser("<div score='85.5'></div>").css_first("div")
    result = base_scraper._parse_float(node, attribute="score")
    assert result == 85.5


def test_parse_float_invalid_value(base_scraper):
    """Test float parsing with invalid string value."""
    html = HTMLParser("<div><span class='score'>abc</span></div>")
    result = base_scraper._parse_float(html, ".score")
    assert result is None


def test_parse_float_invalid_value_with_default(base_scraper):
    """Test float parsing with invalid string value and default."""
    html = HTMLParser("<div><span class='score'>abc</span></div>")
    result = base_scraper._parse_float(html, ".score", default=0.0)
    assert result == 0.0


def test_parse_float_selector_not_found(base_scraper):
    """Test float parsing when selector is not found."""
    html = HTMLParser("<div></div>")
    result = base_scraper._parse_float(html, ".score")
    assert result is None


def test_parse_float_attribute_not_found(base_scraper):
    """Test float parsing when attribute is not found."""
    html = HTMLParser("<div><span class='score'>10</span></div>")
    result = base_scraper._parse_float(html, ".score", attribute="data-value")
    assert result is None


def test_parse_list_of_texts_success(base_scraper):
    """Test successful extraction of a list of texts."""
    html = HTMLParser("<div><ul><li>Item 1</li><li>Item 2</li></ul></div>")
    result = base_scraper._parse_list_of_texts(html, "li")
    assert result == ["Item 1", "Item 2"]


def test_parse_list_of_texts_no_elements(base_scraper):
    """Test extraction of a list of texts when no elements match."""
    html = HTMLParser("<div></div>")
    result = base_scraper._parse_list_of_texts(html, "li")
    assert result == []


def test_parse_list_of_texts_empty_elements(base_scraper):
    """Test extraction of a list of texts with empty elements."""
    html = HTMLParser("<div><ul><li></li><li>Item 2</li><li> </li></ul></div>")
    result = base_scraper._parse_list_of_texts(html, "li")
    assert result == ["", "Item 2", ""] # Note: strip=True is applied, but empty strings remain if content is just whitespace


def test_parse_attribute_with_selector_success(base_scraper):
    """Test successful attribute parsing with a selector."""
    html = HTMLParser("<div><a href='/test'>Link</a></div>")
    result = base_scraper._parse_attribute(html, "a", "href")
    assert result == "/test"


def test_parse_attribute_direct_node_success(base_scraper):
    """Test successful attribute parsing directly from a node."""
    node = HTMLParser("<img src='/image.jpg'>").css_first("img")
    result = base_scraper._parse_attribute(node, attribute="src")
    assert result == "/image.jpg"


def test_parse_attribute_not_found(base_scraper):
    """Test attribute parsing when attribute is not found."""
    html = HTMLParser("<div><a href='/test'>Link</a></div>")
    result = base_scraper._parse_attribute(html, "a", "title")
    assert result is None


def test_parse_attribute_not_found_with_default(base_scraper):
    """Test attribute parsing when attribute is not found with a default."""
    html = HTMLParser("<div><a href='/test'>Link</a></div>")
    result = base_scraper._parse_attribute(html, "a", "title", default="Default Title")
    assert result == "Default Title"


def test_parse_attribute_selector_not_found(base_scraper):
    """Test attribute parsing when selector is not found."""
    html = HTMLParser("<div></div>")
    result = base_scraper._parse_attribute(html, "a", "href")
    assert result is None


def test_parse_attribute_missing_attribute_name(base_scraper):
    """Test attribute parsing raises ValueError if attribute name is missing."""
    html = HTMLParser("<div><a href='/test'>Link</a></div>")
    with pytest.raises(ValueError) as excinfo:
        base_scraper._parse_attribute(html, "a", attribute=None)
    assert "Attribute name must be provided for _parse_attribute." in str(excinfo.value)

