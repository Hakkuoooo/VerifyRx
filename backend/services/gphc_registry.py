"""
GPhC (General Pharmaceutical Council) registry check.

We compare a hostname against a hand-curated whitelist of UK pharmacies
known to be GPhC-registered. A match is a strong positive legitimacy
signal in the risk score; a miss does NOT prove a site is illegitimate
(our list is not exhaustive), just that we can't vouch for it.

The registry file lives at data/gphc_domains.json so it can be updated
without code changes. We load it once at import time — it's tiny and
read-only.
"""

import json
from pathlib import Path

# Locate the JSON file relative to this module, not the current working
# directory (which changes depending on how uvicorn is launched).
_DATA_PATH = Path(__file__).parent.parent / "data" / "gphc_domains.json"


def _load_domains() -> frozenset[str]:
    """Load the whitelist into a frozenset for O(1) lookups."""
    try:
        with _DATA_PATH.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        # Lowercase everything for case-insensitive comparison.
        return frozenset(d.lower() for d in payload.get("domains", []))
    except (OSError, json.JSONDecodeError):
        # If the file is missing or corrupt we return an empty set —
        # every check will report "not registered", which is the safe
        # default (no false positives for legitimacy).
        return frozenset()


# Loaded once at module import. frozenset is hashable, immutable, and
# backed by a hash table — membership checks are O(1).
_GPHC_DOMAINS: frozenset[str] = _load_domains()


def is_registered(hostname: str) -> bool:
    """
    Check whether a hostname is on the GPhC whitelist.

    Matches progressively shorter suffixes so that subdomains of a
    registered domain still count:
        www.boots.com    -> matches boots.com
        shop.boots.com   -> matches boots.com
        boots.com        -> matches boots.com
        imposter-boots.com -> no match (it's not a subdomain of boots.com)

    Args:
        hostname: The bare domain (no scheme, no path). Typically the
                  second value returned by validate_url().

    Returns:
        True if the hostname or any of its parent domains is in the
        whitelist.
    """
    if not hostname:
        return False

    host = hostname.lower().strip()

    # Check the full hostname first, then each parent by stripping one
    # label at a time. We stop before a single-label suffix (e.g. "com")
    # because TLDs are never meaningful matches on their own.
    parts = host.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in _GPHC_DOMAINS:
            return True

    return False
