import socket

import pytest

from app.services.spec_fetcher import SpecFetchError, validate_spec_url


def _mock_getaddrinfo(address):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]


def test_validate_spec_url_allows_public_http_url(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _mock_getaddrinfo("93.184.216.34"))

    validate_spec_url("https://example.com/openapi.yaml")


def test_validate_spec_url_rejects_non_http_scheme():
    with pytest.raises(SpecFetchError, match="http:// or https://"):
        validate_spec_url("file:///etc/passwd")


def test_validate_spec_url_rejects_private_hosts(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: _mock_getaddrinfo("127.0.0.1"))

    with pytest.raises(SpecFetchError, match="public internet address"):
        validate_spec_url("https://localhost/openapi.yaml")


def test_validate_spec_url_rejects_unresolvable_hosts(monkeypatch):
    def fail_resolution(*args, **kwargs):
        raise socket.gaierror()

    monkeypatch.setattr(socket, "getaddrinfo", fail_resolution)

    with pytest.raises(SpecFetchError, match="Could not resolve"):
        validate_spec_url("https://example.invalid/openapi.yaml")


def test_validate_spec_url_rejects_invalid_port():
    with pytest.raises(SpecFetchError, match="port is invalid"):
        validate_spec_url("https://example.com:bad/openapi.yaml")
