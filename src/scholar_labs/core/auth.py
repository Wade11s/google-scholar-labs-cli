from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlencode

import httpx


class ScholarLabsError(Exception):
    """Base exception for all scholar-labs-cli errors."""


class AuthError(ScholarLabsError):
    """Raised when authentication credentials are missing or invalid."""


class AuthConfigError(AuthError):
    """Raised when local authentication config cannot be used."""


class LegacyAuthConfigError(AuthConfigError):
    """Raised when an old unversioned auth config is found."""


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


@dataclass(frozen=True)
class ManualAuthConfig:
    cookie: str
    xsrf_token: str
    validated_at: str | None = None
    version: int = 1
    method: Literal["manual"] = "manual"


@dataclass(frozen=True)
class ChromeProfileAuthConfig:
    browser: str
    profile: str
    profile_path: str
    validated_at: str | None = None
    version: int = 1
    method: Literal["chrome-profile"] = "chrome-profile"


AuthConfig = ManualAuthConfig | ChromeProfileAuthConfig


class AuthConfigStore:
    CONFIG_DIR = ".scholar-labs-cli"
    CONFIG_FILE = "auth.json"

    def __init__(self, path: Path | None = None):
        self.path = path or Path.home() / self.CONFIG_DIR / self.CONFIG_FILE

    def read(self) -> AuthConfig | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            raise AuthConfigError("Auth config is not valid JSON.") from e

        if "version" not in data and {"cookie", "xsrf_token"}.issubset(data):
            raise LegacyAuthConfigError(
                "Legacy auth config is no longer supported. "
                "Run 'sls login' or 'sls auth manual' to create a new Auth Config."
            )

        if data.get("version") != 1:
            raise AuthConfigError("Unsupported auth config version.")

        method = data.get("method")
        if method == "manual":
            return self._read_manual(data)
        if method == "chrome-profile":
            return self._read_chrome_profile(data)
        raise AuthConfigError("Unsupported auth config method.")

    def write(self, config: AuthConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(config), indent=2))

    def delete(self) -> bool:
        if not self.path.exists():
            return False
        self.path.unlink()
        return True

    def _read_manual(self, data: dict) -> ManualAuthConfig:
        try:
            return ManualAuthConfig(
                cookie=data["cookie"],
                xsrf_token=data["xsrf_token"],
                validated_at=data.get("validated_at"),
            )
        except KeyError as e:
            raise AuthConfigError("Manual auth config is missing required fields.") from e

    def _read_chrome_profile(self, data: dict) -> ChromeProfileAuthConfig:
        try:
            return ChromeProfileAuthConfig(
                browser=data["browser"],
                profile=data["profile"],
                profile_path=data["profile_path"],
                validated_at=data.get("validated_at"),
            )
        except KeyError as e:
            raise AuthConfigError("Chrome profile auth config is missing required fields.") from e


class AuthProvider(ABC):
    @abstractmethod
    def get_credentials(self) -> AuthTokens: ...


class ManualAuthProvider(AuthProvider):
    def __init__(
        self,
        cookie: str | None = None,
        xsrf_token: str | None = None,
        config_store: AuthConfigStore | None = None,
        config_store_path: Path | None = None,
        browser_extractor_factory=None,
        xsrf_discoverer=None,
    ):
        self._cookie = cookie
        self._xsrf_token = xsrf_token
        self._config_store = config_store or AuthConfigStore(config_store_path)
        self._browser_extractor_factory = browser_extractor_factory or _create_extractor_from_config
        self._xsrf_discoverer = xsrf_discoverer or _discover_xsrf_sync

    def get_credentials(self) -> AuthTokens:
        cookie = self._cookie or os.environ.get("SCHOLAR_COOKIE")
        xsrf = self._xsrf_token or os.environ.get("SCHOLAR_XSRF_TOKEN")

        if not cookie or not xsrf:
            config = self._config_store.read()
            if isinstance(config, ManualAuthConfig):
                cookie, xsrf = config.cookie, config.xsrf_token
            elif isinstance(config, ChromeProfileAuthConfig):
                material = self._browser_extractor_factory(config).extract()
                cookie = material.cookie_header
                xsrf = self._xsrf_discoverer(cookie)

        if not cookie or not xsrf:
            raise AuthError(
                "No authentication credentials found. "
                "Set SCHOLAR_COOKIE and SCHOLAR_XSRF_TOKEN environment variables, "
                "or run 'sls login' to configure authentication."
            )

        return AuthTokens(cookie=cookie, xsrf_token=xsrf)


def _create_extractor_from_config(config: ChromeProfileAuthConfig):
    from scholar_labs.core.browser_auth import create_browser_credential_extractor

    return create_browser_credential_extractor(
        browser=config.browser,
        profile=config.profile,
        profile_path=config.profile_path,
    )


def _discover_xsrf_sync(cookie_header: str) -> str:
    hl = os.environ.get("SCHOLAR_HL", "en")
    url = "https://scholar.google.com/scholar_labs/search?" + urlencode({"hl": hl})
    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        response = client.get(url, headers={"Cookie": cookie_header})
    if response.status_code >= 400:
        raise AuthError(f"Scholar Labs page returned HTTP {response.status_code}.")
    match = re.search(r"[?&]xsrf=([^\"'&<>\s]+)", response.text)
    if not match:
        raise AuthError("Could not discover XSRF token from Scholar Labs page.")
    return match.group(1)
