from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path


class ScholarLabsError(Exception):
    """Base exception for all scholar-labs-cli errors."""


class AuthError(ScholarLabsError):
    """Raised when authentication credentials are missing or invalid."""


class ProtocolError(ScholarLabsError):
    """Raised when the binary protocol response cannot be parsed."""


class ParseError(ScholarLabsError):
    """Raised when HTML result parsing fails."""


class NetworkError(ScholarLabsError):
    """Raised when an HTTP request fails."""


class RateLimitError(ScholarLabsError):
    """Raised when Google returns HTTP 429 — too many requests."""


@dataclass(frozen=True)
class AuthTokens:
    cookie: str
    xsrf_token: str


class AuthProvider(ABC):
    @abstractmethod
    def get_credentials(self) -> AuthTokens: ...


class ManualAuthProvider(AuthProvider):
    CONFIG_DIR = ".scholar-labs-cli"
    CONFIG_FILE = "auth.json"

    def __init__(self, cookie: str | None = None, xsrf_token: str | None = None):
        self._cookie = cookie
        self._xsrf_token = xsrf_token

    def get_credentials(self) -> AuthTokens:
        cookie = self._cookie or os.environ.get("SCHOLAR_COOKIE")
        xsrf = self._xsrf_token or os.environ.get("SCHOLAR_XSRF_TOKEN")

        if not cookie or not xsrf:
            cookie, xsrf = self._read_from_config_file()

        if not cookie or not xsrf:
            raise AuthError(
                "No authentication credentials found. "
                "Set SCHOLAR_COOKIE and SCHOLAR_XSRF_TOKEN environment variables, "
                "or run 'sls login' to configure authentication."
            )

        return AuthTokens(cookie=cookie, xsrf_token=xsrf)

    def _read_from_config_file(self) -> tuple[str | None, str | None]:
        config_path = Path.home() / self.CONFIG_DIR / self.CONFIG_FILE
        if not config_path.exists():
            return None, None
        try:
            data = json.loads(config_path.read_text())
            return data.get("cookie"), data.get("xsrf_token")
        except (json.JSONDecodeError, OSError):
            return None, None
