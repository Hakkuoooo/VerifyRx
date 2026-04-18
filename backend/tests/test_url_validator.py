"""
Unit tests for utils.url_validator.

Primary target is SSRF prevention — the single most important piece of
defensive code in this backend, because the URL checker fetches user-
supplied URLs. These tests are DNS-mock-only: no sockets are opened so
the suite stays offline-safe.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from utils.url_validator import ALLOWED_SCHEMES, validate_url


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
class TestHappyPath:
    def test_accepts_plain_domain_and_prepends_https(self):
        with patch("utils.url_validator.socket.gethostbyname", return_value="142.250.72.110"):
            url, host = validate_url("boots.com")
        assert url == "https://boots.com"
        assert host == "boots.com"

    def test_accepts_explicit_https(self):
        with patch("utils.url_validator.socket.gethostbyname", return_value="142.250.72.110"):
            url, host = validate_url("https://www.nhs.uk/page")
        assert url == "https://www.nhs.uk/page"
        assert host == "www.nhs.uk"

    def test_accepts_http(self):
        with patch("utils.url_validator.socket.gethostbyname", return_value="1.1.1.1"):
            url, host = validate_url("http://example.com")
        assert url.startswith("http://")
        assert host == "example.com"

    def test_strips_surrounding_whitespace(self):
        with patch("utils.url_validator.socket.gethostbyname", return_value="8.8.8.8"):
            url, _ = validate_url("   https://example.com   ")
        assert url == "https://example.com"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class TestInputValidation:
    @pytest.mark.parametrize("bad", ["", None, 123, [], {}])
    def test_rejects_non_string_or_empty(self, bad):
        with pytest.raises(ValueError):
            validate_url(bad)

    @pytest.mark.parametrize("scheme", [
        "file", "ftp", "gopher", "javascript", "data", "chrome",
    ])
    def test_rejects_disallowed_schemes(self, scheme):
        with pytest.raises(ValueError, match="Scheme"):
            validate_url(f"{scheme}://example.com")

    def test_http_and_https_are_the_allowed_set(self):
        # Guard against accidental scheme list widening in a future PR.
        assert ALLOWED_SCHEMES == {"http", "https"}

    def test_rejects_missing_hostname(self):
        # urlparse accepts "https:///" but hostname is None.
        with pytest.raises(ValueError, match="hostname"):
            validate_url("https:///path")


# ---------------------------------------------------------------------------
# DNS failure
# ---------------------------------------------------------------------------
class TestDnsFailure:
    def test_reraises_resolution_error(self):
        import socket as stdlib_socket

        with patch(
            "utils.url_validator.socket.gethostbyname",
            side_effect=stdlib_socket.gaierror("Name or service not known"),
        ):
            with pytest.raises(ValueError, match="Could not resolve"):
                validate_url("nonexistent-domain-foo-bar-baz.test")


# ---------------------------------------------------------------------------
# SSRF — the main defensive test bank
# ---------------------------------------------------------------------------
class TestSsrfPrevention:
    # Each row is a (hostname, resolved_ip, human_reason) triple. The
    # validator must reject every one of these; the parametrisation
    # makes it obvious from the pytest output which class of address is
    # being blocked.
    DANGEROUS = [
        # Loopback
        ("localhost", "127.0.0.1", "loopback"),
        ("malicious.test", "127.0.0.42", "loopback-other"),
        # RFC1918 private
        ("internal.test", "10.0.0.1", "rfc1918-10"),
        ("corp.test", "172.16.5.1", "rfc1918-172"),
        ("home.test", "192.168.1.1", "rfc1918-192"),
        # Link-local — CRITICAL: AWS/GCP metadata lives at 169.254.169.254
        ("metadata.test", "169.254.169.254", "cloud-metadata"),
        # IPv6 loopback
        ("v6loop.test", "::1", "ipv6-loopback"),
        # Unspecified
        ("unspec.test", "0.0.0.0", "unspecified"),
    ]

    @pytest.mark.parametrize("hostname,ip,reason", DANGEROUS)
    def test_rejects_non_public_ips(self, hostname, ip, reason):
        with patch("utils.url_validator.socket.gethostbyname", return_value=ip):
            with pytest.raises(ValueError, match="non-public IP"):
                validate_url(f"https://{hostname}")

    def test_accepts_public_ipv4(self):
        # Sanity-check the allowlist side — 1.1.1.1 (Cloudflare public DNS)
        # must not be blocked.
        with patch("utils.url_validator.socket.gethostbyname", return_value="1.1.1.1"):
            url, _ = validate_url("https://public.example.com")
        assert url == "https://public.example.com"
