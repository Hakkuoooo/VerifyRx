"""
Redirect chain counter.

Multi-hop redirects are a weak but useful scam signal — they're used to
launder the final destination and track clicks. We follow the chain
with a HEAD request (body not fetched) and return the hop count.
"""

import requests

from config import settings

# Most servers send redirects as 301/302/307/308. requests handles all
# of them under allow_redirects=True and caps the chain at 30 by
# default, which is plenty — real sites use 1–2 hops, scams rarely
# exceed 5.

# A plain browser-like User-Agent. Some CDNs return 403 to the default
# "python-requests/x" string, which would make every check look like
# 0 redirects.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def count_redirects(url: str) -> int:
    """
    Count how many redirects a URL goes through to reach its final page.

    Args:
        url: A fully-validated URL (must already have http:// or https://).

    Returns:
        The number of hops in the redirect chain. Returns 0 on any
        failure (timeout, DNS error, non-2xx final status, etc.) — the
        scorer treats 0 as benign.
    """
    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=settings.request_timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        # response.history holds the intermediate responses. Length 0
        # means "arrived directly, no redirect happened".
        return len(response.history)
    except requests.RequestException:
        # Covers timeouts, connection errors, too many redirects,
        # invalid SSL, malformed URLs, etc.
        return 0
