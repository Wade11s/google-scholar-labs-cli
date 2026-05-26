"""XSRF token discovery helpers."""

from html import unescape
import re
from urllib.parse import unquote


_QUERY_XSRF_PATTERN = re.compile(r"[?&]xsrf=([^\"'&<>\s\\]+)")
_NAMED_XSRF_PATTERNS = (
    re.compile(r"""["']xsrf["']\s*[:=]\s*["']([^"'<>\\\s]+)["']"""),
    re.compile(r"""data-xsrf=["']([^"'<>\\\s]+)["']"""),
)
_JS_ESCAPE_PATTERN = re.compile(r"\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})")


def extract_xsrf_token(page_text: str) -> str | None:
    """Extract a Scholar Labs XSRF token from raw or escaped page text."""
    for candidate in _normalized_candidates(page_text):
        query_match = _QUERY_XSRF_PATTERN.search(candidate)
        if query_match:
            return unquote(query_match.group(1))

        for pattern in _NAMED_XSRF_PATTERNS:
            named_match = pattern.search(candidate)
            if named_match:
                return unquote(named_match.group(1))

    return None


def _normalized_candidates(page_text: str) -> list[str]:
    candidates = [page_text]
    cursor = page_text
    for normalizer in (unescape, unquote, _decode_javascript_escapes):
        cursor = normalizer(cursor)
        candidates.append(cursor)
    return candidates


def _decode_javascript_escapes(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        hex_value = match.group(1) or match.group(2)
        return chr(int(hex_value, 16))

    return _JS_ESCAPE_PATTERN.sub(replace, value)
