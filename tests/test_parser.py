"""HTML result parser tests."""

from scholar_labs.core.parser import parse_result_html, SearchResult

SAMPLE_HTML = """
<div class="gs_r" data-cid="test-cid" data-aid="test-aid">
  <h3 class="gs_rt">
    <a href="https://example.com/paper">A Novel Approach to LLM Safety</a>
  </h3>
  <div class="gs_a">
    <a href="/citations?user=abc">J Smith</a>,
    <a href="/citations?user=def">K Lee</a>
    - Journal of AI Research, 2025 - example.com
  </div>
  <div class="gs_rs">
    This paper presents a groundbreaking approach to ensuring large language models
    behave safely and ethically in production environments.
  </div>
  <div class="gs_fl">
    <a href="#">Save</a>
    <a href="#">Cite</a>
    <a href="/scholar?cites=123">Cited by 42</a>
  </div>
</div>
"""

NO_AUTHORS_HTML = """
<div class="gs_r" data-cid="minimal-id" data-aid="minimal-aid">
  <h3 class="gs_rt"><a href="https://example.com/minimal">Minimal Paper</a></h3>
  <div class="gs_rs">Just a short abstract.</div>
</div>
"""

BROKEN_HTML = "<div>This is not a proper result</div>"


def test_parse_result_extracts_title():
    result = parse_result_html(SAMPLE_HTML)
    assert result["title"] == "A Novel Approach to LLM Safety"


def test_parse_result_extracts_authors():
    result = parse_result_html(SAMPLE_HTML)
    assert "J Smith" in result["authors"]
    assert "K Lee" in result["authors"]


def test_parse_result_extracts_citation_count():
    result = parse_result_html(SAMPLE_HTML)
    assert result["citation_count"] == 42


def test_parse_result_extracts_url():
    result = parse_result_html(SAMPLE_HTML)
    assert result["url"] == "https://example.com/paper"


def test_parse_result_extracts_paper_id():
    result = parse_result_html(SAMPLE_HTML)
    assert result["paper_id"] == "test-aid"


def test_parse_result_extracts_abstract():
    result = parse_result_html(SAMPLE_HTML)
    assert "groundbreaking" in result["abstract"]


def test_parse_result_extracts_venue_and_year():
    result = parse_result_html(SAMPLE_HTML)
    assert "Journal of AI Research" in result["authors"]
    assert "2025" in result["authors"]


def test_parse_result_graceful_degradation_on_minimal_html():
    result = parse_result_html(NO_AUTHORS_HTML)
    assert result["title"] == "Minimal Paper"
    assert result["paper_id"] == "minimal-aid"
    assert "authors" in result["parse_warning"]


def test_parse_result_returns_partial_on_broken_html():
    result = parse_result_html(BROKEN_HTML)
    assert result["parse_warning"] != ""
    assert result["raw_html"] == BROKEN_HTML
