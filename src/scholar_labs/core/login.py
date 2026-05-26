"""CLI Login orchestration."""

from datetime import UTC, datetime
import re
from urllib.parse import urlencode

import httpx

from scholar_labs.core.auth import AuthConfigStore, ChromeProfileAuthConfig
from scholar_labs.core.browser_auth import BrowserCredentialExtractor


class LoginError(Exception):
    """Raised when CLI Login cannot validate Scholar Labs access."""


class XsrfDiscovery:
    SEARCH_URL = "https://scholar.google.com/scholar_labs/search"

    async def discover(self, cookie_header: str, hl: str = "en") -> str:
        params = urlencode({"hl": hl})
        url = f"{self.SEARCH_URL}?{params}"
        headers = {"Cookie": cookie_header}
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(url, headers=headers)
        if response.status_code >= 400:
            raise LoginError(f"Scholar Labs page returned HTTP {response.status_code}.")
        match = re.search(r"[?&]xsrf=([^\"'&<>\s]+)", response.text)
        if not match:
            raise LoginError("Could not discover XSRF token from Scholar Labs page.")
        return match.group(1)


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
            "Cookie": cookie_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(url, content=urlencode({"q": "test"}), headers=headers)
        if response.status_code >= 400:
            raise LoginError(f"Scholar Labs validation returned HTTP {response.status_code}.")
