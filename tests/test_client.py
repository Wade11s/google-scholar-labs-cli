"""HTTP client tests for ScholarLabsClient."""

import pytest
from scholar_labs.core.auth import ManualAuthProvider, AuthError, NetworkError
from scholar_labs.core.client import ScholarLabsClient


@pytest.fixture
def auth_provider():
    return ManualAuthProvider(cookie="test-cookie", xsrf_token="test-xsrf")


def test_client_builds_request_url_with_xsrf(auth_provider):
    """The client includes hl and xsrf query parameters in the request URL."""
    client = ScholarLabsClient(auth_provider)
    url = client._build_url()
    assert "hl=en" in url
    assert "xsrf=test-xsrf" in url


def test_client_builds_request_body_url_encoded(auth_provider):
    """The client sends query as URL-encoded form data."""
    client = ScholarLabsClient(auth_provider)
    body = client._build_body("test query")
    assert body == "q=test+query"


def test_client_builds_auth_headers(auth_provider):
    """The client includes browser-mimicking headers."""
    client = ScholarLabsClient(auth_provider)
    headers = client._build_headers()
    assert headers["Cookie"] == "test-cookie"
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers["Referer"].startswith("https://scholar.google.com")
    assert "Chrome" in headers["User-Agent"]


@pytest.mark.asyncio
async def test_search_raises_network_error_on_http_failure(auth_provider, httpx_mock):
    """search() raises NetworkError when the server returns 5xx."""
    httpx_mock.add_response(status_code=500)
    client = ScholarLabsClient(auth_provider)

    with pytest.raises(NetworkError):
        await client.search("test")


@pytest.mark.asyncio
async def test_search_raises_auth_error_on_403(auth_provider, httpx_mock):
    """search() raises AuthError when the server returns 403."""
    httpx_mock.add_response(status_code=403)
    client = ScholarLabsClient(auth_provider)

    with pytest.raises(AuthError):
        await client.search("test")
