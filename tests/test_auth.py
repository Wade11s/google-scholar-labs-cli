import json

import pytest

from scholar_labs.core.auth import AuthTokens, ManualAuthProvider, AuthError


def test_explicit_credentials_returns_auth_tokens():
    """Explicitly passed cookie and xsrf token are returned correctly."""
    provider = ManualAuthProvider(
        cookie="my-cookie-value",
        xsrf_token="my-xsrf-token",
    )
    tokens = provider.get_credentials()

    assert tokens.cookie == "my-cookie-value"
    assert tokens.xsrf_token == "my-xsrf-token"


def test_reads_from_environment_variables(monkeypatch):
    """When no explicit credentials given, reads from env vars."""
    monkeypatch.setenv("SCHOLAR_COOKIE", "env-cookie")
    monkeypatch.setenv("SCHOLAR_XSRF_TOKEN", "env-xsrf")

    provider = ManualAuthProvider()
    tokens = provider.get_credentials()

    assert tokens.cookie == "env-cookie"
    assert tokens.xsrf_token == "env-xsrf"


def test_reads_from_config_file(tmp_path, monkeypatch):
    """Falls back to versioned manual Auth Config if no env vars."""
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)

    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    config_file = config_dir / "auth.json"
    config_file.write_text(json.dumps({
        "version": 1,
        "method": "manual",
        "cookie": "file-cookie",
        "xsrf_token": "file-xsrf",
        "validated_at": "2026-05-26T00:00:00Z",
    }))

    monkeypatch.setenv("HOME", str(tmp_path))

    provider = ManualAuthProvider()
    tokens = provider.get_credentials()

    assert tokens.cookie == "file-cookie"
    assert tokens.xsrf_token == "file-xsrf"


def test_environment_variables_override_manual_auth_config(tmp_path, monkeypatch):
    """Environment variables take priority over local Auth Config."""
    monkeypatch.setenv("SCHOLAR_COOKIE", "env-cookie")
    monkeypatch.setenv("SCHOLAR_XSRF_TOKEN", "env-xsrf")

    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    config_file = config_dir / "auth.json"
    config_file.write_text(json.dumps({
        "version": 1,
        "method": "manual",
        "cookie": "file-cookie",
        "xsrf_token": "file-xsrf",
    }))

    monkeypatch.setenv("HOME", str(tmp_path))

    provider = ManualAuthProvider()
    tokens = provider.get_credentials()

    assert tokens.cookie == "env-cookie"
    assert tokens.xsrf_token == "env-xsrf"


def test_reads_chrome_profile_config_by_reextracting_browser_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    config_file = tmp_path / "auth.json"
    config_file.write_text(json.dumps({
        "version": 1,
        "method": "chrome-profile",
        "browser": "chrome",
        "profile": "Default",
        "profile_path": "/tmp/Chrome/Default",
    }))

    provider = ManualAuthProvider(
        config_store_path=config_file,
        browser_extractor_factory=lambda config: FakeExtractor(),
        xsrf_discoverer=lambda cookie_header: "discovered-xsrf",
    )

    tokens = provider.get_credentials()

    assert tokens == AuthTokens(cookie="SID=sid-value", xsrf_token="discovered-xsrf")


def test_raises_auth_error_when_no_credentials(monkeypatch, tmp_path):
    """Raises AuthError when no credentials available from any source."""
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    provider = ManualAuthProvider()
    with pytest.raises(AuthError, match="No authentication credentials"):
        provider.get_credentials()


class FakeExtractor:
    def extract(self):
        return type("Material", (), {"cookie_header": "SID=sid-value"})()
