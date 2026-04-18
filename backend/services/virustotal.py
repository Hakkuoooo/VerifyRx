"""
VirusTotal API v3 client — URL reputation lookup.

VirusTotal aggregates verdicts from 70+ security vendors. A URL
flagged as malicious/suspicious by multiple engines is a strong scam
signal; a URL with zero flags is not necessarily clean (unknown URLs
return 404), just unseen.

Free tier: 4 req/min, 500/day. We don't batch or queue — if rate
limited we return 0 for this check and let the rest of the risk score
stand.

If VIRUSTOTAL_API_KEY is unset, this module is effectively a no-op:
get_score() returns 0 without making any network call. That lets a
student run the project locally before signing up for a key.
"""

import base64

import requests

from config import settings

_API_BASE = "https://www.virustotal.com/api/v3"


def _encode_url_id(url: str) -> str:
    """
    VirusTotal's URL resource ID is base64url(url) without padding.
    Passing the raw URL in the path wouldn't survive URL parsing.
    """
    encoded = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def get_score(url: str) -> int:
    """
    Query VirusTotal for a URL's reputation and return a 0–100 risk
    score derived from the ratio of engines that flagged it.

    Args:
        url: The full URL to query (must include scheme).

    Returns:
        An integer 0–100. Returns 0 when:
          * no API key is configured
          * VT has no record of the URL (404)
          * we're rate-limited (429)
          * any network / parsing error occurs
        Errors are swallowed by design — this check is advisory, not
        authoritative, and shouldn't ever crash the wider risk analysis.
    """
    if not settings.virustotal_api_key:
        # Dev-friendly: no key, no request, no noise.
        return 0

    url_id = _encode_url_id(url)
    endpoint = f"{_API_BASE}/urls/{url_id}"
    headers = {"x-apikey": settings.virustotal_api_key}

    try:
        response = requests.get(
            endpoint, headers=headers, timeout=settings.request_timeout
        )
    except requests.RequestException:
        return 0

    if response.status_code != 200:
        # 404 (never scanned), 429 (rate limited), 401 (bad key), etc.
        # All map to "no usable data" from our point of view.
        return 0

    try:
        stats = response.json()["data"]["attributes"]["last_analysis_stats"]
    except (KeyError, ValueError):
        # Malformed payload — VT changed their schema or we hit a proxy
        # returning HTML. Either way, fail safe.
        return 0

    malicious = int(stats.get("malicious", 0))
    suspicious = int(stats.get("suspicious", 0))
    total = sum(int(v) for v in stats.values())

    if total == 0:
        return 0

    raw_score = (malicious + suspicious) / total * 100
    return min(round(raw_score), 100)
