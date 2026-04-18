"""
URL checker orchestrator.

This is the top-level function for Module 2. It calls each sub-service,
combines their outputs with an additive risk-scoring rubric, and
returns a populated UrlCheckResponse.

Design choice: additive, rule-based scoring (rather than a trained ML
model). Every point added to the final score can be traced to one
specific rule — essential for an explainable thesis demo, and the
`flags` list doubles as that explanation for the end user.
"""

from models.url import UrlCheckResponse
from services import gphc_registry, redirect_checker, virustotal, whois_service
from utils.url_validator import validate_url


def check_url(raw_url: str) -> UrlCheckResponse:
    """
    Run all URL checks and compute an aggregated risk score.

    Args:
        raw_url: A user-supplied URL string (scheme may be missing).

    Returns:
        A fully-populated UrlCheckResponse.

    Raises:
        ValueError: If the URL fails validation (malformed, unsupported
                    scheme, or resolves to a non-public IP).
    """
    # 1. Validation gate. Raises ValueError on bad input — the router
    #    maps that to HTTP 422.
    normalized_url, hostname = validate_url(raw_url)
    is_https = normalized_url.startswith("https://")

    # 2. Parallel-ish data collection. We run these sequentially for
    #    simplicity — each takes 1–5s, total ~10s. Good enough for a
    #    synchronous API. A production version would wrap these in
    #    asyncio.gather() or a ThreadPoolExecutor.
    whois_data = whois_service.lookup_whois(hostname)
    gphc_registered = gphc_registry.is_registered(hostname)
    redirect_count = redirect_checker.count_redirects(normalized_url)
    vt_score = virustotal.get_score(normalized_url)

    # 3. Score computation. Keep running totals + flags in lockstep so
    #    every point of risk has a matching human-readable reason.
    score = 0
    flags: list[str] = []

    if not is_https:
        score += 20
        flags.append("No HTTPS — connection is not encrypted")

    age_days = whois_data["domain_age_days"]
    # age_days == 0 means "unknown"; we don't penalise unknown ages
    # because WHOIS is unreliable on some TLDs (notably .uk).
    if 0 < age_days < 30:
        score += 25
        flags.append("Domain registered less than 30 days ago")
    elif 30 <= age_days < 180:
        score += 15
        flags.append("Domain registered less than 6 months ago")

    if not gphc_registered:
        score += 15
        flags.append("Not found in GPhC register")

    registrant = whois_data["registrant"]
    if registrant == "Privacy Protected":
        score += 10
        flags.append("WHOIS registrant uses privacy protection")

    if vt_score > 0:
        # Weight VT heavily but not dominantly — a 100% VT score adds 30
        # points, which combined with other signals pushes us well into
        # the red without overriding other rules.
        score += round(vt_score * 0.3)
        flags.append(f"Flagged by {vt_score}% of VirusTotal engines")

    if redirect_count > 2:
        score += 10
        flags.append(f"{redirect_count} redirect hops detected")
    elif redirect_count >= 1:
        score += 5
        flags.append(f"{redirect_count} redirect hop detected")

    # 4. Cap at 100 — clamps edge cases where every rule fires.
    final_score = min(score, 100)

    return UrlCheckResponse(
        url=normalized_url,
        risk_score=final_score,
        is_https=is_https,
        domain_age=whois_data["domain_age"],
        domain_age_days=age_days,
        is_gphc_registered=gphc_registered,
        whois_registrant=registrant,
        virus_total_score=vt_score,
        redirect_count=redirect_count,
        flags=flags,
    )
