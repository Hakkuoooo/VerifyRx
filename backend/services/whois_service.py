"""
WHOIS lookup — domain age + registrant extraction.

Why this is defensive:
WHOIS is one of the oldest internet protocols (RFC 812, 1982). Each
TLD's registry returns a different text format, and python-whois tries
to normalize them — but fields still come back in unpredictable shapes.
creation_date can be:
    - a datetime              (most .com domains)
    - a list[datetime]        (some registrars return multiple timestamps)
    - a string                (rare, when parsing fails)
    - None                    (privacy/redacted TLDs like .uk post-GDPR)

Any of those should NOT crash the whole risk check. The public function
always returns a dict with safe defaults ("Unknown", 0, False), even
when the lookup fails entirely.
"""

from datetime import datetime, timezone
from typing import Any

import whois

# Strings that show up in WHOIS records when the real registrant is
# hidden behind a privacy service. Matched case-insensitively as
# substrings. Not exhaustive — new privacy providers appear — but
# catches the big ones.
PRIVACY_MARKERS = (
    "privacy",
    "whoisguard",
    "domains by proxy",
    "redacted",
    "contact privacy",
    "perfect privacy",
    "identity protect",
    "private registration",
    "data protected",
)


def _coerce_to_datetime(value: Any) -> datetime | None:
    """
    Best-effort conversion of a WHOIS date field to a single datetime.

    python-whois can hand us a datetime, a list of datetimes (where the
    first is usually the authoritative one), a string, or None. This
    function normalizes all those cases — and returns None if nothing
    usable came back.
    """
    if value is None:
        return None

    # List: take the first element that's itself a datetime.
    if isinstance(value, list):
        for item in value:
            if isinstance(item, datetime):
                return item
        return None

    if isinstance(value, datetime):
        return value

    # String fallback: try a couple of common formats. Not exhaustive —
    # on failure we return None and the caller reports "Unknown".
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _format_age(days: int) -> str:
    """
    Turn a day count into a human-friendly string for the UI.

    47        -> "47 days"
    180       -> "5 months, 30 days"
    800       -> "2 years, 2 months"
    """
    if days < 30:
        return f"{days} days"

    if days < 365:
        months = days // 30
        remainder_days = days % 30
        if remainder_days == 0:
            return f"{months} months"
        return f"{months} months, {remainder_days} days"

    years = days // 365
    remainder_days = days % 365
    months = remainder_days // 30
    if months == 0:
        return f"{years} year{'s' if years != 1 else ''}"
    return f"{years} year{'s' if years != 1 else ''}, {months} months"


def _extract_registrant(record: Any) -> str:
    """
    Build a displayable registrant string from a WHOIS record.

    Order of preference: organization name, then country as a suffix.
    If privacy-protected, return a flag so the risk scorer can act on it.
    """
    # python-whois exposes fields as attributes AND dict keys; use getattr
    # with a fallback to handle both.
    org = getattr(record, "org", None) or getattr(record, "organization", None)
    country = getattr(record, "country", None)
    name = getattr(record, "name", None)

    # Pick the best single string we have to scan for privacy markers.
    candidate = " ".join(str(x) for x in (org, name) if x).lower()
    if any(marker in candidate for marker in PRIVACY_MARKERS):
        return "Privacy Protected"

    if org:
        org_str = str(org).strip()
        if country:
            return f"{org_str} ({country})"
        return org_str

    if name:
        return str(name).strip()

    return "Unknown"


def lookup_whois(domain: str) -> dict[str, Any]:
    """
    Run a WHOIS lookup and return structured fields for risk scoring.

    Always returns a dict with these keys, even on failure:
        domain_age:       str   — human-readable ("2 years, 3 months") or "Unknown"
        domain_age_days:  int   — 0 if creation date unavailable
        registrant:       str   — org name, "Privacy Protected", or "Unknown"

    Never raises. WHOIS is inherently unreliable (rate limits, TLD
    quirks, network hiccups) and we treat all failures as "unknown".
    """
    default = {
        "domain_age": "Unknown",
        "domain_age_days": 0,
        "registrant": "Unknown",
    }

    try:
        record = whois.whois(domain)
    except Exception:
        # python-whois raises a broad set of exceptions (PywhoisError,
        # socket errors, UnicodeDecodeError on some TLDs). We don't care
        # which — anything means "couldn't determine age/registrant".
        return default

    if record is None:
        return default

    creation = _coerce_to_datetime(getattr(record, "creation_date", None))
    if creation is not None:
        # Make both datetimes timezone-aware so subtraction works.
        if creation.tzinfo is None:
            creation = creation.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - creation).days
        # Clamp to 0 in case a registry returned a creation date in the
        # future (has happened — data entry bugs).
        age_days = max(age_days, 0)
        default["domain_age_days"] = age_days
        default["domain_age"] = _format_age(age_days)

    default["registrant"] = _extract_registrant(record)
    return default
