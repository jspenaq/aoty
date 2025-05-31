import os

# Base URL for the Album of the Year website
AOTY_BASE_URL = "https://www.albumoftheyear.org"

# # Request timeout in seconds
REQUEST_TIMEOUT_SECONDS = int(os.getenv("AOTY_REQUEST_TIMEOUT_SECONDS", 10))
