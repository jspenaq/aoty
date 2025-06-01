import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from selectolax.parser import HTMLParser

from src.aoty.scrapers.base import BaseScraper
from aoty.exceptions import ResourceNotFoundError, NetworkError, AOTYError


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
    mock_response.text = AsyncMock(
        return_value="<html><body><h1>Test</h1></body></html>"
    )
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

    with pytest.raises(ResourceNotFoundError) as excinfo:
        await base_scraper._get_html("http://example.com/nonexistent")
    assert "Resource not found at http://example.com/nonexistent (Status: 404)" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_get_html_other_http_error(base_scraper):
    """Test other HTTP error handling in _get_html."""
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    base_scraper._client.get.return_value = mock_response

    with pytest.raises(NetworkError) as excinfo:
        await base_scraper._get_html("http://example.com/error")
    assert "Failed to fetch http://example.com/error (Status: 500)" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_get_html_connection_error(base_scraper):
    """Test general connection error handling in _get_html."""
    base_scraper._client.get.side_effect = ConnectionError("Failed to connect")

    with pytest.raises(NetworkError) as excinfo:
        await base_scraper._get_html("http://example.com/bad-connection")
    assert (
        "Network error fetching http://example.com/bad-connection: Failed to connect"
        in str(excinfo.value)
    )

