import asyncio
import re
from math import ceil

from aoty.config import AOTY_BASE_URL
from aoty.exceptions import (
    AlbumNotFoundError,
    NetworkError,
    ParsingError,
    ResourceNotFoundError,
)
from aoty.models import (
    Album,
    AlbumCredit,
    AlbumLink,
    CriticReview,
    Review,
    Track,
    UserRating,
)
from aoty.scrapers.base import BaseScraper
from aoty.utils import parse_release_date


class AlbumScraper(BaseScraper):
    """Scraper for Album of the Year album pages."""

    async def scrape_album_by_id(self, album_id: str) -> Album | None:
        """Scrapes album data using its ID."""
        url = f"{AOTY_BASE_URL}/album/{album_id}.php"
        return await self._scrape_album_page(url)

    async def _scrape_album_page(self, url: str) -> Album | None:
        """Internal method to scrape an album page URL."""
        try:
            html = await self._get_html(url)
        except ResourceNotFoundError as e:
            raise AlbumNotFoundError(f"Album not found at URL: {url}") from e
        except NetworkError as e:
            raise ParsingError(f"Failed to fetch album page {url}: {e}") from e

        try:
            album_data: Album = {
                "title": self._parse_text(html, 'h1.albumTitle span[itemprop="name"]'),
                "artist": self._parse_text(html, 'div.artist span[itemprop="name"] a'),
                "url": url,
                "id": (int(re.search(r"/album/(\d+)", url).group(1))),
                "genres": [],
                "release_date": None,
                "format": None,
                "labels": [],
                # "producers": [],  # Initialized as empty; not directly populated by this scraper
                # "writers": [],  # Initialized as empty; not directly populated by this scraper
                "credits": [],
                "total_length": None,
            }

            # Cover URL
            cover_img = html.css_first("div.albumTopBox.cover img")
            if cover_img:
                srcset = cover_img.attributes.get("srcset")
                if srcset:
                    # Take the last (presumably largest) URL from srcset
                    album_data["cover_url"] = srcset.split(",")[-1].strip().split(" ")[0]
                else:
                    album_data["cover_url"] = cover_img.attributes.get(
                        "data-src",
                    ) or cover_img.attributes.get("src")

            # Critic Score
            critic_score_link = html.css_first(
                'div.albumCriticScore span[itemprop="ratingValue"] a',
            )
            if critic_score_link:
                album_data["critic_score"] = self._parse_float(
                    critic_score_link,
                    attribute="title",
                )

            album_data["critic_review_count"] = self._parse_float(
                html,
                'div.albumCriticScoreBox span[itemprop="ratingCount"]',
                default=None,
            )

            critic_rank_text = self._parse_text(
                html,
                "div.albumCriticScoreBox .text.gray",
            )
            if critic_rank_text:
                match = re.search(r"#(\d+)\s*/\s*(\d+)", critic_rank_text)
                if match:
                    album_data["critic_rank_year"] = int(match.group(1))
                    album_data["critic_rank_year_total"] = int(match.group(2))

            # User Score
            user_score_link = html.css_first("div.albumUserScore a")
            if user_score_link:
                album_data["user_score"] = self._parse_float(
                    user_score_link,
                    attribute="title",
                )

            user_rating_count_text = self._parse_text(
                html,
                "div.albumUserScoreBox .text.numReviews strong",
            )
            if user_rating_count_text:
                album_data["user_rating_count"] = self._parse_int(
                    user_rating_count_text.replace(",", ""),
                )

            user_rank_text = self._parse_text(
                html,
                "div.albumUserScoreBox .text.gray strong a",
            )
            if user_rank_text:
                match = re.search(r"#(\d+)", user_rank_text)
                if match:
                    album_data["user_rank_year"] = self._parse_int(match.group(1))

            # Details Section Parsing
            details_section = html.css_first("div.albumTopBox.info")
            if details_section:
                for detail_row in details_section.css("div.detailRow"):
                    label_span = detail_row.css_first("span")
                    if label_span:
                        # Extract label text and normalize it
                        label_text_raw = label_span.text(strip=True)
                        label_text_normalized = (
                            label_text_raw.replace("/ ", "")
                            .replace("/", "")
                            .replace(" ", "")
                            .strip()
                            .lower()
                        )

                        if label_text_normalized == "releasedate":
                            # Get the full text of the detail row, preserving internal spaces
                            # Then remove the label text and strip leading/trailing whitespace
                            full_text_with_spaces = detail_row.text(strip=False)
                            value_text_with_spaces = (
                                full_text_with_spaces.replace(label_text_raw, "")
                                .replace(" ", "")
                                .strip()
                            )
                            album_data["release_date"] = parse_release_date(
                                value_text_with_spaces,
                            )  # Use parse_release_date
                        elif label_text_normalized == "format":
                            # For format, the simple text extraction should be fine
                            album_data["format"] = (
                                detail_row.text(strip=True).replace(label_text_raw, "").strip()
                            )
                        elif label_text_normalized == "label":
                            labels_list = []
                            for a in detail_row.css("a"):
                                name = a.text(strip=True)
                                href = a.attributes.get("href")
                                if name:  # Only add if name exists
                                    if href is None:  # Explicitly check for missing href
                                        raise ParsingError(
                                            f"Missing href for label '{name}' in album details.",
                                        )
                                    labels_list.append(
                                        {
                                            "name": name,
                                            "url": self._build_full_url(href),
                                        },
                                    )
                            album_data["labels"] = labels_list
                        elif label_text_normalized == "genre":
                            genres = []
                            # Prioritize meta tags for canonical names
                            for meta_tag in detail_row.css('meta[itemprop="genre"]'):
                                genre_name = meta_tag.attributes.get("content")
                                if genre_name and genre_name not in genres:
                                    genres.append(genre_name)
                            # Add from <a> tags
                            for a_tag in detail_row.css("a"):
                                genre_name = a_tag.text(strip=True)
                                if genre_name and genre_name not in genres:
                                    genres.append(genre_name)
                            # Add from div.secondary
                            for div_secondary in detail_row.css("div.secondary"):
                                genre_name = div_secondary.text(strip=True)
                                if genre_name and genre_name not in genres:
                                    genres.append(genre_name)
                            album_data["genres"] = genres
                        # Removed producer and writer parsing here

            # Tracklist
            tracklist: list[Track] = []
            for _, row in enumerate(html.css("table.trackListTable tr")):
                track_number_node = row.css_first("td.trackNumber")
                track_title_node = row.css_first("td.trackTitle a")
                track_duration_node = row.css_first("td.trackTitle div.length")
                track_rating_node = row.css_first("td.trackRating span")

                if track_number_node and track_title_node:
                    track: Track = {
                        "number": self._parse_int(track_number_node),
                        "title": track_title_node.text(strip=True),
                        "url": self._build_full_url(
                            track_title_node.attributes.get("href"),
                        ),
                        "duration": (
                            track_duration_node.text(strip=True) if track_duration_node else None
                        ),
                        "featured_artists": [],
                        "rating": None,
                        "rating_count": None,
                    }

                    featured_artists_nodes = row.css(
                        "td.trackTitle div.featuredArtists a",
                    )
                    if featured_artists_nodes:
                        track["featured_artists"] = [
                            {
                                "name": fa.text(strip=True),
                                "url": self._build_full_url(fa.attributes.get("href")),
                            }
                            for fa in featured_artists_nodes
                        ]

                    if track_rating_node:
                        track["rating"] = self._parse_float(
                            track_rating_node,
                            None,
                            default=None,
                        )
                        rating_count_title = track_rating_node.attributes.get("title")
                        if rating_count_title:
                            count_match = re.search(
                                r"(\d+)\s*Ratings",
                                rating_count_title,
                            )
                            if count_match:
                                track["rating_count"] = self._parse_int(
                                    count_match.group(1),
                                )
                    tracklist.append(track)
            album_data["tracklist"] = tracklist

            total_length_text = self._parse_text(html, "div.totalLength")
            if total_length_text:
                album_data["total_length"] = total_length_text.replace(
                    "Total Length: ",
                    "",
                ).strip()

            # Scrape full credits
            if album_data["id"] is not None:
                album_data["credits"] = await self._scrape_full_credits(str(album_data["id"]))
            else:
                album_data["credits"] = []  # Or None, depending on desired default for missing ID

            # Third-party links
            links: list[AlbumLink] = []
            for link_node in html.css("div.buyButtons a"):
                link_name = link_node.attributes.get("title")
                link_url = link_node.attributes.get("href")
                if link_name and link_url:
                    links.append({"name": link_name, "url": link_url})
            album_data["links"] = links

            # Critic Reviews
            critic_reviews: list[CriticReview] = []
            for review_row in html.css("div#criticReviewContainer div.albumReviewRow"):
                publication_node = review_row.css_first("div.publication a")
                author_node = review_row.css_first("div.author a")
                score_node = review_row.css_first("div.albumReviewRating")
                text_node = review_row.css_first("div.albumReviewText")
                link_node = review_row.css_first("div.albumReviewLinks .extLink a")
                date_node = review_row.css_first("div.albumReviewLinks .date")

                if publication_node and score_node:
                    review: CriticReview = {
                        "publication_name": publication_node.text(strip=True),
                        "publication_url": self._build_full_url(
                            publication_node.attributes.get("href"),
                        ),
                        "author_name": (author_node.text(strip=True) if author_node else None),
                        "author_url": (
                            self._build_full_url(author_node.attributes.get("href"))
                            if author_node
                            else None
                        ),
                        "score": float(score_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "url": link_node.attributes.get("href") if link_node else None,
                        "date": (date_node.attributes.get("title") if date_node else None),
                    }
                    critic_reviews.append(review)
            album_data["critic_reviews"] = critic_reviews

            # User Reviews (Popular and Recent)
            popular_user_reviews: list[Review] = []
            for review_row in html.css(
                'section#users:has(h2 a[href*="popular"]) div.albumReviewRow',
            ):
                username_node = review_row.css_first("div.userReviewName a")
                rating_node = review_row.css_first("div.ratingBlock div.rating")
                text_node = review_row.css_first("div.albumReviewText.user")
                date_node = review_row.css_first("div.albumReviewLinks .review_date")
                likes_node = review_row.css_first("div.review_likes")
                comment_count_node = review_row.css_first("div.comment_count")

                if username_node and rating_node:
                    user_url_suffix = self._parse_attribute(username_node, None, "href")
                    if user_url_suffix is None:
                        raise ParsingError(
                            "Missing user URL suffix in popular user review block.",
                        )
                    review: Review = {
                        "username": username_node.text(strip=True),
                        "user_url": self._build_full_url(user_url_suffix),
                        "rating": float(rating_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "date": date_node.text(strip=True) if date_node else None,
                        "likes": (
                            self._parse_int(likes_node)
                            if likes_node and likes_node.text(strip=True).isdigit()
                            else 0
                        ),
                        "comment_count": (
                            self._parse_int(comment_count_node)
                            if comment_count_node and comment_count_node.text(strip=True).isdigit()
                            else 0
                        ),
                    }
                    popular_user_reviews.append(review)
            album_data["popular_user_reviews"] = popular_user_reviews

            recent_user_reviews: list[Review] = []
            for review_row in html.css(
                'section#users:has(h2 a[href*="recent"]) div.albumReviewRow',
            ):
                username_node = review_row.css_first("div.userReviewName a")
                rating_node = review_row.css_first("div.ratingBlock div.rating")
                text_node = review_row.css_first("div.albumReviewText.user")
                date_node = review_row.css_first("div.albumReviewLinks .review_date")
                likes_node = review_row.css_first("div.review_likes")
                comment_count_node = review_row.css_first("div.comment_count")

                if username_node and rating_node:
                    user_url_suffix = self._parse_attribute(username_node, None, "href")
                    if user_url_suffix is None:
                        raise ParsingError(
                            "Missing user URL suffix in recent user review block.",
                        )
                    review: Review = {
                        "username": username_node.text(strip=True),
                        "user_url": self._build_full_url(user_url_suffix),
                        "rating": float(rating_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "date": date_node.text(strip=True) if date_node else None,
                        "likes": (
                            self._parse_int(likes_node)
                            if likes_node and likes_node.text(strip=True).isdigit()
                            else 0
                        ),
                        "comment_count": (
                            self._parse_int(comment_count_node)
                            if comment_count_node and comment_count_node.text(strip=True).isdigit()
                            else 0
                        ),
                    }
                    recent_user_reviews.append(review)
            album_data["recent_user_reviews"] = recent_user_reviews

            # Similar Albums
            similar_albums_list = []
            for album_block in html.css(
                'div.section:has(h2 a[href*="similar"]) .albumBlock.small',
            ):
                title_node = album_block.css_first("a div.albumTitle")
                artist_node = album_block.css_first("a div.artistTitle")
                link_node = album_block.css_first("a")
                if title_node and artist_node and link_node:
                    similar_albums_list.append(
                        {
                            "title": title_node.text(strip=True),
                            "artist": artist_node.text(strip=True),
                            "url": self._build_full_url(
                                link_node.attributes.get("href"),
                            ),
                        },
                    )
            album_data["similar_albums"] = similar_albums_list

            # More by Artist
            more_by_artist_list = []
            for album_block in html.css(
                'div.section:has(h2 a[href*="artist"]) .albumBlock.small',
            ):
                title_node = album_block.css_first("a div.albumTitle")
                year_node = album_block.css_first("div.type")
                link_node = album_block.css_first("a")
                if title_node and year_node and link_node:
                    more_by_artist_list.append(
                        {
                            "title": title_node.text(strip=True),
                            "year": (
                                self._parse_int(year_node)
                                if year_node and year_node.text(strip=True).isdigit()
                                else None
                            ),
                            "url": self._build_full_url(
                                link_node.attributes.get("href"),
                            ),
                        },
                    )
            album_data["more_by_artist"] = more_by_artist_list

            # Removed Contributions By parsing here

            return album_data

        except Exception as e:
            raise ParsingError(f"Failed to parse album data from {url}: {e}") from e

    async def _scrape_full_credits(self, album_id: str) -> list[AlbumCredit]:
        """Scrapes full album credits from the dedicated endpoint."""
        credits_url = f"{AOTY_BASE_URL}/scripts/showAlbumCredits.php"
        payload = {"albumID": album_id}

        try:
            # Use the refactored _post_html method to send form data
            credits_html = await self._post_html(
                credits_url,
                form_data=payload,
            )

        except NetworkError as e:
            raise ParsingError(
                f"Failed to fetch full credits for album ID {album_id}: {e}",
            ) from e
        except Exception as e:
            raise ParsingError(
                f"Error fetching or parsing full credits for album ID {album_id}: {e}",
            ) from e

        all_credits: list[AlbumCredit] = []
        # The response HTML contains multiple 'div.content' blocks, each with 'div.heading' and 'div.inner'.
        # We need to parse each 'div.content' block.
        for content_block in credits_html.css("div.content"):
            # Each content block might contain multiple sections (e.g., Performers, Composition, Production)
            for section_node in content_block.css("div.inner"):
                section_title_nodes = section_node.css("div.sectionTitle")
                credit_wrapper_nodes = section_node.css("div.creditWrapper")

                # Iterate through section titles and their corresponding credit wrappers
                for i in range(len(section_title_nodes)):
                    section_title = section_title_nodes[i].text(strip=True)
                    credit_wrapper = credit_wrapper_nodes[i]

                    for credit_node in credit_wrapper.css("div.credit"):
                        name_node = credit_node.css_first("div.name a")
                        songs_node = credit_node.css_first("div.songs")

                        if name_node:
                            name = name_node.text(strip=True)
                            url = self._build_full_url(name_node.attributes.get("href"))
                            roles: list[str] = []

                            if songs_node:
                                for role_node in songs_node.css("a"):
                                    role_text = role_node.text(strip=True)
                                    if (
                                        role_text and role_text != "Primary"
                                    ):  # "Primary" is often redundant
                                        roles.append(role_text)

                            if not roles:
                                # If no specific roles are found, use the section title as the role
                                all_credits.append(
                                    AlbumCredit(name=name, url=url, role=section_title),
                                )
                            else:
                                for role in roles:
                                    all_credits.append(
                                        AlbumCredit(name=name, url=url, role=role),
                                    )
        return all_credits

    async def scrape_user_reviews_ratings(self, album_id: str) -> list[UserRating]:
        """Scrapes all user ratings (without review text) for a given album ID across all pages.
        This function specifically targets pages like
        'https://www.albumoftheyear.org/album/{album_id}/user-reviews/?type=ratings'.

        Args:
            album_id (str): The ID of the album to scrape ratings for.

        Returns:
            List[UserRating]: A list of dictionaries, each representing a user rating.

        Raises:
            AlbumNotFoundError: If the album page for ratings is not found (404).
            ParsingError: If there's an issue parsing the HTML content.

        """

        base_url = f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p=1&type=ratings"
        all_user_ratings: list[UserRating] = []

        try:
            # Fetch the first page to determine total number of reviews/pages and collect initial ratings
            first_page_html = await self._get_html(base_url)
        except ResourceNotFoundError as e:
            raise AlbumNotFoundError(
                f"User ratings page not found for album ID {album_id} at URL: {base_url}",
            ) from e
        except NetworkError as e:
            raise ParsingError(
                f"Failed to fetch initial user ratings page for album ID {album_id}: {e}",
            ) from e

        try:
            # Extract total number of reviews to calculate total pages
            total_reviews_text = self._parse_text(
                first_page_html,
                "div.userReviewCounter",
            )
            total_reviews = 0
            if total_reviews_text:
                match = re.search(r"of (\d+) user reviews", total_reviews_text)
                if match:
                    total_reviews = self._parse_int(match.group(1))

            # Album of the Year displays 80 ratings per page
            reviews_per_page = 80
            total_pages = ceil(total_reviews / reviews_per_page) if total_reviews > 0 else 1

            # Process ratings from the first page
            for rating_block in first_page_html.css("div.userRatingBlock"):
                username_node = rating_block.css_first("div.userName a")
                rating_node = rating_block.css_first("div.ratingBlock div.rating")
                date_node = rating_block.css_first("div.date")

                if username_node and rating_node and date_node:
                    user_url_suffix = self._parse_attribute(username_node, None, "href")
                    if user_url_suffix is None:  # Explicitly check for missing href
                        raise ParsingError(
                            "Missing user URL suffix in user rating block.",
                        )
                    rating_data: UserRating = {
                        "username": self._parse_attribute(username_node, None, "title"),
                        "user_url": self._build_full_url(user_url_suffix),
                        "rating": self._parse_float(rating_node),
                        "date": self._parse_attribute(date_node, None, "title"),
                    }
                    all_user_ratings.append(rating_data)

            # If there are more pages, fetch them concurrently
            if total_pages > 1:
                urls_to_scrape_additional = [
                    f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p={page_num}&type=ratings"
                    for page_num in range(2, total_pages + 1)  # Start from page 2
                ]
                additional_html_pages = await asyncio.gather(
                    *[self._get_html(url) for url in urls_to_scrape_additional],
                )

                # Process each additional page and collect ratings
                for html in additional_html_pages:
                    for rating_block in html.css("div.userRatingBlock"):
                        username_node = rating_block.css_first("div.userName a")
                        rating_node = rating_block.css_first(
                            "div.ratingBlock div.rating",
                        )
                        date_node = rating_block.css_first("div.date")

                        if username_node and rating_node and date_node:
                            user_url_suffix = self._parse_attribute(
                                username_node,
                                None,
                                "href",
                            )
                            if user_url_suffix is None:  # Explicitly check for missing href
                                raise ParsingError(
                                    "Missing user URL suffix in user rating block.",
                                )
                            rating_data: UserRating = {
                                "username": self._parse_attribute(
                                    username_node,
                                    None,
                                    "title",
                                ),
                                "user_url": self._build_full_url(user_url_suffix),
                                "rating": self._parse_float(rating_node),
                                "date": self._parse_attribute(date_node, None, "title"),
                            }
                            all_user_ratings.append(rating_data)
            return all_user_ratings
        except Exception as e:
            raise ParsingError(
                f"Failed to parse user ratings from album ID {album_id}: {e}",
            ) from e
