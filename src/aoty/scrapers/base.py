from typing import Optional
from rnet import Impersonate, Client, Response
from selectolax.parser import HTMLParser
from aoty.config import REQUEST_TIMEOUT_SECONDS


class BaseScraper:
    """
    Base class for all scrapers, providing common functionality like
    making HTTP requests, handling responses, and caching.
    """

    def __init__(self):
        self._client: Client = Client(
            impersonate=Impersonate.Firefox136, timeout=REQUEST_TIMEOUT_SECONDS
        )

    async def _get_html(self, url: str) -> HTMLParser:
        """
        Get HTML content from a given URL

        Args:
            url (str): The full URL to fetch.

        Returns:
            HTMLParser: Parsed HTML content.

        Raises:
            AOTYError: For other HTTP errors or unexpected responses.
        """
        try:
            response: Response = await self._client.get(url)
            if response.status == 404:
                raise Exception(f"Resource not found at {url} (Status: 404)")

            elif not response.ok:
                raise Exception(f"Failed to fetch {url} (Status: {response.status})")
            html_content = await response.text()
            return HTMLParser(html_content)

        except Exception as e:
            raise Exception(e)

    def _parse_text(
        self, node, selector: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Helper to safely extract text from a selector."""
        element = node.css_first(selector)
        return element.text(strip=True) if element else default

    def _parse_float(
        self,
        node,
        selector: Optional[str] = None,
        attribute: Optional[str] = None,
        default: Optional[float] = None,
    ) -> Optional[float]:
        """Helper to safely extract and convert text or attribute to float."""
        element = node.css_first(selector) if selector else node

        if not element:
            return default

        value_str = None
        if attribute:
            value_str = element.attributes.get(attribute)
        else:
            value_str = element.text(strip=True)

        try:
            return float(value_str) if value_str else default
        except (ValueError, TypeError):  # TypeError for None or non-string
            return default

    def _parse_list_of_texts(self, node, selector: str) -> list[str]:
        """Helper to safely extract a list of texts from multiple elements."""
        elements = node.css(selector)
        # Changed: Removed the conditional filter to include empty strings after stripping
        return [el.text(strip=True) for el in elements]

    def _parse_attribute(
        self,
        node,
        selector: Optional[str] = None,
        attribute: str = None,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Helper to safely extract an attribute's value from a selector or directly from a node."""
        if attribute is None:
            raise ValueError("Attribute name must be provided for _parse_attribute.")

        element = node.css_first(selector) if selector else node
        return element.attributes.get(attribute, default) if element else default
