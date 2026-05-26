"""CLI Login orchestration."""

from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx

from scholar_labs.core.auth import AuthConfigStore, ChromeProfileAuthConfig
from scholar_labs.core.browser_page import BrowserPageXsrfDiscovery
from scholar_labs.core.browser_auth import BrowserCredentialExtractor
from scholar_labs.core.xsrf import extract_xsrf_token


class LoginError(Exception):
    """Raised when CLI Login cannot validate Scholar Labs access."""


class LoginRateLimitError(LoginError):
    """Raised when Scholar Labs rate-limits login validation."""


class XsrfDiscovery:
    SEARCH_URL = "https://scholar.google.com/scholar_labs/search"

    def __init__(self, browser_page_discovery: BrowserPageXsrfDiscovery | None = None):
        self._browser_page_discovery = browser_page_discovery or BrowserPageXsrfDiscovery()

    async def discover(self, cookie_header: str, hl: str = "en") -> str:
        params = urlencode({"hl": hl})
        url = f"{self.SEARCH_URL}?{params}"
        headers = _browser_headers(cookie_header)
        async with httpx.AsyncClient(http2=True, timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(url, headers=headers)
        if response.status_code == 429:
            token = self._browser_page_discovery.discover(hl=hl)
            if token:
                return token
            raise LoginRateLimitError(_rate_limit_message(response))
        if response.status_code == 403:
            token = self._browser_page_discovery.discover(hl=hl)
            if token:
                return token
        if response.status_code >= 400:
            raise LoginError(f"Scholar Labs page returned HTTP {response.status_code}.")
        token = extract_xsrf_token(response.text)
        if not token:
            token = self._browser_page_discovery.discover(hl=hl)
        if not token:
            raise LoginError("Could not discover XSRF token from Scholar Labs page.")
        return token


class LoginService:
    SESSION_URL = "https://scholar.google.com/scholar_labs/search/session_data"

    def __init__(
        self,
        store: AuthConfigStore,
        extractor: BrowserCredentialExtractor,
        discovery: XsrfDiscovery | None = None,
        hl: str = "en",
    ):
        self._store = store
        self._extractor = extractor
        self._discovery = discovery or XsrfDiscovery()
        self._hl = hl

    async def login(self) -> ChromeProfileAuthConfig:
        material = self._extractor.extract()
        xsrf_token = await self._discovery.discover(material.cookie_header, hl=self._hl)
        await self._validate(material.cookie_header, xsrf_token)
        profile = self._extractor.profile
        config = ChromeProfileAuthConfig(
            browser=profile.browser,
            profile=profile.profile,
            profile_path=profile.profile_path or "",
            validated_at=datetime.now(UTC).isoformat(),
        )
        self._store.write(config)
        return config

    async def _validate(self, cookie_header: str, xsrf_token: str) -> None:
        params = urlencode({"hl": self._hl, "xsrf": xsrf_token})
        url = f"{self.SESSION_URL}?{params}"
        headers = {
            **_browser_headers(cookie_header),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Origin": "https://scholar.google.com",
        }
        async with httpx.AsyncClient(http2=True, timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(url, content=urlencode({"q": "test"}), headers=headers)
        if response.status_code == 429:
            raise LoginRateLimitError(_rate_limit_message(response))
        if response.status_code >= 400:
            raise LoginError(f"Scholar Labs validation returned HTTP {response.status_code}.")


def _rate_limit_message(response: httpx.Response) -> str:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        return f"Scholar Labs rate limited login; retry after {retry_after} seconds."
    return "Scholar Labs rate limited login. Wait before retrying."


def _browser_headers(cookie_header: str) -> dict[str, str]:
    return {
        "Cookie": cookie_header,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://scholar.google.com/scholar_labs/search",
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
