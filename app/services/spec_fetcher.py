"""
Fetches remote API specifications for URL-based uploads.
"""

import ipaddress
import socket
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_SPEC_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 10


class SpecFetchError(ValueError):
    """Raised when a remote specification cannot be fetched safely."""


class ValidatingRedirectHandler(HTTPRedirectHandler):
    """Validate redirect destinations before following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_spec_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_spec_url(url: str) -> None:
    """
    Validate that a URL is suitable for server-side fetching.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SpecFetchError("URL must start with http:// or https://")

    if not parsed.hostname:
        raise SpecFetchError("URL must include a host")

    try:
        port = parsed.port
    except ValueError as exc:
        raise SpecFetchError("URL port is invalid") from exc

    try:
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SpecFetchError("Could not resolve specification URL host") from exc

    for address in _iter_resolved_addresses(addresses):
        if not _is_public_address(address):
            raise SpecFetchError("URL host must resolve to a public internet address")


def fetch_spec_from_url(url: str) -> str:
    """
    Fetch a remote JSON/YAML specification and return it as text.
    """
    validate_spec_url(url)
    request = Request(
        url,
        headers={
            "Accept": "application/json, application/yaml, text/yaml, text/plain, */*",
            "User-Agent": "SpecDrift/0.1 (+https://specdrift.dev)",
        },
    )
    opener = build_opener(ValidatingRedirectHandler)

    try:
        with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            if final_url != url:
                validate_spec_url(final_url)

            content = response.read(MAX_SPEC_BYTES + 1)
            if len(content) > MAX_SPEC_BYTES:
                raise SpecFetchError("Specification URL response is too large")

            charset = response.headers.get_content_charset() or "utf-8"
            return content.decode(charset)
    except HTTPError as exc:
        raise SpecFetchError(f"Specification URL returned HTTP {exc.code}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise SpecFetchError(f"Could not fetch specification URL: {reason}") from exc
    except UnicodeDecodeError as exc:
        raise SpecFetchError("Specification URL response is not valid text") from exc
    except TimeoutError as exc:
        raise SpecFetchError("Specification URL request timed out") from exc


def _iter_resolved_addresses(addresses: Iterable[tuple]) -> Iterable[str]:
    for entry in addresses:
        sockaddr = entry[4]
        if sockaddr:
            yield sockaddr[0]


def _is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False

    return ip.is_global
