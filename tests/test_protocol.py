"""Protocol parser tests using synthetic and real binary data."""

from scholar_labs.core.protocol import parse_stream, SearchChunk
from tests.fixtures.protocol_samples import SAMPLE_RESPONSE


def test_parse_stream_returns_correct_chunk_count():
    """A complete search response yields the expected number of chunks."""
    chunks = parse_stream(SAMPLE_RESPONSE)

    assert len(chunks) == 6


def test_parse_stream_extracts_state_values():
    """Each chunk has the correct state code."""
    chunks = parse_stream(SAMPLE_RESPONSE)

    states = [c["state"] for c in chunks]
    assert states == [2, 3, 3, 3, 3, 1]


def test_parse_stream_extracts_status_messages():
    """Status messages are extracted from chunks."""
    chunks = parse_stream(SAMPLE_RESPONSE)

    statuses = [c.get("status") for c in chunks if c.get("status")]
    assert "正在分析您的问题" in statuses
    assert "已评估 42 条排名靠前的搜索结果" in statuses


def test_parse_stream_extracts_suggested_questions():
    """Suggested follow-up questions are extracted from the sq field."""
    chunks = parse_stream(SAMPLE_RESPONSE)

    questions = [c.get("suggested_questions") for c in chunks if c.get("suggested_questions")]
    assert len(questions) == 1
    assert "Q1: Is this real?" in questions[0][0]


def test_parse_stream_extracts_result_html():
    """Search result HTML snippets are extracted from f[].h fields."""
    chunks = parse_stream(SAMPLE_RESPONSE)

    results = [c.get("results") for c in chunks if c.get("results")]
    assert len(results) == 1
    assert len(results[0]) == 2
    assert "test-cid-1" in results[0][0]["raw_html"]
    assert "test-cid-2" in results[0][1]["raw_html"]
    assert results[0][0]["paper_id"] == "test-aid-1"
    assert results[0][1]["paper_id"] == "test-aid-2"


def test_parse_stream_handles_empty_input():
    """Empty bytes input returns an empty list."""
    chunks = parse_stream(b"")
    assert chunks == []


def test_parse_stream_skips_malformed_json():
    """Truncated JSON chunks are skipped, not crashing."""
    from tests.fixtures.protocol_samples import CHUNK_WITH_TRUNCATED_JSON

    chunks = parse_stream(CHUNK_WITH_TRUNCATED_JSON)
    assert len(chunks) == 0


def test_parse_stream_skips_zero_length_chunk():
    """Zero-length chunks are ignored."""
    from tests.fixtures.protocol_samples import CHUNK_WITH_zero_LENGTH

    chunks = parse_stream(CHUNK_WITH_zero_LENGTH)
    assert len(chunks) == 0  # empty JSON object would be skipped


def test_parse_stream_handles_huge_length():
    """Chunks with impossibly large length don't crash."""
    from tests.fixtures.protocol_samples import CHUNK_WITH_HUGE_LENGTH

    chunks = parse_stream(CHUNK_WITH_HUGE_LENGTH)
    assert len(chunks) == 0  # length exceeds remaining data, skipped