import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_type, test_data, expected_data",
    [
        (
            "form_data",
            {"key": "value"},
            {"key": "value"},
        ),
        (
            "json_data",
            {"key": "value"},
            {"key": "value"},
        ),
    ],
)
async def test_post_html_success(base_scraper, data_type, test_data, expected_data):
    """Test successful HTML retrieval via POST with different data types."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status = 200
    mock_response.text = AsyncMock(
        return_value="<html><body><h1>Test</h1></body></html>"
    )
    base_scraper._client.post.return_value = mock_response

    test_headers = {"X-Test": "True"}

    if data_type == "form_data":
        html_parser = await base_scraper._post_html(
            "http://example.com/post", form_data=test_data, headers=test_headers
        )
        expected_call_data = list(test_data.items())
        expected_arg = "form"
    elif data_type == "json_data":
        html_parser = await base_scraper._post_html(
            "http://example.com/post", json_data=test_data, headers=test_headers
        )
        expected_call_data = test_data
        expected_arg = "json"
    else:
        raise ValueError("Invalid data_type")

    assert isinstance(html_parser, HTMLParser)
    assert html_parser.css_first("h1").text(strip=True) == "Test"
    base_scraper._client.post.assert_awaited_once_with(
        "http://example.com/post", headers=test_headers, **{expected_arg: expected_call_data}
    )


@pytest.mark.asyncio
async def test_post_html_404_error(base_scraper):
    """Test 404 error handling in _post_html."""
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status = 404
    mock_response.text = AsyncMock(return_value="Not Found")
    base_scraper._client.post.return_value = mock_response

    with pytest.raises(ResourceNotFoundError) as excinfo:
        await base_scraper._post_html("http://example.com/nonexistent")
    assert "Resource not found at http://example.com/nonexistent (Status: 404)" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_post_html_other_http_error(base_scraper):
    """Test other HTTP error handling in _post_html."""
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    base_scraper._client.post.return_value = mock_response

    with pytest.raises(NetworkError) as excinfo:
        await base_scraper._post_html("http://example.com/error")
    assert "Failed to post to http://example.com/error (Status: 500)" in str(
        excinfo.value
    )


@pytest.mark.asyncio
async def test_post_html_connection_error(base_scraper):
    """Test general connection error handling in _post_html."""
    base_scraper._client.post.side_effect = ConnectionError("Failed to connect")

    with pytest.raises(NetworkError) as excinfo:
        await base_scraper._post_html("http://example.com/bad-connection")
    assert (
        "Network error posting to http://example.com/bad-connection: Failed to connect"
        in str(excinfo.value)
    )


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


# New tests for _parse_number
def test_parse_number_float_from_text_success(base_scraper):
    html = HTMLParser("<div><span class='score'>9.5</span></div>")
    result = base_scraper._parse_number(html, float, ".score")
    assert result == 9.5


def test_parse_number_int_from_text_success(base_scraper):
    html = HTMLParser("<div><span class='count'>123</span></div>")
    result = base_scraper._parse_number(html, int, ".count")
    assert result == 123


def test_parse_number_float_from_attribute_success(base_scraper):
    html = HTMLParser("<div data-value='7.8'>10</div>")
    result = base_scraper._parse_number(html, float, "div", attribute="data-value")
    assert result == 7.8


def test_parse_number_int_from_attribute_success(base_scraper):
    html = HTMLParser("<div data-id='456'></div>")
    result = base_scraper._parse_number(html, int, "div", attribute="data-id")
    assert result == 456


def test_parse_number_direct_node_float_text(base_scraper):
    node = HTMLParser("<span>100.0</span>").css_first("span")
    result = base_scraper._parse_number(node, float)
    assert result == 100.0


def test_parse_number_direct_node_int_text(base_scraper):
    node = HTMLParser("<span>789</span>").css_first("span")
    result = base_scraper._parse_number(node, int)
    assert result == 789


def test_parse_number_invalid_value_float(base_scraper):
    html = HTMLParser("<div><span class='score'>abc</span></div>")
    result = base_scraper._parse_number(html, float, ".score")
    assert result is None


def test_parse_number_invalid_value_int(base_scraper):
    html = HTMLParser("<div><span class='count'>abc</span></div>")
    result = base_scraper._parse_number(html, int, ".count")
    assert result is None


def test_parse_number_invalid_value_float_with_default(base_scraper):
    html = HTMLParser("<div><span class='score'>abc</span></div>")
    result = base_scraper._parse_number(html, float, ".score", default=0.0)
    assert result == 0.0


def test_parse_number_invalid_value_int_with_default(base_scraper):
    html = HTMLParser("<div><span class='count'>abc</span></div>")
    result = base_scraper._parse_number(html, int, ".count", default=0)
    assert result == 0


def test_parse_number_selector_not_found(base_scraper):
    html = HTMLParser("<div></div>")
    result = base_scraper._parse_number(html, float, ".score")
    assert result is None


def test_parse_number_attribute_not_found(base_scraper):
    html = HTMLParser("<div><span class='score'>10</span></div>")
    result = base_scraper._parse_number(html, float, ".score", attribute="data-value")
    assert result is None


# Existing tests for _parse_float (now calling _parse_number)
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


# Existing tests for _parse_int (now calling _parse_number)
def test_parse_int_from_text_success(base_scraper):
    """Test successful int parsing from element text."""
    html = HTMLParser("<div><span class='count'>123</span></div>")
    result = base_scraper._parse_int(html, ".count")
    assert result == 123


def test_parse_int_from_attribute_success(base_scraper):
    """Test successful int parsing from element attribute."""
    html = HTMLParser("<div data-id='456'></div>")
    result = base_scraper._parse_int(html, "div", attribute="data-id")
    assert result == 456


def test_parse_int_direct_node_text(base_scraper):
    """Test successful int parsing directly from a node's text."""
    node = HTMLParser("<span>789</span>").css_first("span")
    result = base_scraper._parse_int(node)
    assert result == 789


def test_parse_int_invalid_value(base_scraper):
    """Test int parsing with invalid string value."""
    html = HTMLParser("<div><span class='count'>abc</span></div>")
    result = base_scraper._parse_int(html, ".count")
    assert result is None


def test_parse_int_invalid_value_with_default(base_scraper):
    """Test int parsing with invalid string value and default."""
    html = HTMLParser("<div><span class='count'>abc</span></div>")
    result = base_scraper._parse_int(html, ".count", default=0)
    assert result == 0


def test_parse_int_selector_not_found(base_scraper):
    """Test int parsing when selector is not found."""
    html = HTMLParser("<div></div>")
    result = base_scraper._parse_int(html, ".count")
    assert result is None


def test_parse_int_attribute_not_found(base_scraper):
    """Test int parsing when attribute is not found."""
    html = HTMLParser("<div><span class='count'>10</span></div>")
    result = base_scraper._parse_int(html, ".count", attribute="data-value")
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
    assert result == ["", "Item 2", ""]


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


@pytest.mark.asyncio
async def test_close_client(base_scraper):
    """Test that the close method calls the client's close method."""
    await base_scraper.close()
    base_scraper._client.close.assert_awaited_once()
