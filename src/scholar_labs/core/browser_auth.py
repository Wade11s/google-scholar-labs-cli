"""Browser credential extraction boundary."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable


class BrowserAuthError(Exception):
    """Raised when Browser Credential Extraction fails."""


class UnsupportedBrowserEnvironment(BrowserAuthError):
    """Raised when automatic browser auth is unavailable."""


@dataclass(frozen=True)
class BrowserProfile:
    browser: str
    profile: str = "Default"
    profile_path: str | None = None


@dataclass(frozen=True)
class BrowserCookieMaterial:
    cookie_header: str


class BrowserCredentialExtractor(ABC):
    def __init__(self, profile: BrowserProfile):
        self.profile = profile

    @abstractmethod
    def extract(self) -> BrowserCookieMaterial: ...


class MacOSChromeCredentialExtractor(BrowserCredentialExtractor):
    def __init__(
        self,
        profile: BrowserProfile,
        cookie_loader: Callable[[Path, str], object] | None = None,
    ):
        super().__init__(profile)
        self._cookie_loader = cookie_loader or _load_chrome_cookies

    def extract(self) -> BrowserCookieMaterial:
        profile_path = self._profile_path()
        if not profile_path.exists():
            raise BrowserAuthError(f"Chrome profile not found: {profile_path}")
        cookie_db = self._cookie_db_path()
        if not cookie_db.exists():
            raise BrowserAuthError(f"Chrome cookie database not found: {cookie_db}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            copied_db = Path(tmp_dir) / "Cookies"
            shutil.copy2(cookie_db, copied_db)
            try:
                jar = self._cookie_loader(copied_db, ".google.com")
            except BrowserAuthError:
                raise
            except Exception as e:
                if "decrypt" in str(e).lower():
                    raise BrowserAuthError(f"Chrome cookie decryption failed: {e}") from e
                raise BrowserAuthError(f"Failed to read Chrome cookies: {e}") from e
            cookie_header = _build_cookie_header(jar)

        if not cookie_header:
            raise BrowserAuthError("No Google cookies found in the Chrome profile.")
        return BrowserCookieMaterial(cookie_header=cookie_header)

    def _cookie_db_path(self) -> Path:
        cookie_db = _find_cookie_db(self._profile_path())
        if cookie_db is not None:
            return cookie_db
        return self._profile_path() / "Network" / "Cookies"

    def _profile_path(self) -> Path:
        if self.profile.profile_path:
            return Path(self.profile.profile_path)
        return _default_chrome_root(self.profile.browser) / self.profile.profile


def create_browser_credential_extractor(
    browser: str = "chrome",
    profile: str = "auto",
    profile_path: str | None = None,
    platform: str | None = None,
    chrome_root: Path | None = None,
) -> BrowserCredentialExtractor:
    platform = platform or sys.platform
    normalized_browser = browser.lower()
    if platform != "darwin":
        raise UnsupportedBrowserEnvironment(
            "Browser Credential Extraction currently supports macOS Chrome/Chromium only. "
            "Use 'sls auth manual' for this environment."
        )
    if normalized_browser not in {"chrome", "chromium"}:
        raise UnsupportedBrowserEnvironment(
            "Browser Credential Extraction currently supports macOS Chrome/Chromium only. "
            "Use 'sls auth manual' for this browser."
        )
    resolved_profile = BrowserProfile(
        browser=normalized_browser,
        profile=profile,
        profile_path=profile_path,
    )
    if profile_path is None and profile == "auto":
        resolved_profile = _detect_macos_chrome_profile(normalized_browser, chrome_root)
    return MacOSChromeCredentialExtractor(
        resolved_profile
    )


def _load_chrome_cookies(cookie_file: Path, domain_name: str):
    try:
        import browser_cookie3
    except ImportError as e:
        raise BrowserAuthError(
            "Browser Auth Extension is not installed. Install scholar-labs-cli[browser] "
            "or use 'sls auth manual'."
        ) from e
    return browser_cookie3.chrome(cookie_file=str(cookie_file), domain_name=domain_name)


def _build_cookie_header(cookie_jar) -> str:
    parts = []
    for cookie in cookie_jar:
        domain = getattr(cookie, "domain", "")
        if "google.com" not in domain:
            continue
        parts.append(f"{cookie.name}={cookie.value}")
    return "; ".join(parts)


def _detect_macos_chrome_profile(browser: str, chrome_root: Path | None = None) -> BrowserProfile:
    root = chrome_root or _default_chrome_root(browser)
    candidates = []
    for name in ("Default", "Profile 1"):
        candidate = root / name
        if candidate.exists():
            candidates.append(candidate)
    if root.exists():
        candidates.extend(
            sorted(
                path for path in root.iterdir()
                if path.is_dir() and path.name.startswith("Profile ")
            )
        )

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _find_cookie_db(candidate) is not None:
            return BrowserProfile(
                browser=browser,
                profile=candidate.name,
                profile_path=str(candidate),
            )

    raise BrowserAuthError(
        f"No Chrome profile with a cookie database found under {root}. "
        "Use --profile to select a profile or 'sls auth manual'."
    )


def _default_chrome_root(browser: str) -> Path:
    if browser == "chromium":
        return Path.home() / "Library" / "Application Support" / "Chromium"
    return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def _find_cookie_db(profile_path: Path) -> Path | None:
    for relative_path in (
        Path("Network") / "Cookies",
        Path("Cookies"),
        Path("Default") / "Cookies",
    ):
        candidate = profile_path / relative_path
        if candidate.exists():
            return candidate
    return None
