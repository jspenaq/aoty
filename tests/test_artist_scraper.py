from unittest.mock import AsyncMock

import pytest
from selectolax.parser import HTMLParser

from aoty.config import AOTY_BASE_URL
from aoty.exceptions import ArtistNotFoundError, NetworkError, ParsingError, ResourceNotFoundError
from aoty.models import AlbumSummary, ArtistSummary, SongSummary
from aoty.scrapers.artist import ArtistScraper


@pytest.fixture
def artist_scraper():
    """Fixture to provide an ArtistScraper instance with a mocked _get_html."""
    scraper = ArtistScraper()
    # Mock the _get_html method directly on the scraper instance
    scraper._get_html = AsyncMock()
    return scraper


def create_mock_html_response(html_content: str) -> HTMLParser:
    """Helper to create a parsed HTML response from a string."""
    return HTMLParser(html_content)


# --- Test scrape_artist_by_id / _scrape_artist_page ---


@pytest.mark.asyncio
async def test_scrape_artist_by_id_success(artist_scraper):
    """Test successful scraping of a full artist page with all sections."""
    artist_id = "12345-test-artist"
    mock_html = """
    <html><body>
        <h1 class="artistHeadline">Test Artist</h1>
        <div class="artistImage"><img data-src="/img/artist_cover_default.jpg" src="/img/artist_cover_small.jpg"></div>
        <div class="artistCriticScore"><span itemprop="ratingValue">7.5</span></div>
        <div class="artistCriticScoreBox"><span itemprop="reviewCount">10</span></div>
        <div class="artistUserScore">8.0</div>
        <div class="artistUserScoreBox"><strong>1,000</strong> user reviews</div>
        <div class="artistTopBox info">
            <div class="detailRow"><span>Genre:</span> <a href="/genre/1-pop/">Pop</a>, <a href="/genre/2-rock/">Rock</a></div>
            <div class="detailRow"><span>Member Of:</span> <a href="/artist/67890-band-a.php">Band A</a>, <a href="/artist/98765-band-b.php">Band B</a></div>
        </div>

        <div id="albumOutput">
            <h2 class="subHeadline">Albums</h2>
            <div class="albumBlock small" data-type="">
                <div class="image"><a href="/album/1-album-a.php"><img src="/img/album_a.jpg" alt="Test Artist - Album A"></a></div>
                <a href="/album/1-album-a.php"><div class="albumTitle">Album A</div></a>
                <div class="type">2020</div>
                <div class="ratingRowContainer"><div class="ratingRow"><div class="ratingBlock"><div class="rating">70</div></div><div class="ratingText">critic score</div> <div class="ratingText">(5)</div></div></div>
            </div>
            <h2 class="subHeadline">EPs</h2>
            <div class="albumBlock small" data-type="">
                <div class="image"><a href="/album/2-ep-b.php"><img src="/img/ep_b.jpg" alt="Test Artist - EP B"></a></div>
                <a href="/album/2-ep-b.php"><div class="albumTitle">EP B</div></a>
                <div class="type">2021</div>
                <div class="ratingRowContainer"><div class="ratingRow"><div class="ratingBlock"><div class="rating">85</div></div><div class="ratingText">user score</div> <div class="ratingText">(100)</div></div></div>
            </div>
            <h2 class="subHeadline">Singles<div class="viewAll"><a href="?type=single">View All</a></div></h2>
            <div class="albumBlock small" data-type="">
                <div class="image"><a href="/album/3-single-c.php"><img src="/img/single_c.jpg" alt="Test Artist - Single C"></a></div>
                <a href="/album/3-single-c.php"><div class="albumTitle">Single C</div></a>
                <div class="type">2022</div>
            </div>
            <h2 class="subHeadline">Appears On</h2>
            <div class="albumBlock small" data-type="lp">
                <div class="image"><a href="/album/4-collab-d.php"><img src="/img/collab_d.jpg" alt="Other Artist - Collab D"></a></div>
                <a href="/artist/111-other-artist/"><div class="artistTitle">Other Artist</div></a>
                <a href="/album/4-collab-d.php"><div class="albumTitle">Collab D</div></a>
                <div class="type">2023 • LP</div>
                <div class="ratingRowContainer"><div class="ratingRow"><div class="ratingBlock"><div class="rating">60</div></div><div class="ratingText">user score</div> <div class="ratingText">(50)</div></div></div>
            </div>
        </div>

        <div class="mediaList">
            <table class="trackListTable">
                <tr>
                    <td class="songAlbum">
                        <div style="font-weight: bold"><a href="/song/1-song-x.php">Song X</a></div>
                        <div class="gray-font">Album A</div>
                    </td>
                    <td class="coverart"><a href="/album/1-album-a.php"><img src="/img/album_a_small.jpg"></a></td>
                    <td class="trackRating"><span title="10 Rating">7.0</span></td>
                </tr>
                <tr>
                    <td class="songAlbum">
                        <div style="font-weight: bold"><a href="/song/2-song-y.php">Song Y</a></div>
                        <div class="gray-font">EP B</div>
                    </td>
                    <td class="coverart"><a href="/album/2-ep-b.php"><img src="/img/ep_b_small.jpg"></a></td>
                    <td class="trackRating"><span title="20 Rating">8.5</span></td>
                </tr>
            </table>
        </div>

        <div class="relatedArtists">
            <div class="artistBlock">
                <div class="image"><img src="/img/similar_artist_1.jpg"></div>
                <div class="name"><a href="/artist/222-similar-1.php">Similar Artist 1</a></div>
            </div>
            <div class="artistBlock">
                <div class="image"><img src="/img/similar_artist_2.jpg"></div>
                <div class="name"><a href="/artist/333-similar-2.php">Similar Artist 2</a></div>
            </div>
        </div>
    </body>
    </html>
    """
    artist_scraper._get_html.return_value = create_mock_html_response(mock_html)

    artist = await artist_scraper.scrape_artist_by_id(artist_id)

    expected_url = f"{AOTY_BASE_URL}/artist/{artist_id}/"
    artist_scraper._get_html.assert_awaited_once_with(expected_url)

    assert artist is not None
    assert artist["name"] == "Test Artist"
    assert artist["url"] == expected_url
    assert artist["id"] == 12345
    assert artist["cover_url"] == "/img/artist_cover_default.jpg"
    assert artist["critic_score"] == 7.5
    assert artist["critic_review_count"] == 10
    assert artist["user_score"] == 8.0
    assert artist["user_rating_count"] == 1000
    assert artist["genres"] == ["Pop", "Rock"]
    assert artist["associated_artists"] == [
        ArtistSummary(
            name="Band A",
            url=f"{AOTY_BASE_URL}/artist/67890-band-a.php",
            image_url=None,
        ),
        ArtistSummary(
            name="Band B",
            url=f"{AOTY_BASE_URL}/artist/98765-band-b.php",
            image_url=None,
        ),
    ]

    # Discography assertions
    assert len(artist["discography"]) == 4
    assert artist["discography"][0] == AlbumSummary(
        title="Album A",
        artist="Test Artist",
        url=f"{AOTY_BASE_URL}/album/1-album-a.php",
        year=2020,
        type="Albums",
        cover_url="/img/album_a.jpg",
        critic_score=70.0,
        critic_review_count=5,
        user_score=None,
        user_rating_count=None,
    )
    assert artist["discography"][1] == AlbumSummary(
        title="EP B",
        artist="Test Artist",
        url=f"{AOTY_BASE_URL}/album/2-ep-b.php",
        year=2021,
        type="EPs",
        cover_url="/img/ep_b.jpg",
        critic_score=None,
        critic_review_count=None,
        user_score=85.0,
        user_rating_count=100,
    )
    assert artist["discography"][2] == AlbumSummary(
        title="Single C",
        artist="Test Artist",
        url=f"{AOTY_BASE_URL}/album/3-single-c.php",
        year=2022,
        type="Singles",
        cover_url="/img/single_c.jpg",
        critic_score=None,
        critic_review_count=None,
        user_score=None,
        user_rating_count=None,
    )
    assert artist["discography"][3] == AlbumSummary(
        title="Collab D",
        artist="Other Artist",  # This should be "Other Artist" as per HTML
        url=f"{AOTY_BASE_URL}/album/4-collab-d.php",
        year=2023,
        type="Appears On",
        cover_url="/img/collab_d.jpg",
        critic_score=None,
        critic_review_count=None,
        user_score=60.0,
        user_rating_count=50,
    )

    # Top Songs assertions
    assert len(artist["top_songs"]) == 2
    assert artist["top_songs"][0] == SongSummary(
        title="Song X",
        url=f"{AOTY_BASE_URL}/song/1-song-x.php",
        album_title="Album A",
        album_url=f"{AOTY_BASE_URL}/album/1-album-a.php",
        cover_url="/img/album_a_small.jpg",
        rating=7.0,
        rating_count=10,
    )
    assert artist["top_songs"][1] == SongSummary(
        title="Song Y",
        url=f"{AOTY_BASE_URL}/song/2-song-y.php",
        album_title="EP B",
        album_url=f"{AOTY_BASE_URL}/album/2-ep-b.php",
        cover_url="/img/ep_b_small.jpg",
        rating=8.5,
        rating_count=20,
    )

    # Similar Artists assertions
    assert len(artist["similar_artists"]) == 2
    assert artist["similar_artists"][0] == ArtistSummary(
        name="Similar Artist 1",
        url=f"{AOTY_BASE_URL}/artist/222-similar-1.php",
        image_url="/img/similar_artist_1.jpg",
    )
    assert artist["similar_artists"][1] == ArtistSummary(
        name="Similar Artist 2",
        url=f"{AOTY_BASE_URL}/artist/333-similar-2.php",
        image_url="/img/similar_artist_2.jpg",
    )


