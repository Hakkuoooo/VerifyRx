"""
URL validation with SSRF (Server-Side Request Forgery) prevention.

Why this file exists:
Our backend fetches user-supplied URLs (WHOIS lookup, redirect chain,
VirusTotal). Without validation, an attacker could point us at internal
addresses (127.0.0.1, 192.168.x.x, cloud metadata endpoints like
169.254.169.254) to probe or attack systems behind our firewall. This
module is the single choke point where we reject such inputs.

Always call validate_url() BEFORE making any outbound request with a
user-supplied URL.
"""

import ipaddress
import socket
from urllib.parse import urlparse


# Schemes we accept. Anything else (file://, gopher://, ftp://, javascript:)
# is rejected — those are classic SSRF escape hatches.
ALLOWED_SCHEMES = {"http", "https"}


def validate_url(raw_url: str) -> tuple[str, str]:
    """
    Validate a user-supplied URL and confirm its hostname resolves to a
    public IP address.

    Args:
        raw_url: The URL as typed by the user (may be missing scheme).

    Returns:
        A tuple of (normalized_url, hostname). The normalized URL always
        has a scheme; the hostname is the bare domain we can feed to
        WHOIS/GPhC lookups.

    Raises:
        ValueError: If the URL is malformed, uses a disallowed scheme,
                    fails DNS resolution, or resolves to a private/
                    reserved IP range.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("URL must be a non-empty string")

    url = raw_url.strip()

    # urlparse treats "boots.com" as a path, not a host. If no scheme is
    # present, prepend https:// so .netloc populates correctly.
    if "://" not in url:
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Could not parse URL: {exc}") from exc

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"Scheme '{parsed.scheme}' not allowed; only http/https accepted"
        )

    hostname = parsed.hostname  # Lowercased, credentials/port stripped.
    if not hostname:
        raise ValueError("URL is missing a hostname")

    # DNS resolve. Note: TOCTOU (time-of-check-to-time-of-use) applies —
    # DNS can return a different IP by the time we actually connect. For
    # a student project this is acceptable; production systems use a
    # pinned-IP HTTP client to close that gap.
    try:
        resolved_ip = socket.gethostbyname(hostname)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    try:
        ip_obj = ipaddress.ip_address(resolved_ip)
    except ValueError as exc:
        raise ValueError(f"Invalid IP address '{resolved_ip}'") from exc

    # The core SSRF check. Reject loopback (127/8), private RFC1918
    # (10/8, 172.16/12, 192.168/16), link-local (169.254/16 — cloud
    # metadata!), multicast, and other reserved ranges.
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        raise ValueError(
            f"URL resolves to a non-public IP ({resolved_ip}); refusing request"
        )

    return url, hostname
