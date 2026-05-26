"""Read Scholar Labs page state from a user-owned browser page."""

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BrowserPageXsrfDiscovery:
    """Discover XSRF from an already usable Scholar Labs browser page."""

    COMMAND_URL = "http://127.0.0.1:10086/command"
    STATUS_URL = "http://127.0.0.1:10086/status"
    SESSION = "sls-login"

    def __init__(self, timeout: float = 1.5):
        self._timeout = timeout

    def discover(self, hl: str = "en") -> str | None:
        if not self._is_available():
            return None

        self._ensure_scholar_page(hl)
        return self._read_page_xsrf()

    def _is_available(self) -> bool:
        try:
            with urlopen(self.STATUS_URL, timeout=self._timeout) as response:
                status = json.loads(response.read().decode())
        except (OSError, URLError, json.JSONDecodeError):
            return False
        return bool(status.get("running") and status.get("extension_connected"))

    def _ensure_scholar_page(self, hl: str) -> None:
        found = self._command(
            "find_tab",
            {"url": "https://scholar.google.com", "active": False},
        )
        if found.get("ok"):
            return

        self._command(
            "navigate",
            {
                "url": f"https://scholar.google.com/scholar_labs/search?{urlencode({'hl': hl})}",
                "newTab": True,
                "group_title": "Scholar Labs",
            },
        )

    def _read_page_xsrf(self) -> str | None:
        response = self._command(
            "evaluate",
            {
                "code": (
                    "(() => {"
                    "const dsp=document.querySelector('#gs_as_glb[data-dsp]')?.getAttribute('data-dsp')||'';"
                    "return new URLSearchParams(dsp).get('xsrf')||'';"
                    "})()"
                )
            },
        )
        value = response.get("data", {}).get("value")
        return value if isinstance(value, str) and value else None

    def _command(self, action: str, args: dict) -> dict:
        body = json.dumps(
            {"action": action, "args": args, "session": self.SESSION}
        ).encode()
        request = Request(
            self.COMMAND_URL,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode())
        except (OSError, URLError, json.JSONDecodeError):
            return {}
