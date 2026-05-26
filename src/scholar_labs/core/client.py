"""HTTP client for Google Scholar Labs API."""

import asyncio
from urllib.parse import urlencode

import httpx

from scholar_labs.core.auth import AuthProvider, AuthError, NetworkError, RateLimitError


class ScholarLabsClient:
    REFERER = "https://scholar.google.com/scholar_labs/search"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    )

    BASE_URL = "https://scholar.google.com/scholar_labs/search/session_data"
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self, auth_provider: AuthProvider, hl: str = "en"):
        self._auth = auth_provider
        self._hl = hl

    async def search(self, query: str) -> bytes:
        """Execute a search and return the raw binary response body."""
        url = self._build_url()
        headers = self._build_headers()
        body = self._build_body(query)

        async with httpx.AsyncClient(http2=True, timeout=httpx.Timeout(60.0)) as client:
            for attempt in range(self.MAX_RETRIES):
                response = await client.post(url, content=body, headers=headers)
                if response.status_code == 429 and attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> bytes:
        if response.status_code == 403:
            raise AuthError(
                "Authentication failed. Your cookie or XSRF token may have expired. "
                "Re-run the credential steps in the README to get fresh tokens."
            )
        if response.status_code == 429:
            raise RateLimitError(
                "Rate limited by Google Scholar. Wait a minute and try again. "
                f"(Retried {self.MAX_RETRIES} times)"
            )
        if response.status_code >= 400:
            raise NetworkError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
        return response.content

    def _build_url(self, session_id: str | None = None) -> str:
        creds = self._auth.get_credentials()
        url = self.BASE_URL
        if session_id:
            url = f"{url}/{session_id}"
        params = {"hl": self._hl, "xsrf": creds.xsrf_token}
        return f"{url}?{urlencode(params)}"

    def _build_body(self, query: str) -> str:
        return urlencode({"q": query})

    def _build_headers(self) -> dict[str, str]:
        creds = self._auth.get_credentials()
        return {
            "Cookie": creds.cookie,
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self.USER_AGENT,
            "Referer": self.REFERER,
            "Origin": "https://scholar.google.com",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
