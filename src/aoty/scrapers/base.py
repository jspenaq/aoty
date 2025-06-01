"""Base scraper for Album of the Year, providing common HTTP and parsing utilities."""

from typing import TypeVar

from rnet import Client, Impersonate, Response
from selectolax.parser import HTMLParser, Node

from aoty.config import AOTY_BASE_URL, REQUEST_TIMEOUT_SECONDS
from aoty.exceptions import NetworkError, ResourceNotFoundError

# Define a TypeVar for numeric types
_NumberType = TypeVar("_NumberType", int, float)


class BaseScraper:
    """Base class for all scrapers.

    Provides common functionality like making HTTP requests, handling responses,
    and parsing HTML elements.
    """

    def __init__(self) -> None:
        """Initialize the BaseScraper with a configured HTTP client."""
        self._client: Client = Client(
            impersonate=Impersonate.Firefox136,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    async def _get_html(self, url: str) -> HTMLParser:
        """Get HTML content from a given URL.

        Args:
            url (str): The full URL to fetch.

        Returns:
            HTMLParser: Parsed HTML content.

        Raises:
            ResourceNotFoundError: If the resource is not found (404 status).
            NetworkError: For other HTTP errors, connection issues, or unexpected responses.

        """
        try:
            response: Response = await self._client.get(url)
            if response.status == 404:
                raise ResourceNotFoundError(f"Resource not found at {url} (Status: 404)")
            if not response.ok:
                raise NetworkError(f"Failed to fetch {url} (Status: {response.status})")
            html_content = await response.text()
            return HTMLParser(html_content)
        except ResourceNotFoundError:  # Catch ResourceNotFoundError specifically
            raise  # Re-raise it without wrapping
        except Exception as e:  # Catch other exceptions (e.g., ConnectionError)
            raise NetworkError(f"Network error fetching {url}: {e}") from e

    async def _post_html(
        self,
        url: str,
        form_data: dict | None = None,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> HTMLParser:
        """Post data to a given URL and get HTML content.

        Args:
            url (str): The full URL to post to.
            form_data (dict | None): Dict of form data to send (application/x-www-form-urlencoded).
            json_data (dict | None): Dict of JSON data to send (application/json).
            headers (dict | None): Dict of HTTP headers to send.

        Returns:
            HTMLParser: Parsed HTML content.

        Raises:
            ValueError: If both form_data and json_data are provided.
            ResourceNotFoundError: If the resource is not found (404 status).
            NetworkError: For other HTTP errors, connection issues, or unexpected responses.
        """
        if form_data is not None and json_data is not None:
            raise ValueError("Cannot provide both 'form_data' and 'json_data'.")

        post_kwargs = {"headers": headers}
        if form_data is not None:
            post_kwargs["form"] = list(form_data.items())
        elif json_data is not None:
            post_kwargs["json"] = json_data

        try:
            response: Response = await self._client.post(url, **post_kwargs)
            if response.status == 404:
                raise ResourceNotFoundError(f"Resource not found at {url} (Status: 404)")
            if not response.ok:
                raise NetworkError(f"Failed to post to {url} (Status: {response.status})")
            html_content = await response.text()
            return HTMLParser(html_content)
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise NetworkError(f"Network error posting to {url}: {e}") from e

    def _parse_text(self, node: Node, selector: str, default: str | None = None) -> str | None:
        """Safely extract text from a selector."""
        element = node.css_first(selector)
        return element.text(strip=True) if element else default

    def _parse_number(
        self,
        node: Node | str,  # Updated type hint to accept Node or str
        target_type: type[_NumberType],
        selector: str | None = None,
        attribute: str | None = None,
        default: _NumberType | None = None,
    ) -> _NumberType | None:
        """Safely extract and convert text or attribute to a numeric type (int or float).
        This method is primarily designed to parse numbers from HTML nodes.
        If a string is passed directly as 'node', it is assumed to be the value itself.

        Args:
            node (Node | str): The HTML node to search within, or a string containing the number.
            target_type (type[_NumberType]): The desired numeric type (int or float).
            selector (str | None): CSS selector for the element containing the number.
                                   If None, the number is extracted directly from the `node`.
                                   This parameter is typically ignored if `node` is a string.
            attribute (str | None): The attribute name to extract the number from.
                                    If None, the text content of the element is used.
            default (_NumberType | None): Default value to return.

        Returns:
            _NumberType | None: The parsed number, or the default value if parsing fails.
        """
        value_str: str | None = None

        if isinstance(node, str):
            # If node is already a string, it is assumed to be the value itself.
            # Selector and attribute are not applicable in this case.
            value_str = node
        else:  # node is a Node
            element = node.css_first(selector) if selector else node
            if not element:
                return default
            value_str = element.attributes.get(attribute) if attribute else element.text(strip=True)

        try:
            return target_type(value_str) if value_str is not None else default
        except (ValueError, TypeError):
            return default

    def _parse_float(
        self,
        node: Node,
        selector: str | None = None,
        attribute: str | None = None,
        default: float | None = None,
    ) -> float | None:
        """Safely extract and convert text or attribute to float."""
        return self._parse_number(node, float, selector, attribute, default)

    def _parse_int(
        self,
        node: Node,
        selector: str | None = None,
        attribute: str | None = None,
        default: int | None = None,
    ) -> int | None:
        """Safely extract and convert text or attribute to integer."""
        return self._parse_number(node, int, selector, attribute, default)

    def _parse_list_of_texts(self, node: Node, selector: str) -> list[str]:
        """Safely extract a list of texts from multiple elements."""
        elements = node.css(selector)
        # Changed: Removed the conditional filter to include empty strings after stripping
        return [el.text(strip=True) for el in elements]

    def _parse_attribute(
        self,
        node: Node,
        selector: str | None = None,
        attribute: str = None,
        default: str | None = None,
    ) -> str | None:
        """Safely extract an attribute's value from a selector or directly from a node."""
        if attribute is None:
            raise ValueError("Attribute name must be provided for _parse_attribute.")

        element = node.css_first(selector) if selector else node
        return element.attributes.get(attribute, default) if element else default

    def _build_full_url(self, relative_path: str | None) -> str | None:
        """Builds a full URL from a relative path, prepending AOTY_BASE_URL."""
        if relative_path:
            return AOTY_BASE_URL + relative_path
        return None

    async def close(self) -> None:
        """Close the underlying HTTP client session."""
        if hasattr(self._client, "close") and callable(self._client.close):
            await self._client.close()
