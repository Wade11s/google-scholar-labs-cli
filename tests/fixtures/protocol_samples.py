import json
import struct


def make_chunk(data: dict) -> bytes:
    """Encode a dict as a length-prefixed binary chunk matching the Scholar Labs protocol."""
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return struct.pack(">I", len(raw)) + raw


# Simulated search response matching the reverse-engineered protocol:
# Chunk 0: state=2 "analyzing"
# Chunk 1: state=3 with suggested questions
# Chunk 2: empty heartbeat
# Chunk 3: state=3 "evaluated N results"
# Chunk 4: state=3 with actual result HTML
# Chunk 5: state=1 ack

SAMPLE_RESPONSE = b"".join([
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 2,
        "t": [{"a": True, "e": False, "f": [], "i": 0, "q": "test query", "qr": False, "s": "正在分析您的问题"}],
        "tl": False, "y": 1,
    }),
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 3,
        "t": [{"a": True, "e": False, "f": [], "i": 0, "q": "test query", "qr": False,
               "s": "正在执行 5 项查询",
               "sq": "<h3>Suggested questions:</h3><ul><li>Q1: Is this real?</li></ul>"}],
        "tl": False, "y": 1,
    }),
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 3,
        "t": [],
        "tl": False, "y": 1,
    }),
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 3,
        "t": [{"a": True, "e": False, "f": [], "i": 0, "qr": False, "s": "已评估 42 条排名靠前的搜索结果"}],
        "tl": False, "y": 1,
    }),
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 3,
        "t": [{"a": True, "e": False, "f": [
            {"h": '<div class="gs_r" data-cid="test-cid-1" data-aid="test-aid-1"><h3 class="gs_rt"><a href="https://example.com/paper1">A Test Paper About LLMs</a></h3><div class="gs_a">J Smith, K Lee - Journal of Testing, 2025</div><div class="gs_rs">This paper tests important things about large language models.</div><div class="gs_fl"><a href="#">Save</a> <a href="#">Cite</a> <a href="#">Cited by 42</a></div></div>', "i": 0},
            {"h": '<div class="gs_r" data-cid="test-cid-2" data-aid="test-aid-2"><h3 class="gs_rt"><a href="https://example.com/paper2">Another Great Paper</a></h3><div class="gs_a">A Author - Conference on AI, 2024</div><div class="gs_rs">A second excellent contribution to the field.</div><div class="gs_fl"><a href="#">Save</a> <a href="#">Cite</a> <a href="#">Cited by 10</a></div></div>', "i": 1},
        ], "i": 0, "qr": False, "s": "找到 2 条相关结果"}],
        "tl": False, "y": 1,
    }),
    make_chunk({
        "i": "test-session-123",
        "m": True, "n": 1, "s": 1,
        "t": [],
        "tl": False, "y": 1,
    }),
])

# Malformed chunks for resilience testing
CHUNK_WITH_TRUNCATED_JSON = struct.pack(">I", 50) + b'{"incomplete": true'
CHUNK_WITH_zero_LENGTH = struct.pack(">I", 0)
CHUNK_WITH_HUGE_LENGTH = struct.pack(">I", 999999999)
