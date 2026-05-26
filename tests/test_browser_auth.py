from http.cookiejar import Cookie, CookieJar

import pytest

from scholar_labs.core.browser_auth import (
    BrowserAuthError,
    BrowserCredentialExtractor,
    BrowserCookieMaterial,
    BrowserProfile,
    MacOSChromeCredentialExtractor,
    UnsupportedBrowserEnvironment,
    create_browser_credential_extractor,
)


def test_unsupported_browser_environment_points_to_manual_fallback():
    with pytest.raises(UnsupportedBrowserEnvironment, match="sls auth manual"):
        create_browser_credential_extractor(
            browser="firefox",
            profile="Default",
            platform="darwin",
        )


def test_non_macos_browser_environment_is_unsupported():
    with pytest.raises(UnsupportedBrowserEnvironment, match="macOS Chrome"):
        create_browser_credential_extractor(
            browser="chrome",
            profile="Default",
            platform="linux",
        )


def test_macos_chrome_extractor_uses_narrow_interface():
    extractor = create_browser_credential_extractor(
        browser="chrome",
        profile="Default",
        platform="darwin",
    )

    assert isinstance(extractor, BrowserCredentialExtractor)
    assert extractor.profile == BrowserProfile(browser="chrome", profile="Default")


def test_macos_chrome_extractor_reads_from_temporary_cookie_db_copy(tmp_path):
    profile_path = tmp_path / "Default"
    cookie_db = profile_path / "Network" / "Cookies"
    cookie_db.parent.mkdir(parents=True)
    cookie_db.write_text("cookie-db")
    seen = {}

    def fake_cookie_loader(cookie_file, domain_name):
        seen["cookie_file"] = cookie_file
        seen["domain_name"] = domain_name
        assert cookie_file != str(cookie_db)
        assert cookie_file.read_text() == "cookie-db"
        jar = CookieJar()
        jar.set_cookie(_cookie("SID", "sid-value", ".google.com"))
        jar.set_cookie(_cookie("SCHOLAR", "scholar-value", "scholar.google.com"))
        return jar

    extractor = MacOSChromeCredentialExtractor(
        BrowserProfile(
            browser="chrome",
            profile="Default",
            profile_path=str(profile_path),
        ),
        cookie_loader=fake_cookie_loader,
    )

    material = extractor.extract()

    assert material == BrowserCookieMaterial(
        cookie_header="SID=sid-value; SCHOLAR=scholar-value"
    )
    assert seen["domain_name"] == ".google.com"


def test_macos_chrome_extractor_reports_missing_cookie_db(tmp_path):
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    extractor = MacOSChromeCredentialExtractor(
        BrowserProfile(
            browser="chrome",
            profile="Default",
            profile_path=str(profile_path),
        )
    )

    with pytest.raises(BrowserAuthError, match="Chrome cookie database"):
        extractor.extract()


def test_macos_chrome_extractor_reports_missing_profile(tmp_path):
    extractor = MacOSChromeCredentialExtractor(
        BrowserProfile(
            browser="chrome",
            profile="Default",
            profile_path=str(tmp_path / "Missing"),
        )
    )

    with pytest.raises(BrowserAuthError, match="Chrome profile not found"):
        extractor.extract()


def test_macos_chrome_extractor_reports_decryption_failure(tmp_path):
    profile_path = tmp_path / "Default"
    cookie_db = profile_path / "Network" / "Cookies"
    cookie_db.parent.mkdir(parents=True)
    cookie_db.write_text("cookie-db")

    def failing_cookie_loader(cookie_file, domain_name):
        raise RuntimeError("decrypt failed")

    extractor = MacOSChromeCredentialExtractor(
        BrowserProfile(
            browser="chrome",
            profile="Default",
            profile_path=str(profile_path),
        ),
        cookie_loader=failing_cookie_loader,
    )

    with pytest.raises(BrowserAuthError, match="decryption failed"):
        extractor.extract()


def _cookie(name, value, domain):
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )
