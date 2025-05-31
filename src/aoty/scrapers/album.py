import re
import asyncio
from typing import List, Optional
from math import ceil  # Import ceil for calculating total pages

from aoty.scrapers.base import BaseScraper
from aoty.exceptions import AlbumNotFoundError, ParsingError
from aoty.models import Album, Review, Track, CriticReview, AlbumLink, UserRating
from aoty.config import AOTY_BASE_URL


class AlbumScraper(BaseScraper):
    """
    Scraper for Album of the Year album pages.
    """

    async def scrape_album_by_id(self, album_id: str) -> Optional[Album]:
        """
        Scrapes album data using its ID.
        """
        url = f"{AOTY_BASE_URL}/album/{album_id}.php"
        return await self._scrape_album_page(url)

    async def _scrape_album_page(self, url: str) -> Optional[Album]:
        """
        Internal method to scrape an album page URL.
        """
        try:
            html = await self._get_html(url)
        except Exception as e:
            if "404" in str(e):  # Check for 404 specifically
                raise AlbumNotFoundError(f"Album not found at URL: {url}") from e
            raise  # Re-raise other exceptions

        try:
            album_data: Album = {
                "title": self._parse_text(html, 'h1.albumTitle span[itemprop="name"]'),
                "artist": self._parse_text(html, 'div.artist span[itemprop="name"] a'),
                "url": url,
                "id": (
                    int(re.search(r"/album/(\d+)", url).group(1))
                    if re.search(r"/album/(\d+)", url)
                    else None
                ),
                "genres": [],
                # "description": self._parse_attribute(html, 'meta[name="description"]', 'content'),
                "release_date": None,
                "format": None,
                "labels": [],
                "producers": [],
                "writers": [],
                "credits": None,
            }

            # Cover URL
            cover_img = html.css_first("div.albumTopBox.cover img")
            if cover_img:
                srcset = cover_img.attributes.get("srcset")
                if srcset:
                    # Take the last (presumably largest) URL from srcset
                    album_data["cover_url"] = (
                        srcset.split(",")[-1].strip().split(" ")[0]
                    )
                else:
                    album_data["cover_url"] = cover_img.attributes.get(
                        "data-src"
                    ) or cover_img.attributes.get("src")

            # Critic Score
            critic_score_link = html.css_first(
                'div.albumCriticScore span[itemprop="ratingValue"] a'
            )
            if critic_score_link:
                album_data["critic_score"] = self._parse_float(
                    critic_score_link, attribute="title"
                )

            album_data["critic_review_count"] = self._parse_float(
                html,
                'div.albumCriticScoreBox span[itemprop="ratingCount"]',
                default=None,
            )

            critic_rank_text = self._parse_text(
                html, "div.albumCriticScoreBox .text.gray"
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
                    user_score_link, attribute="title"
                )

            user_rating_count_text = self._parse_text(
                html, "div.albumUserScoreBox .text.numReviews strong"
            )
            if user_rating_count_text:
                album_data["user_rating_count"] = int(
                    user_rating_count_text.replace(",", "")
                )

            user_rank_text = self._parse_text(
                html, "div.albumUserScoreBox .text.gray strong a"
            )
            if user_rank_text:
                match = re.search(r"#(\d+)", user_rank_text)
                if match:
                    album_data["user_rank_year"] = int(match.group(1))

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

                        # Get the full text of the detail row and remove the label text to get the value
                        full_row_text = detail_row.text(strip=True)
                        value_text = full_row_text.replace(label_text_raw, "").strip()

                        if label_text_normalized == "releasedate":
                            album_data["release_date"] = value_text
                        elif label_text_normalized == "format":
                            album_data["format"] = value_text
                        elif label_text_normalized == "label":
                            album_data["labels"] = [
                                {
                                    "name": a.text(strip=True),
                                    "url": AOTY_BASE_URL + a.attributes.get("href"),
                                }
                                for a in detail_row.css("a")
                            ]
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
                        elif label_text_normalized == "producer":
                            album_data["producers"] = [
                                {
                                    "name": a.text(strip=True),
                                    "url": AOTY_BASE_URL + a.attributes.get("href"),
                                }
                                for a in detail_row.css("a:not(.showAlbumCredits)")
                            ]
                        elif label_text_normalized == "writer":
                            album_data["writers"] = [
                                {
                                    "name": a.text(strip=True),
                                    "url": AOTY_BASE_URL + a.attributes.get("href"),
                                }
                                for a in detail_row.css("a:not(.showAlbumCredits)")
                            ]

            # Tracklist
            tracklist: List[Track] = []
            for i, row in enumerate(html.css("table.trackListTable tr")):
                track_number_node = row.css_first("td.trackNumber")
                track_title_node = row.css_first("td.trackTitle a")
                track_duration_node = row.css_first("td.trackTitle div.length")
                track_rating_node = row.css_first("td.trackRating span")

                if track_number_node and track_title_node:
                    track: Track = {
                        "number": int(track_number_node.text(strip=True)),
                        "title": track_title_node.text(strip=True),
                        "url": AOTY_BASE_URL + track_title_node.attributes.get("href"),
                        "duration": (
                            track_duration_node.text(strip=True)
                            if track_duration_node
                            else None
                        ),
                        "featured_artists": [],
                        "rating": None,
                        "rating_count": None,
                    }

                    featured_artists_nodes = row.css(
                        "td.trackTitle div.featuredArtists a"
                    )
                    if featured_artists_nodes:
                        track["featured_artists"] = [
                            {
                                "name": fa.text(strip=True),
                                "url": AOTY_BASE_URL + fa.attributes.get("href"),
                            }
                            for fa in featured_artists_nodes
                        ]

                    if track_rating_node:
                        track["rating"] = self._parse_float(
                            track_rating_node, None, default=None
                        )
                        rating_count_title = track_rating_node.attributes.get("title")
                        if rating_count_title:
                            count_match = re.search(
                                r"(\d+)\s*Ratings", rating_count_title
                            )
                            if count_match:
                                track["rating_count"] = int(count_match.group(1))
                    tracklist.append(track)
            album_data["tracklist"] = tracklist

            total_length_text = self._parse_text(html, "div.totalLength")
            if total_length_text:
                album_data["total_length"] = total_length_text.replace(
                    "Total Length: ", ""
                ).strip()

            # Third-party links
            links: List[AlbumLink] = []
            for link_node in html.css("div.buyButtons a"):
                link_name = link_node.attributes.get("title")
                link_url = link_node.attributes.get("href")
                if link_name and link_url:
                    links.append({"name": link_name, "url": link_url})
            album_data["links"] = links

            # Critic Reviews
            critic_reviews: List[CriticReview] = []
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
                        "publication_url": AOTY_BASE_URL
                        + publication_node.attributes.get("href"),
                        "author_name": (
                            author_node.text(strip=True) if author_node else None
                        ),
                        "author_url": (
                            AOTY_BASE_URL + author_node.attributes.get("href")
                            if author_node
                            else None
                        ),
                        "score": float(score_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "url": link_node.attributes.get("href") if link_node else None,
                        "date": (
                            date_node.attributes.get("title") if date_node else None
                        ),
                    }
                    critic_reviews.append(review)
            album_data["critic_reviews"] = critic_reviews

            # User Reviews (Popular and Recent)
            popular_user_reviews: List[Review] = []
            for review_row in html.css(
                'section#users:has(h2 a[href*="popular"]) div.albumReviewRow'
            ):
                username_node = review_row.css_first("div.userReviewName a")
                rating_node = review_row.css_first("div.ratingBlock div.rating")
                text_node = review_row.css_first("div.albumReviewText.user")
                date_node = review_row.css_first("div.albumReviewLinks .review_date")
                likes_node = review_row.css_first("div.review_likes")
                comment_count_node = review_row.css_first("div.comment_count")

                if username_node and rating_node:
                    review: Review = {
                        "username": username_node.text(strip=True),
                        "user_url": AOTY_BASE_URL
                        + username_node.attributes.get("href"),
                        "rating": float(rating_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "date": date_node.text(strip=True) if date_node else None,
                        "likes": (
                            int(likes_node.text(strip=True))
                            if likes_node and likes_node.text(strip=True).isdigit()
                            else 0
                        ),
                        "comment_count": (
                            int(comment_count_node.text(strip=True))
                            if comment_count_node
                            and comment_count_node.text(strip=True).isdigit()
                            else 0
                        ),
                    }
                    popular_user_reviews.append(review)
            album_data["popular_user_reviews"] = popular_user_reviews

            recent_user_reviews: List[Review] = []
            for review_row in html.css(
                'section#users:has(h2 a[href*="recent"]) div.albumReviewRow'
            ):
                username_node = review_row.css_first("div.userReviewName a")
                rating_node = review_row.css_first("div.ratingBlock div.rating")
                text_node = review_row.css_first("div.albumReviewText.user")
                date_node = review_row.css_first("div.albumReviewLinks .review_date")
                likes_node = review_row.css_first("div.review_likes")
                comment_count_node = review_row.css_first("div.comment_count")

                if username_node and rating_node:
                    review: Review = {
                        "username": username_node.text(strip=True),
                        "user_url": AOTY_BASE_URL
                        + username_node.attributes.get("href"),
                        "rating": float(rating_node.text(strip=True)),
                        "text": text_node.text(strip=True) if text_node else None,
                        "date": date_node.text(strip=True) if date_node else None,
                        "likes": (
                            int(likes_node.text(strip=True))
                            if likes_node and likes_node.text(strip=True).isdigit()
                            else 0
                        ),
                        "comment_count": (
                            int(comment_count_node.text(strip=True))
                            if comment_count_node
                            and comment_count_node.text(strip=True).isdigit()
                            else 0
                        ),
                    }
                    recent_user_reviews.append(review)
            album_data["recent_user_reviews"] = recent_user_reviews

            # Similar Albums
            similar_albums_list = []
            for album_block in html.css(
                'div.section:has(h2 a[href*="similar"]) .albumBlock.small'
            ):
                title_node = album_block.css_first("a div.albumTitle")
                artist_node = album_block.css_first("a div.artistTitle")
                link_node = album_block.css_first("a")
                if title_node and artist_node and link_node:
                    similar_albums_list.append(
                        {
                            "title": title_node.text(strip=True),
                            "artist": artist_node.text(strip=True),
                            "url": AOTY_BASE_URL + link_node.attributes.get("href"),
                        }
                    )
            album_data["similar_albums"] = similar_albums_list

            # More by Artist
            more_by_artist_list = []
            for album_block in html.css(
                'div.section:has(h2 a[href*="artist"]) .albumBlock.small'
            ):
                title_node = album_block.css_first("a div.albumTitle")
                year_node = album_block.css_first("div.type")
                link_node = album_block.css_first("a")
                if title_node and year_node and link_node:
                    more_by_artist_list.append(
                        {
                            "title": title_node.text(strip=True),
                            "year": (
                                int(year_node.text(strip=True))
                                if year_node.text(strip=True).isdigit()
                                else None
                            ),
                            "url": AOTY_BASE_URL + link_node.attributes.get("href"),
                        }
                    )
            album_data["more_by_artist"] = more_by_artist_list

            # Contributions By
            contributions_by_list = []
            for contributor_node in html.css("div#contributions a"):
                contributions_by_list.append(
                    {
                        "name": contributor_node.text(strip=True),
                        "url": AOTY_BASE_URL + contributor_node.attributes.get("href"),
                    }
                )
            album_data["contributions_by"] = contributions_by_list

            return album_data

        except Exception as e:
            raise ParsingError(f"Failed to parse album data from {url}: {e}") from e

    async def scrape_user_reviews_ratings(self, album_id: str) -> List[UserRating]:
        """
        Scrapes all user ratings (without review text) for a given album ID across all pages.
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
        base_url = f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?type=ratings"
        all_user_ratings: List[UserRating] = []

        try:
            # Fetch the first page to determine total number of reviews/pages
            first_page_html = await self._get_html(base_url)
        except Exception as e:
            if "404" in str(e):
                raise AlbumNotFoundError(
                    f"User ratings page not found for album ID {album_id} at URL: {base_url}"
                ) from e
            raise ParsingError(
                f"Failed to fetch initial user ratings page for album ID {album_id}: {e}"
            ) from e

        try:
            # Extract total number of reviews to calculate total pages
            total_reviews_text = self._parse_text(
                first_page_html, "div.userReviewCounter"
            )
            total_reviews = 0
            if total_reviews_text:
                match = re.search(r"of (\d+) user reviews", total_reviews_text)
                if match:
                    total_reviews = int(match.group(1))

            # Album of the Year displays 80 ratings per page
            reviews_per_page = 80
            total_pages = (
                ceil(total_reviews / reviews_per_page) if total_reviews > 0 else 1
            )

            # Prepare URLs for all pages
            urls_to_scrape = [
                f"{AOTY_BASE_URL}/album/{album_id}/user-reviews/?p={page_num}&type=ratings"
                for page_num in range(1, total_pages + 1)
            ]

            # Fetch all pages concurrently
            html_pages = await asyncio.gather(
                *[self._get_html(url) for url in urls_to_scrape]
            )

            # Process each page and collect ratings
            for html in html_pages:
                for rating_block in html.css("div.userRatingBlock"):
                    username_node = rating_block.css_first("div.userName a")
                    rating_node = rating_block.css_first("div.ratingBlock div.rating")
                    date_node = rating_block.css_first("div.date")

                    if username_node and rating_node and date_node:
                        rating_data: UserRating = {
                            "username": self._parse_attribute(
                                username_node, None, "title"
                            ),
                            "user_url": AOTY_BASE_URL
                            + self._parse_attribute(username_node, None, "href"),
                            "rating": self._parse_float(rating_node),
                            "date": self._parse_attribute(date_node, None, "title"),
                        }
                        all_user_ratings.append(rating_data)
            return all_user_ratings
        except Exception as e:
            raise ParsingError(
                f"Failed to parse user ratings from album ID {album_id}: {e}"
            ) from e
