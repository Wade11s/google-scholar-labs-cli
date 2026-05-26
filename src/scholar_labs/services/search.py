"""Search service — orchestrates the search pipeline."""

from dataclasses import dataclass, field

from scholar_labs.core.auth import AuthProvider
from scholar_labs.core.client import ScholarLabsClient
from scholar_labs.core.protocol import parse_stream, SearchResult


@dataclass
class SearchResponse:
    results: list[SearchResult] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    status: str = ""


class SearchService:
    def __init__(self, auth_provider: AuthProvider, hl: str = "en"):
        self._client = ScholarLabsClient(auth_provider, hl=hl)

    async def search(self, query: str) -> SearchResponse:
        """Execute a search and return aggregated results."""
        raw = await self._client.search(query)
        chunks = parse_stream(raw)

        all_results: list[SearchResult] = []
        suggested_questions: list[str] = []

        for chunk in chunks:
            if chunk.get("results"):
                all_results.extend(chunk["results"])
            if chunk.get("suggested_questions"):
                suggested_questions.extend(chunk["suggested_questions"])

        return SearchResponse(
            results=all_results,
            suggested_questions=suggested_questions,
            status=chunks[-1].get("status", "") if chunks else "",
        )
