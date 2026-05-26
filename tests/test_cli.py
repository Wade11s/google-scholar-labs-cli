import json

from typer.testing import CliRunner

from scholar_labs.cli import main as cli_main
from scholar_labs.core.browser_auth import BrowserCookieMaterial, BrowserProfile
from scholar_labs.core.login import LoginRateLimitError


runner = CliRunner()


def test_root_command_shows_help():
    result = runner.invoke(cli_main.app, [])

    assert result.exit_code == 0
    assert "search" in result.output
    assert "login" in result.output


def test_search_command_runs_search(monkeypatch):
    calls = {}

    async def fake_run_search(service, query):
        calls["query"] = query
        return cli_main.SearchResponse(status="done")

    monkeypatch.setenv("SCHOLAR_COOKIE", "cookie")
    monkeypatch.setenv("SCHOLAR_XSRF_TOKEN", "xsrf")
    monkeypatch.setattr(cli_main, "_run_search", fake_run_search)

    result = runner.invoke(cli_main.app, ["search", "large language model safety"])

    assert result.exit_code == 0
    assert calls["query"] == "large language model safety"
    assert "large language model safety" in result.output


def test_search_command_uses_manual_auth_config(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    (config_dir / "auth.json").write_text(json.dumps({
        "version": 1,
        "method": "manual",
        "cookie": "file-cookie",
        "xsrf_token": "file-xsrf",
    }))

    async def fake_run_search(service, query):
        calls["query"] = query
        return cli_main.SearchResponse(status="done")

    monkeypatch.setattr(cli_main, "_run_search", fake_run_search)

    result = runner.invoke(cli_main.app, ["search", "manual config query"])

    assert result.exit_code == 0
    assert calls["query"] == "manual config query"


def test_root_query_is_not_a_search(monkeypatch):
    calls = {}

    async def fake_run_search(service, query):
        calls["query"] = query
        return cli_main.SearchResponse(status="done")

    monkeypatch.setenv("SCHOLAR_COOKIE", "cookie")
    monkeypatch.setenv("SCHOLAR_XSRF_TOKEN", "xsrf")
    monkeypatch.setattr(cli_main, "_run_search", fake_run_search)

    result = runner.invoke(cli_main.app, ["large language model safety"])

    assert result.exit_code != 0
    assert calls == {}


def test_auth_manual_writes_versioned_auth_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(
        cli_main.app,
        ["auth", "manual"],
        input="cookie-value\nxsrf-value\n",
    )

    assert result.exit_code == 0
    config_path = tmp_path / ".scholar-labs-cli" / "auth.json"
    config = json.loads(config_path.read_text())
    assert config["version"] == 1
    assert config["method"] == "manual"
    assert config["cookie"] == "cookie-value"
    assert config["xsrf_token"] == "xsrf-value"


def test_auth_status_reports_manual_without_leaking_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    (config_dir / "auth.json").write_text(json.dumps({
        "version": 1,
        "method": "manual",
        "cookie": "secret-cookie-value",
        "xsrf_token": "secret-xsrf-value",
        "validated_at": "2026-05-26T00:00:00Z",
    }))

    result = runner.invoke(cli_main.app, ["auth", "status"])

    assert result.exit_code == 0
    assert "manual" in result.output
    assert "2026-05-26T00:00:00Z" in result.output
    assert "secret-cookie-value" not in result.output
    assert "secret-xsrf-value" not in result.output


def test_auth_logout_removes_auth_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / ".scholar-labs-cli"
    config_dir.mkdir()
    config_path = config_dir / "auth.json"
    config_path.write_text(json.dumps({
        "version": 1,
        "method": "manual",
        "cookie": "cookie",
        "xsrf_token": "xsrf",
    }))

    result = runner.invoke(cli_main.app, ["auth", "logout"])

    assert result.exit_code == 0
    assert not config_path.exists()


def test_search_without_auth_prompts_for_login_when_interactive(tmp_path, monkeypatch):
    login_calls = {}
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    monkeypatch.setattr(cli_main, "_is_interactive", lambda json_output: True)
    monkeypatch.setattr(
        cli_main,
        "_run_browser_login",
        lambda browser, profile, hl: login_calls.setdefault("called", True),
    )

    result = runner.invoke(cli_main.app, ["search", "query"], input="y\n")

    assert result.exit_code == 0
    assert "Start browser login now?" in result.output
    assert login_calls == {"called": True}


def test_json_search_without_auth_does_not_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SCHOLAR_COOKIE", raising=False)
    monkeypatch.delenv("SCHOLAR_XSRF_TOKEN", raising=False)
    monkeypatch.setattr(cli_main, "_is_interactive", lambda json_output: False)

    result = runner.invoke(cli_main.app, ["search", "query", "--json"])

    assert result.exit_code == 1
    assert "Start browser login now?" not in result.output
    assert "Run 'sls login'" in result.output


def test_login_writes_chrome_profile_source_record(tmp_path, monkeypatch, httpx_mock):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        cli_main,
        "create_browser_credential_extractor",
        lambda browser, profile: FakeBrowserExtractor(),
    )
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text='"/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf"',
    )
    httpx_mock.add_response(
        method="POST",
        url="https://scholar.google.com/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf",
        content=b"ok",
    )

    result = runner.invoke(cli_main.app, ["login"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".scholar-labs-cli" / "auth.json").read_text())
    assert config["method"] == "chrome-profile"
    assert config["browser"] == "chrome"
    assert "cookie" not in config
    assert "xsrf_token" not in config


