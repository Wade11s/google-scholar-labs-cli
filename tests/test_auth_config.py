import json

import pytest

from scholar_labs.core.auth import (
    AuthConfigError,
    AuthConfigStore,
    ChromeProfileAuthConfig,
    LegacyAuthConfigError,
    ManualAuthConfig,
)


def test_writes_and_reads_manual_auth_config(tmp_path):
    store = AuthConfigStore(tmp_path / "auth.json")

    store.write(
        ManualAuthConfig(
            cookie="cookie",
            xsrf_token="xsrf",
            validated_at="2026-05-26T00:00:00Z",
        )
    )

    config = store.read()

    assert config == ManualAuthConfig(
        cookie="cookie",
        xsrf_token="xsrf",
        validated_at="2026-05-26T00:00:00Z",
    )


def test_writes_and_reads_chrome_profile_auth_config(tmp_path):
    store = AuthConfigStore(tmp_path / "auth.json")

    store.write(
        ChromeProfileAuthConfig(
            browser="chrome",
            profile="Default",
            profile_path="/Users/me/Library/Application Support/Google/Chrome/Default",
            validated_at="2026-05-26T00:00:00Z",
        )
    )

    config = store.read()

    assert config == ChromeProfileAuthConfig(
        browser="chrome",
        profile="Default",
        profile_path="/Users/me/Library/Application Support/Google/Chrome/Default",
        validated_at="2026-05-26T00:00:00Z",
    )


def test_rejects_legacy_auth_config_without_modifying_file(tmp_path):
    path = tmp_path / "auth.json"
    legacy = {"cookie": "cookie", "xsrf_token": "xsrf"}
    path.write_text(json.dumps(legacy))

    store = AuthConfigStore(path)

    with pytest.raises(LegacyAuthConfigError, match="Legacy auth config"):
        store.read()

    assert json.loads(path.read_text()) == legacy


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 2, "method": "manual", "cookie": "cookie", "xsrf_token": "xsrf"},
        {"version": 1, "method": "unknown"},
        {"version": 1, "method": "manual", "cookie": "cookie"},
    ],
)
def test_rejects_invalid_auth_config(tmp_path, payload):
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(payload))

    store = AuthConfigStore(path)

    with pytest.raises(AuthConfigError):
        store.read()
