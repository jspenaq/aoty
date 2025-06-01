class AOTYError(Exception):
    """Base exception for all AOTY scraper errors.

    This exception should be inherited by all custom exceptions
    in the AOTY scraper.
    """
    pass


class AlbumNotFoundError(AOTYError):
    """Raised when an album is not found (e.g., 404).

    This exception indicates that the requested album could not be
    found on the website. This might be due to an invalid URL or
    the album being removed from the site.
    """
    pass


class ParsingError(AOTYError):
    """Raised when there is an error parsing HTML content.

    This exception indicates that the scraper failed to extract
    the necessary information from the HTML structure of the page.
    This could be due to changes in the website's layout or
    incorrect parsing logic.
    """
    pass


class ResourceNotFoundError(AOTYError):
    """Raised when a requested resource (e.g., page, image) is not found (404).

    This exception indicates that a specific resource, such as an image
    or a webpage, could not be found. This is often due to a broken
    link or the resource being removed from the server.
    """
    pass


class NetworkError(AOTYError):
    """Raised for network-related issues or non-200 HTTP responses.

    This exception indicates that there was a problem with the network
    connection or that the server returned an unexpected HTTP status code
    (other than 200 OK). This could be due to network outages, server
    errors, or incorrect URLs.
    """
    pass
