import os

import json
import os
from pathlib import Path

import pytest

from scholar_labs.core.auth import ManualAuthProvider, AuthTokens, AuthError


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
    """Falls back to ~/.scholar-labs-cli/auth.json if no env vars."""
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)

    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    config_file = config_dir / "auth.json"
    config_file.write_text(json.dumps({
        "cookie": "file-cookie",
        "xsrf_token": "file-xsrf",
    }))

    monkeypatch.setenv("HOME", str(tmp_path))

    provider = ManualAuthProvider()
    tokens = provider.get_credentials()

    assert tokens.cookie == "file-cookie"
    assert tokens.xsrf_token == "file-xsrf"


def test_raises_auth_error_when_no_credentials(monkeypatch, tmp_path):
    """Raises AuthError when no credentials available from any source."""
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    provider = ManualAuthProvider()
    with pytest.raises(AuthError, match="No authentication credentials"):
        provider.get_credentials()
