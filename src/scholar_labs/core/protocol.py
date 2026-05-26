"""Binary streaming protocol parser for Google Scholar Labs API.

The protocol uses a simple framing format:
    4 bytes: big-endian uint32 chunk length
    N bytes: JSON payload

Multiple chunks are concatenated in the response body.
"""

import json
import struct
from typing import TypedDict


class SearchResult(TypedDict, total=False):
    title: str
    authors: str
    abstract: str
    citation_count: int
    url: str
    paper_id: str
    raw_html: str


class SearchChunk(TypedDict, total=False):
    state: int
    status: str
    results: list[SearchResult]
    suggested_questions: list[str]


def parse_stream(data: bytes) -> list[SearchChunk]:
    chunks: list[SearchChunk] = []
    offset = 0

    while offset + 4 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4

        if offset + length > len(data):
            break

        raw = data[offset : offset + length]
        offset += length

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue

        chunks.append(_parse_chunk(obj))

    return chunks


def _parse_chunk(obj: dict) -> SearchChunk:
    chunk: SearchChunk = {"state": obj.get("s", 0)}

    thread_items = obj.get("t", [])
    statuses = []
    all_results: list[SearchResult] = []
    all_questions: list[str] = []

    for item in thread_items:
        if item.get("s"):
            statuses.append(item["s"])
        if item.get("sq"):
            all_questions.extend(_extract_questions(item["sq"]))
        for result_item in item.get("f", []):
            if result_item.get("h"):
                result = _parse_result_html(result_item["h"])
                all_results.append(result)

    if statuses:
        chunk["status"] = statuses[-1]
    if all_questions:
        chunk["suggested_questions"] = all_questions
    if all_results:
        chunk["results"] = all_results

    return chunk


def _extract_questions(sq_html: str) -> list[str]:
    """Extract suggested questions from the sq HTML field."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(sq_html, "html.parser")
    questions = []
    for li in soup.select("li"):
        text = li.get_text(strip=True)
        if text:
            questions.append(text)
    return questions


def _parse_result_html(html: str) -> SearchResult:
    """Parse a single result HTML snippet. Delegates to the full parser."""
    from scholar_labs.core.parser import parse_result_html

    return parse_result_html(html)