def test_login_recovery_opens_browser_and_retries(tmp_path, monkeypatch, httpx_mock):
    opened = []
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_main, "_is_interactive", lambda json_output: True)
    monkeypatch.setattr(cli_main.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(
        cli_main,
        "create_browser_credential_extractor",
        lambda browser, profile: FakeBrowserExtractor(),
    )
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text="<html>No token yet</html>",
    )
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text='"/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf"',
    )
    httpx_mock.add_response(
        method="POST",
        url="https://scholar.google.com/scholar_labs/search/session_data?hl=en&xsrf=test-xsrf",
        content=b"ok",
    )

    result = runner.invoke(cli_main.app, ["login"], input="y\n")

    assert result.exit_code == 0
    assert opened == ["https://scholar.google.com/scholar_labs/search?hl=en"]
    config = json.loads((tmp_path / ".scholar-labs-cli" / "auth.json").read_text())
    assert config["method"] == "chrome-profile"


def test_login_does_not_recover_when_noninteractive(tmp_path, monkeypatch, httpx_mock):
    opened = []
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_main, "_is_interactive", lambda json_output: False)
    monkeypatch.setattr(cli_main.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(
        cli_main,
        "create_browser_credential_extractor",
        lambda browser, profile: FakeBrowserExtractor(),
    )
    httpx_mock.add_response(
        url="https://scholar.google.com/scholar_labs/search?hl=en",
        text="<html>No token</html>",
    )

    result = runner.invoke(cli_main.app, ["login"])

    assert result.exit_code == 1
    assert opened == []


def test_login_rate_limit_does_not_open_browser_recovery(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_main, "_is_interactive", lambda json_output: True)
    monkeypatch.setattr(cli_main.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(
        cli_main,
        "_run_browser_login",
        lambda browser, profile, hl: (_ for _ in ()).throw(
            LoginRateLimitError("Scholar Labs rate limited login; retry after 60 seconds.")
        ),
    )

    result = runner.invoke(cli_main.app, ["login"])

    assert result.exit_code == 1
    assert "rate limited" in result.output
    assert opened == []


class FakeBrowserExtractor:
    profile = BrowserProfile(
        browser="chrome",
        profile="Default",
        profile_path="/tmp/Chrome/Default",
    )

    def extract(self):
        return BrowserCookieMaterial(cookie_header="SID=sid-value")
