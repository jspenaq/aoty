from aoty.config import AOTY_BASE_URL
from aoty.exceptions import NetworkError, ParsingError, ResourceNotFoundError
from aoty.models import NewsArticle
from aoty.scrapers.base import BaseScraper


class NewsScraper(BaseScraper):
    """
    Scraper for Album of The Year news pages.
    """

    async def scrape_news_articles(self, max_pages: int = 10) -> list[NewsArticle]:
        """
        Scrapes news articles from the main news section.
        Handles pagination.

        Args:
            max_pages (int): The maximum number of pages to scrape.

        Returns:
            A list of NewsArticle objects containing news article data.

        Raises:
            NetworkError: If a network-related issue occurs while fetching a page.
            ParsingError: If the HTML structure of a page is fundamentally unparseable.
        """
        all_news_articles: list[NewsArticle] = []
        page_number = 1

        while page_number <= max_pages:
            url = (
                f"{AOTY_BASE_URL}/l/newsworthy/{page_number}/"
                if page_number > 1
                else f"{AOTY_BASE_URL}/l/newsworthy/"
            )

            try:
                html = await self._get_html(url)
                news_items = html.css("div.mediaContainer")

                if not news_items:
                    break  # No more articles found, or reached end of pagination

                for item in news_items:
                    title = self._parse_text(item, "div.content > div.title > a")
                    url_path = self._parse_attribute(
                        item,
                        "div.content > div.title > a",
                        "href",
                    )
                    date = self._parse_text(
                        item,
                        "div.content > div.sourceRow > div.postDate",
                    )

                    news_article = {
                        "title": title,
                        "url": AOTY_BASE_URL + url_path if url_path else "",
                        "publication_date": date,
                    }
                    all_news_articles.append(news_article)

                page_number += 1

            except ResourceNotFoundError as e:
                raise ResourceNotFoundError(
                    f"Resource not found while scraping news page {page_number} ({url})",
                ) from e
            except NetworkError as e:
                raise NetworkError(
                    f"Network error while scraping news page {page_number} ({url}): {e}",
                ) from e
            except ParsingError as e:
                raise ParsingError(
                    f"Parsing error while scraping news page {page_number} ({url}): {e}",
                ) from e
            except Exception as e:
                raise Exception(
                    f"Unexpected error while scraping news page {page_number} ({url}): {e}",
                ) from e

        return all_news_articles
