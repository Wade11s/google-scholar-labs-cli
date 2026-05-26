import json

import pytest

from scholar_labs.core.auth import AuthConfigStore, ChromeProfileAuthConfig
from scholar_labs.core.browser_auth import BrowserCookieMaterial, BrowserProfile
from scholar_labs.core.login import LoginError, LoginRateLimitError, LoginService, XsrfDiscovery


@pytest.mark.asyncio
async def test_xsrf_discovery_extracts_token_from_scholar_labs_page(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text='<script>fetch("/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf")</script>',
    )

    token = await XsrfDiscovery().discover("SID=sid-value", hl="en")

    assert token == "test-xsrf"
    request = httpx_mock.get_requests()[0]
    assert request.headers["User-Agent"].startswith("Mozilla/5.0")
    assert request.headers["Referer"] == "https://scholar.google.com/scholar_labs/search"
    assert request.headers["Accept-Language"] == "en-US,en;q=0.9"


@pytest.mark.asyncio
async def test_xsrf_discovery_extracts_token_from_escaped_scholar_labs_page(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text=(
            r'<script>AF_initDataCallback({"data":'
            r'"/scholar_labs/search/session_data?hl\x3den\x26xsrf\x3descaped-xsrf"});'
            r"</script>"
        ),
    )

    token = await XsrfDiscovery().discover("SID=sid-value", hl="en")

    assert token == "escaped-xsrf"


@pytest.mark.asyncio
async def test_xsrf_discovery_falls_back_to_browser_page_on_forbidden(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        status_code=403,
    )

    token = await XsrfDiscovery(
        browser_page_discovery=FakeBrowserPageDiscovery("browser-xsrf")
    ).discover("SID=sid-value", hl="en")

    assert token == "browser-xsrf"


@pytest.mark.asyncio
async def test_xsrf_discovery_falls_back_to_browser_page_on_rate_limit(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        status_code=429,
    )

    token = await XsrfDiscovery(
        browser_page_discovery=FakeBrowserPageDiscovery("browser-xsrf")
    ).discover("SID=sid-value", hl="en")

    assert token == "browser-xsrf"


@pytest.mark.asyncio
async def test_xsrf_discovery_reports_missing_token(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text="<html>No token</html>",
    )

    with pytest.raises(LoginError, match="XSRF"):
        await XsrfDiscovery(
            browser_page_discovery=FakeBrowserPageDiscovery(None)
        ).discover("SID=sid-value", hl="en")


@pytest.mark.asyncio
async def test_xsrf_discovery_reports_rate_limit_without_browser_recovery(httpx_mock):
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        status_code=429,
        headers={"Retry-After": "60"},
    )

    with pytest.raises(LoginRateLimitError, match="retry after 60 seconds"):
        await XsrfDiscovery(
            browser_page_discovery=FakeBrowserPageDiscovery(None)
        ).discover("SID=sid-value", hl="en")


@pytest.mark.asyncio
async def test_login_service_validates_and_writes_credential_source_record(tmp_path, httpx_mock):
    store = AuthConfigStore(tmp_path / "auth.json")
    extractor = FakeExtractor()
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text='"/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf"',
    )
    httpx_mock.add_response(
        method="POST",
        url="https://scholar.google.com/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf",
        content=b"ok",
    )

    service = LoginService(store=store, extractor=extractor, hl="en")

    config = await service.login()

    post_request = httpx_mock.get_requests()[1]
    assert post_request.headers["User-Agent"].startswith("Mozilla/5.0")
    assert post_request.headers["Referer"] == "https://scholar.google.com/scholar_labs/search"
    assert post_request.headers["Origin"] == "https://scholar.google.com"
    assert post_request.headers["Accept-Language"] == "en-US,en;q=0.9"
    assert config == ChromeProfileAuthConfig(
        browser="chrome",
        profile="Default",
        profile_path="/tmp/Chrome/Default",
        validated_at=config.validated_at,
    )
    written = json.loads((tmp_path / "auth.json").read_text())
    assert written["method"] == "chrome-profile"
    assert "cookie" not in written
    assert "xsrf_token" not in written


@pytest.mark.asyncio
async def test_login_service_reports_validation_failure(tmp_path, httpx_mock):
    store = AuthConfigStore(tmp_path / "auth.json")
    extractor = FakeExtractor()
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text='"/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf"',
    )
    httpx_mock.add_response(
        method="POST",
        url="https://scholar.google.com/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf",
        status_code=403,
    )

    service = LoginService(store=store, extractor=extractor, hl="en")

    with pytest.raises(LoginError, match="validation returned HTTP 403"):
        await service.login()

    assert not (tmp_path / "auth.json").exists()


class FakeExtractor:
    profile = BrowserProfile(
        browser="chrome",
        profile="Default",
        profile_path="/tmp/Chrome/Default",
    )

    def extract(self):
        return BrowserCookieMaterial(cookie_header="SID=sid-value")


class FakeBrowserPageDiscovery:
    def __init__(self, token):
        self._token = token

    def discover(self, hl="en"):
        return self._token
