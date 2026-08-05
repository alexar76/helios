"""Fetch fresh GitHub text for allowlisted ecosystem repos (Calliope corpus)."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


@dataclass
class FetchResult:
    repo: str
    ok: bool
    path: Path | None
    error: str = ""
    chars: int = 0


def _github_headers(token: str) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "helios-calliope-fetch",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get_json(url: str, token: str, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(url, headers=_github_headers(token))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _readme_text(owner: str, repo: str, token: str) -> str:
    data = _get_json(f"https://api.github.com/repos/{owner}/{repo}/readme", token)
    content = data.get("content") or ""
    encoding = data.get("encoding") or "base64"
    if encoding == "base64":
        raw = base64.b64decode(content).decode("utf-8", errors="replace")
    else:
        raw = str(content)
    return raw[:12000]


def _latest_release(owner: str, repo: str, token: str) -> str:
    try:
        data = _get_json(f"https://api.github.com/repos/{owner}/{repo}/releases/latest", token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return ""
        raise
    tag = data.get("tag_name") or ""
    name = data.get("name") or ""
    body = (data.get("body") or "")[:4000]
    return f"Latest release: {tag} — {name}\n{body}".strip()


def fetch_cache_dir(data_dir: Path) -> Path:
    p = data_dir / "fetch"
    p.mkdir(parents=True, exist_ok=True)
    return p


def fetch_repo(
    *,
    owner: str,
    repo: str,
    data_dir: Path,
    token: str = "",
) -> FetchResult:
    if not _REPO_RE.match(repo):
        return FetchResult(repo=repo, ok=False, path=None, error="invalid repo name")
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    try:
        readme = _readme_text(owner, repo, token)
        release = _latest_release(owner, repo, token)
    except Exception as exc:  # noqa: BLE001 — fail-soft per repo
        return FetchResult(repo=repo, ok=False, path=None, error=str(exc)[:300])

    payload = {
        "repo": repo,
        "owner": owner,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readme": readme,
        "release": release,
        "url": f"https://github.com/{owner}/{repo}",
    }
    path = fetch_cache_dir(data_dir) / f"{repo}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return FetchResult(repo=repo, ok=True, path=path, chars=len(readme) + len(release))


def fetch_allowlist(
    *,
    owner: str,
    repos: list[str],
    data_dir: Path,
    token: str = "",
    limit: int = 20,
) -> list[FetchResult]:
    out: list[FetchResult] = []
    for repo in repos[:limit]:
        out.append(fetch_repo(owner=owner, repo=repo, data_dir=data_dir, token=token))
    return out


def corpus_from_fetch(
    data_dir: Path,
    *,
    repos: list[str] | None = None,
    max_chars: int = 6000,
) -> str:
    """Concatenate cached fetch blobs for Calliope grounding."""
    root = data_dir / "fetch"
    if not root.is_dir():
        return ""
    files = sorted(root.glob("*.json"))
    want = {r.lower() for r in repos} if repos else None
    parts: list[str] = []
    total = 0
    for path in files:
        if want is not None and path.stem.lower() not in want:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        repo = data.get("repo") or path.stem
        block = (
            f"## Fetched {repo} ({data.get('fetched_at', '')})\n"
            f"{(data.get('readme') or '')[:2500]}\n"
            f"{(data.get('release') or '')[:800]}\n"
        )
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()
