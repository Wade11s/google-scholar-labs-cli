"""HTML result parser for Google Scholar Labs search results.

Extracts structured paper metadata from server-rendered HTML snippets.
Uses CSS selectors with graceful degradation: if a field can't be parsed,
returns whatever was found plus a parse_warning.
"""

import re
from typing import TypedDict

from bs4 import BeautifulSoup

from scholar_labs.core import selectors


class SearchResult(TypedDict, total=False):
    title: str
    authors: str
    abstract: str
    citation_count: int
    url: str
    paper_id: str
    raw_html: str
    parse_warning: str


def parse_result_html(html: str) -> SearchResult:
    """Parse a single search result HTML snippet into a structured SearchResult.

    Graceful degradation: if parsing fails for any field, a partial result
    is returned with a parse_warning describing what went wrong.
    """
    soup = BeautifulSoup(html, "html.parser")
    warnings: list[str] = []

    paper_id = _extract_paper_id(soup, warnings)
    title = _extract_title(soup, warnings)
    url = _extract_url(soup, warnings)
    authors = _extract_authors(soup, warnings)
    abstract = _extract_abstract(soup, warnings)
    citation_count = _extract_citation_count(soup, warnings)

    warning_str = "; ".join(warnings) if warnings else ""

    return SearchResult(
        title=title,
        authors=authors,
        abstract=abstract,
        citation_count=citation_count,
        url=url,
        paper_id=paper_id,
        raw_html=html,
        parse_warning=warning_str,
    )


def _extract_paper_id(soup: BeautifulSoup, warnings: list[str]) -> str:
    root = soup.select_one(selectors.ROOT)
    if root:
        return root.get("data-aid", "")
    warnings.append("paper_id not found")
    return ""


def _extract_title(soup: BeautifulSoup, warnings: list[str]) -> str:
    el = soup.select_one(selectors.TITLE)
    if el:
        return el.get_text(strip=True)
    # Fallback: try any h3 link
    el = soup.select_one("h3 a, a")
    if el:
        return el.get_text(strip=True)
    warnings.append("title not found")
    return ""


def _extract_url(soup: BeautifulSoup, warnings: list[str]) -> str:
    el = soup.select_one(selectors.TITLE)
    if el and el.get("href"):
        href: str = el["href"]
        return href.strip()
    warnings.append("url not found")
    return ""


def _extract_authors(soup: BeautifulSoup, warnings: list[str]) -> str:
    el = soup.select_one(selectors.AUTHORS)
    if el:
        return el.get_text(" ", strip=True)
    warnings.append("authors not found")
    return ""


def _extract_abstract(soup: BeautifulSoup, warnings: list[str]) -> str:
    el = soup.select_one(selectors.ABSTRACT)
    if el:
        return el.get_text(" ", strip=True)
    warnings.append("abstract not found")
    return ""


def _extract_citation_count(soup: BeautifulSoup, warnings: list[str]) -> int:
    el = soup.select_one(selectors.CITATION_LINK)
    if el:
        text = el.get_text(strip=True)
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
    return 0
