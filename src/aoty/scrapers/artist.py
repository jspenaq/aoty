import re

from selectolax.parser import Node

from aoty.config import AOTY_BASE_URL
from aoty.exceptions import ArtistNotFoundError, NetworkError, ParsingError, ResourceNotFoundError
from aoty.models import AlbumSummary, Artist, ArtistSummary, SongSummary
from aoty.scrapers.base import BaseScraper


class ArtistScraper(BaseScraper):
    """
    Scraper for Album of the Year artist pages.
    """

    async def scrape_artist_by_id(self, artist_id: str) -> Artist | None:
        """
        Scrapes artist data using its ID.
        """
        url = f"{AOTY_BASE_URL}/artist/{artist_id}/"  # AOTY often redirects to full name
        return await self._scrape_artist_page(url)

    async def scrape_artist_by_url(self, artist_url: str) -> Artist | None:
        """
        Scrapes artist data using its full URL.
        """
        return await self._scrape_artist_page(artist_url)

    async def _scrape_artist_page(self, url: str) -> Artist | None:
        """
        Internal method to scrape a generic artist page URL.
        """
        try:
            html = await self._get_html(url)
        except ResourceNotFoundError as e:
            raise ArtistNotFoundError(f"Artist not found at URL: {url}") from e
        except NetworkError as e:
            raise ParsingError(f"Failed to fetch artist page {url}: {e}") from e

        try:
            artist_name = self._parse_text(html, "h1.artistHeadline")
            if artist_name is None:
                raise ParsingError(f"Could not parse artist name from {url}")

            artist_data: Artist = {
                "name": artist_name,
                "url": url,
                "id": (int(re.search(r"artist/(\d+)", url).group(1))),
                "cover_url": None,
                "critic_score": None,
                "critic_review_count": None,
                "user_score": None,
                "user_rating_count": None,
                "genres": [],
                "associated_artists": [],
                "discography": [],
                "top_songs": [],
                "similar_artists": [],
            }

            # Cover URL
            cover_img = html.css_first("div.artistImage img")
            if cover_img:
                artist_data["cover_url"] = cover_img.attributes.get(
                    "data-src",
                ) or cover_img.attributes.get("src")

            # Critic Score
            critic_score_node = html.css_first(
                'div.artistCriticScore span[itemprop="ratingValue"]',
            )
            if critic_score_node:
                artist_data["critic_score"] = self._parse_float(critic_score_node)

            critic_review_count_node = html.css_first(
                'div.artistCriticScoreBox span[itemprop="reviewCount"]',
            )
            if critic_review_count_node:
                artist_data["critic_review_count"] = self._parse_int(
                    critic_review_count_node,
                )

            # User Score
            user_score_node = html.css_first("div.artistUserScore")
            if user_score_node:
                artist_data["user_score"] = self._parse_float(user_score_node)

            user_rating_count_text = self._parse_text(
                html,
                "div.artistUserScoreBox strong",
            )
            if user_rating_count_text:
                artist_data["user_rating_count"] = self._parse_int(
                    user_rating_count_text.replace(",", ""),
                )

            # Details Section Parsing (Genres, Associated Artists)
            details_section = html.css_first("div.artistTopBox.info")
            if details_section:
                for detail_row in details_section.css("div.detailRow"):
                    label_span = detail_row.css_first("span")
                    if label_span:
                        label_text_normalized = (
                            label_span.text(strip=True)
                            .replace("/\xa0", "")  # Remove non-breaking space
                            .replace("/", "")
                            .replace(" ", "")
                            .replace(":", "")
                            .strip()
                            .lower()
                        )

                        if label_text_normalized == "genre":
                            genres = []
                            for a_tag in detail_row.css("a"):
                                genre_name = a_tag.text(strip=True)
                                if genre_name and genre_name not in genres:
                                    genres.append(genre_name)
                            artist_data["genres"] = genres
                        elif label_text_normalized == "memberof":
                            associated_artists = []
                            for a_tag in detail_row.css("a"):
                                name = a_tag.text(strip=True)
                                href = a_tag.attributes.get("href")
                                if name and href:
                                    associated_artists.append(
                                        ArtistSummary(
                                            name=name,
                                            url=self._build_full_url(href),
                                            image_url=None,  # Image not available here
                                        ),
                                    )
                            artist_data["associated_artists"] = associated_artists

            # Discography (Albums, Mixtapes, Singles, Appears On)
            discography: list[AlbumSummary] = []
            current_album_category: str | None = None  # This will hold "Albums", "Mixtapes", etc.

            album_output_node = html.css_first("div#albumOutput")
            if album_output_node:
                # Iterate through direct children of album_output_node to ensure strict document order
                child_node = album_output_node.child
                while child_node:
                    # Ensure it's an element node (skip text nodes, etc.)
                    if child_node.tag:
                        # Check if it's an h2 with the "subHeadline" class
                        if (
                            child_node.tag == "h2"
                            and "subHeadline" in child_node.attributes.get("class", "").split()
                        ):
                            current_album_category = child_node.text(strip=True)
                            # Remove "View All" if present (e.g., for Singles headline)
                            if "View All" in current_album_category:
                                current_album_category = current_album_category.replace(
                                    "View All", "",
                                ).strip()
                        # Check if it's a div with the "albumBlock" class
                        elif (
                            child_node.tag == "div"
                            and "albumBlock" in child_node.attributes.get("class", "").split()
                        ):
                            # Pass the current category to the parsing helper
                            album_summary = self._parse_album_block(
                                child_node, artist_data["name"], current_album_category,
                            )
                            if album_summary:
                                discography.append(album_summary)
                    child_node = child_node.next  # Move to the next sibling

            artist_data["discography"] = discography

            # Top Songs
            top_songs: list[SongSummary] = []
            for song_row in html.css("div.mediaList table.trackListTable tr"):
                song_summary = self._parse_song_block(song_row)
                if song_summary:
                    top_songs.append(song_summary)
            artist_data["top_songs"] = top_songs

            # Similar Artists
            similar_artists: list[ArtistSummary] = []
            for artist_block in html.css("div.relatedArtists .artistBlock"):
                name_node = artist_block.css_first("div.name a")
                image_node = artist_block.css_first("div.image img")
                if name_node:
                    name = name_node.text(strip=True)
                    href = name_node.attributes.get("href")
                    image_url = (
                        image_node.attributes.get("data-src") or image_node.attributes.get("src")
                        if image_node
                        else None
                    )
                    if name and href:
                        similar_artists.append(
                            ArtistSummary(
                                name=name,
                                url=self._build_full_url(href),
                                image_url=image_url,
                            ),
                        )
            artist_data["similar_artists"] = similar_artists

            return artist_data

        except Exception as e:
            raise ParsingError(f"Failed to parse artist data from {url}: {e}") from e

    def _parse_album_block(
        self, node: Node, original_artist: str, album_category: str | None,
    ) -> AlbumSummary | None:
        """Helper to parse an album block into an AlbumSummary."""
        title_node = node.css_first("a div.albumTitle")
        link_node = node.css_first("a")
        year_type_node = node.css_first("div.type")
        cover_img_node = node.css_first("div.image img")
        artist_node = node.css_first("a div.artistTitle")  # For "Appears On" sections

        if not title_node or not link_node:
            return None

        album_title = title_node.text(strip=True)
        album_url = self._build_full_url(link_node.attributes.get("href"))
        cover_url = (
            cover_img_node.attributes.get("data-src") or cover_img_node.attributes.get("src")
            if cover_img_node
            else None
        )
        cover_url = re.sub(r"/\d+x0", "", cover_url)
        year: int | None = None
        if year_type_node:
            year_text = year_type_node.text(strip=True)
            year_match = re.search(r"(\d{4})", year_text)
            if year_match:
                year = self._parse_int(year_match.group(1))

        critic_score: float | None = None
        critic_review_count: int | None = None
        user_score: float | None = None
        user_rating_count: int | None = None

        for n in node.css("div.ratingRow"):
            if "critic score" in n.text():
                critic_score, critic_review_count = self._parse_rating(n)
            elif "user score" in n.text():
                user_score, user_rating_count = self._parse_rating(n)

        album_artist: str | None = None
        if artist_node:
            album_artist = artist_node.text(strip=True)
        else:
            album_artist = original_artist

        return AlbumSummary(
            title=album_title,
            artist=album_artist,
            url=album_url,
            year=year,
            type=album_category,  # Use the passed album_category
            cover_url=cover_url,
            critic_score=critic_score,
            critic_review_count=critic_review_count,
            user_score=user_score,
            user_rating_count=user_rating_count,
        )

    def _parse_rating(self, node: Node) -> tuple[float | None, int | None]:
        score = None
        review_count = None

        text = node.text()
        match = re.match(r"(\d+)\s*(critic|user)\s*score\s*\((\d+(,\d+)?)\)", text)
        if match:
            score = float(match.group(1))
            review_count = int(match.group(3).replace(",", ""))

        return score, review_count

    def _parse_song_block(
        self, node: Node,
    ) -> SongSummary | None:  # Changed from HTMLParser to Node
        """Helper to parse a song row into a SongSummary."""
        title_node = node.css_first("td.songAlbum div[style='font-weight: bold'] a")
        album_title_node = node.css_first("td.songAlbum div.gray-font")
        cover_img_node = node.css_first("td.coverart img")
        rating_node = node.css_first("td.trackRating span")

        if not title_node:
            return None

        song_title = title_node.text(strip=True)
        song_url = self._build_full_url(title_node.attributes.get("href"))
        cover_url = (
            cover_img_node.attributes.get("data-src") or cover_img_node.attributes.get("src")
            if cover_img_node
            else None
        )

        album_title: str | None = None
        album_url: str | None = None
        if album_title_node:
            album_title = album_title_node.text(strip=True)
            # The album link is the parent <a> of the coverart img
            album_link_node = node.css_first("td.coverart a")
            if album_link_node:
                album_url = self._build_full_url(album_link_node.attributes.get("href"))

        rating: float | None = None
        rating_count: int | None = None
        if rating_node:
            rating = self._parse_float(rating_node)
            rating_count_title = rating_node.attributes.get("title")
            if rating_count_title:
                count_match = re.search(r"(\d+)\s*Rating", rating_count_title)
                if count_match:
                    rating_count = self._parse_int(count_match.group(1))

        return SongSummary(
            title=song_title,
            url=song_url,
            album_title=album_title,
            album_url=album_url,
            cover_url=cover_url,
            rating=rating,
            rating_count=rating_count,
        )



async def main():
    scraper = ArtistScraper()
    try:
        artist = await scraper.scrape_artist_by_id("209-lykke-li")  # Replace with a valid artist ID
        if artist:
            print(artist)
        print(e)
    except ParsingError as e:
        print(f"Parsing error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())