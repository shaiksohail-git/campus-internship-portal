"""Host-header guard (custom domain hardening) + cookie banner markup.

The guard is the `ALLOWED_HOSTS` before_request hook in the app factory:
an empty list accepts everything (local dev default); a populated list
answers only to the configured hosts (case-insensitive, port-stripped,
IPv6-literal-safe) and rejects everything else with 400.
"""

import re
from pathlib import Path

import pytest

from conftest import ADMIN_PASSWORD, login, make_admin

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_JS = REPO_ROOT / "frontend" / "static" / "js" / "app.js"


# ---------------------------------------------------------------- helpers


def get_with_host(client, path, host):
    """GET a path while faking the browser's Host header.

    Uses base_url rather than environ_base: Werkzeug's EnvironBuilder
    derives HTTP_HOST from base_url and overrides anything supplied via
    environ_base, so that approach silently tests the wrong host."""
    return client.get(path, base_url=f"http://{host}")


def set_allowed(app, hosts):
    """Point the guard at `hosts` and drop TestConfig's SERVER_NAME, which
    would otherwise make Werkzeug 400/404 foreign hosts before the guard
    (the guard must be the thing under test)."""
    app.config["ALLOWED_HOSTS"] = hosts
    app.config["SERVER_NAME"] = None


# ------------------------------------------------------- host-header guard


def test_empty_allowlist_accepts_any_host(app, client):
    """Dev default: no ALLOWED_HOSTS configured, nothing is ever rejected."""
    set_allowed(app, [])
    for host in ("localhost:5000", "127.0.0.1:5000", "anything.example"):
        assert get_with_host(client, "/", host).status_code == 200, host


def test_allowed_host_passes_guard(app, client):
    set_allowed(app, ["placements.mycollege.edu"])
    res = get_with_host(client, "/", "placements.mycollege.edu")
    assert res.status_code == 200
    assert b"Campus" in res.data  # the landing page actually rendered


def test_allowed_host_with_port_passes_guard(app, client):
    """Browsers send host:port; the port must not cause a false rejection."""
    set_allowed(app, ["placements.mycollege.edu"])
    assert get_with_host(client, "/", "placements.mycollege.edu:443").status_code == 200


def test_allowed_host_is_case_insensitive(app, client):
    """DNS names are case-insensitive; LOCALHOST must not be rejected."""
    set_allowed(app, ["Placements.MyCollege.edu"])
    assert get_with_host(client, "/", "placements.mycollege.edu").status_code == 200
    assert get_with_host(client, "/", "PLACEMENTS.MYCOLLEGE.EDU:80").status_code == 200


def test_www_variant_must_be_listed_explicitly(app, client):
    """www.apex is a different host: not auto-allowed, but fine when listed."""
    set_allowed(app, ["placements.mycollege.edu"])
    assert get_with_host(client, "/", "www.placements.mycollege.edu").status_code == 400

    set_allowed(app, ["placements.mycollege.edu", "www.placements.mycollege.edu"])
    assert get_with_host(client, "/", "www.placements.mycollege.edu").status_code == 200


def test_foreign_host_is_rejected_with_400(app, client):
    set_allowed(app, ["placements.mycollege.edu"])
    res = get_with_host(client, "/", "evil.example")
    assert res.status_code == 400
    assert b"Invalid host." in res.data


def test_rejection_is_flat_400_not_html_error_page(app, client):
    """The guard fires before_request, so even API paths get a bare 400
    (attackers should not be able to probe which hosts are valid via
    differing error payloads)."""
    set_allowed(app, ["placements.mycollege.edu"])
    res = get_with_host(client, "/api/v1/auth/me", "evil.example")
    assert res.status_code == 400


def test_ipv6_loopback_with_port_passes_guard(app, client):
    """request.host for IPv6 literals is [::1]:5000; naive colon-split
    would mangle this to '['."""
    set_allowed(app, ["::1", "localhost"])
    assert get_with_host(client, "/", "[::1]:5000").status_code == 200


def test_guard_allows_authenticated_flows_when_host_matches(app, client):
    """Sanity: with the guard on, a normal admin login + page fetch works."""
    set_allowed(app, ["localhost"])
    make_admin(app, "guard-admin@test.edu")
    res = login(client, "guard-admin@test.edu", ADMIN_PASSWORD)
    assert res.status_code == 200
    assert client.get("/admin/dashboard").status_code == 200


@pytest.mark.parametrize(
    "host",
    ["evil.example", "evil.example:8080", "sub.placements.mycollege.edu.evil.example", "0.0.0.0"],
)
def test_host_header_injection_variants_rejected(app, client, host):
    set_allowed(app, ["placements.mycollege.edu"])
    assert get_with_host(client, "/", host).status_code == 400


def test_allowed_hosts_change_applies_without_restart(app, client):
    """The guard reads config per request, so rotating domains needs no
    process restart (documented behavior)."""
    set_allowed(app, ["old.example"])
    assert get_with_host(client, "/", "old.example").status_code == 200
    assert get_with_host(client, "/", "new.example").status_code == 400
    set_allowed(app, ["new.example"])
    assert get_with_host(client, "/", "new.example").status_code == 200
    assert get_with_host(client, "/", "old.example").status_code == 400


# ------------------------------------------------------------ cookie banner


def _base_html(client):
    return client.get("/").get_data(as_text=True)


def test_cookie_banner_present_on_public_pages(client):
    html = _base_html(client)
    assert 'id="cookieBanner"' in html


def test_cookie_banner_starts_hidden(client):
    """Hidden by default; app.js reveals it only when no consent is stored."""
    html = _base_html(client)
    banner = re.search(r'<div class="cookie-banner[^"]*" id="cookieBanner"', html)
    assert banner, "cookie banner markup not found"
    assert "hidden" in banner.group(0)


def test_cookie_banner_copy_is_honest(client):
    """The banner must state what we actually store: one session cookie."""
    html = _base_html(client).lower()
    assert "single session cookie" in html
    assert "no tracking" in html
    assert 'id="cookieaccept"' in html  # accept button exists


def test_cookie_banner_present_on_auth_pages(client):
    """auth_base.html carries the banner too (consistency fix)."""
    res = client.get("/login")
    assert res.status_code == 200
    assert 'id="cookieBanner"' in res.get_data(as_text=True)


def test_cookie_banner_hidden_logic_is_client_side_only(client):
    """Consent is read from localStorage by app.js; no server round-trip
    or server-set consent cookie is involved."""
    html = _base_html(client)
    assert 'id="cookieAccept"' in html
    assert "campusplace-cookie-ok" not in html  # key lives only in app.js
    app_js = APP_JS.read_text(encoding="utf-8")
    assert 'localStorage.getItem(COOKIE_KEY)' in app_js
    assert 'localStorage.setItem(COOKIE_KEY, "1")' in app_js
