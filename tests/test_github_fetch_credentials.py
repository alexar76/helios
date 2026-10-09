"""A GitHub token must not follow a redirect off api.github.com.

`urllib` re-sends every header except content-length/content-type to a redirect target — verified
against the stdlib: `HTTPRedirectHandler.redirect_request` builds `newheaders` from
`req.headers` minus `CONTENT_HEADERS` only. So a `Bearer` token issued for api.github.com used to
follow a 302 anywhere, and whoever could answer or forge one of these requests got the token.

Refusing cross-host redirects outright would break asset downloads, which GitHub legitimately
redirects off api.github.com. The redirect is followed; the credential is dropped.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from helios.knowledge.github_fetch import (  # noqa: E402
    _DropCredentialOnHostChange,
    _github_headers,
)

TOKEN = "gh-token-must-not-travel"


def _req(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=_github_headers(TOKEN))


def _has_auth(req) -> bool:
    if req is None:
        return False
    return any(k.lower() == "authorization" for k in req.headers) or \
        "Authorization" in getattr(req, "unredirected_hdrs", {})


def test_same_host_redirect_keeps_the_credential():
    handler = _DropCredentialOnHostChange()
    out = handler.redirect_request(_req("https://api.github.com/a"), None, 302, "", {},
                                   "https://api.github.com/b")
    assert _has_auth(out), "an authenticated same-host redirect would break without it"


def test_cross_host_redirect_drops_the_credential():
    handler = _DropCredentialOnHostChange()
    out = handler.redirect_request(_req("https://api.github.com/a"), None, 302, "", {},
                                   "https://objects.githubusercontent.com/b")
    assert out is not None, "the redirect itself must still be followed"
    assert not _has_auth(out)


def test_a_hostile_redirect_target_gets_nothing():
    handler = _DropCredentialOnHostChange()
    out = handler.redirect_request(_req("https://api.github.com/a"), None, 302, "", {},
                                   "https://evil.example/collect")
    assert not _has_auth(out)


def test_scheme_downgrade_is_refused_outright():
    handler = _DropCredentialOnHostChange()
    out = handler.redirect_request(_req("https://api.github.com/a"), None, 302, "", {},
                                   "http://api.github.com/b")
    assert out is None


def test_the_fetch_path_uses_the_guarded_opener():
    source = (ROOT / "helios" / "knowledge" / "github_fetch.py").read_text(encoding="utf-8")
    assert "_opener().open(req" in source
    assert "urllib.request.urlopen(req" not in source, \
        "a bare urlopen follows redirects with the credential attached"