@pytest.mark.asyncio
async def test_scrape_artist_by_id_not_found(artist_scraper):
    """Test ArtistNotFoundError is raised when the artist page returns 404."""
    artist_id = "999-nonexistent-artist"
    artist_scraper._get_html.side_effect = ResourceNotFoundError("Not Found")

    with pytest.raises(ArtistNotFoundError) as excinfo:
        await artist_scraper.scrape_artist_by_id(artist_id)
    assert f"Artist not found at URL: {AOTY_BASE_URL}/artist/{artist_id}/" in str(excinfo.value)


@pytest.mark.asyncio
async def test_scrape_artist_by_id_network_error(artist_scraper):
    """Test ParsingError is raised for network issues fetching artist page."""
    artist_id = "123-artist"
    artist_scraper._get_html.side_effect = NetworkError("Connection failed")

    with pytest.raises(ParsingError) as excinfo:
        await artist_scraper.scrape_artist_by_id(artist_id)
    assert (
        f"Failed to fetch artist page {AOTY_BASE_URL}/artist/{artist_id}/: Connection failed"
        in str(
            excinfo.value,
        )
    )


@pytest.mark.asyncio
async def test_scrape_artist_by_id_parsing_error(artist_scraper):
    """Test ParsingError is raised for malformed HTML on artist page."""
    artist_id = "123-malformed-artist"
    # Mock HTML that is missing critical elements, e.g., artistHeadline, leading to a parsing error
    mock_html = """
    <html><body>
        <!-- Missing h1.artistHeadline -->
        <div class="artistImage"><img src="/img/artist_cover_small.jpg"></div>
    </body></html>
    """
    artist_scraper._get_html.return_value = create_mock_html_response(mock_html)

    with pytest.raises(ParsingError) as excinfo:
        await artist_scraper.scrape_artist_by_id(artist_id)
    assert f"Failed to parse artist data from {AOTY_BASE_URL}/artist/{artist_id}/" in str(
        excinfo.value,
    )
    # Expecting an error related to failing to parse the artist name
    assert "Could not parse artist name" in str(excinfo.value)


@pytest.mark.asyncio
async def test_scrape_artist_by_id_no_discography_or_songs_or_similar(artist_scraper):
    """Test scraping an artist page with minimal content (no discography, songs, or similar artists)."""
    artist_id = "456-minimal-artist"
    mock_html = """
    <html><body>
        <h1 class="artistHeadline">Minimal Artist</h1>
        <div class="artistImage"><img data-src="/img/artist_cover_default.jpg" src="/img/artist_cover_small.jpg"></div>
        <div class="artistCriticScore"><span itemprop="ratingValue">6.0</span></div>
        <div class="artistCriticScoreBox"><span itemprop="reviewCount">1</span></div>
        <div class="artistUserScore">7.0</div>
        <div class="artistUserScoreBox"><strong>10</strong> user reviews</div>
        <div class="artistTopBox info">
            <div class="detailRow"><span>Genre:</span> <a href="/genre/10-ambient/">Ambient</a></div>
        </div>
        <!-- No div#albumOutput -->
        <!-- No div.mediaList -->
        <!-- No div.relatedArtists -->
    </body>
    </html>
    """
    artist_scraper._get_html.return_value = create_mock_html_response(mock_html)

    artist = await artist_scraper.scrape_artist_by_id(artist_id)

    expected_url = f"{AOTY_BASE_URL}/artist/{artist_id}/"
    artist_scraper._get_html.assert_awaited_once_with(expected_url)

    assert artist is not None
    assert artist["name"] == "Minimal Artist"
    assert artist["discography"] == []
    assert artist["top_songs"] == []
    assert artist["similar_artists"] == []
    assert artist["genres"] == ["Ambient"]
    assert artist["critic_score"] == 6.0
    assert artist["user_score"] == 7.0


@pytest.mark.asyncio
async def test_scrape_artist_by_url_success(artist_scraper):
    """Test successful scraping using scrape_artist_by_url."""
    artist_url = f"{AOTY_BASE_URL}/artist/12345-test-artist/"
    mock_html = """
    <html><body>
        <h1 class="artistHeadline">Test Artist</h1>
        <div class="artistImage"><img data-src="/img/artist_cover_default.jpg" src="/img/artist_cover_small.jpg"></div>
    </body>
    </html>
    """
    artist_scraper._get_html.return_value = create_mock_html_response(mock_html)

    artist = await artist_scraper.scrape_artist_by_url(artist_url)

    artist_scraper._get_html.assert_awaited_once_with(artist_url)
    assert artist is not None
    assert artist["name"] == "Test Artist"
    assert artist["url"] == artist_url
    assert artist["id"] == 12345  # Ensure ID is parsed from URL
