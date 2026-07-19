"""Input validation and path safety for HELIOS."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Match

ALLOWED_SPECIAL_TEMPLATES = frozenset({"promo-backfill", "calliope-episode"})

# Allowed job/template variable keys — no shell injection via ffmpeg args.
ALLOWED_VAR_KEYS = frozenset({
    "repo", "tag", "url", "summary", "episode", "season", "title", "topic", "script_id",
})

# Template IDs: alphanumeric + hyphen only.
TEMPLATE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
JOB_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,128}$")

MAX_VAR_VALUE_LEN = 2000
MAX_TEMPLATE_PATH_LEN = 512


def sanitize_text(text: str, *, max_len: int = MAX_VAR_VALUE_LEN) -> str:
    """NFKC normalize, strip control chars, cap length."""
    text = unicodedata.normalize("NFKC", text or "")
    text = "".join(ch for ch in text if ch in "\n\t\r" or (ord(ch) >= 32 and ord(ch) != 127))
    return text[:max_len]


def validate_template_id(template_id: str) -> str:
    tid = (template_id or "").strip().lower()
    if tid in ALLOWED_SPECIAL_TEMPLATES:
        return tid
    if not TEMPLATE_ID_RE.match(tid):
        raise ValueError(f"invalid template id: {template_id!r}")
    return tid


IDEMPOTENCY_KEY_RE = re.compile(r"^[a-zA-Z0-9_./:-]{1,256}$")


def validate_idempotency_key(key: str) -> str:
    k = (key or "").strip()
    if not IDEMPOTENCY_KEY_RE.match(k):
        raise ValueError(f"invalid idempotency key: {key!r}")
    return k


def validate_source(source: str) -> str:
    s = sanitize_text(source, max_len=64)
    if not re.match(r"^[a-z][a-z0-9._-]{0,63}$", s):
        raise ValueError(f"invalid source: {source!r}")
    return s


def resolve_asset_path(rel: str, roots: list[Path]) -> Path:
    """Resolve asset relative path within configured roots only."""
    rel = (rel or "").strip().replace("\\", "/")
    if not rel or rel.startswith("/") or ".." in rel.split("/"):
        raise ValueError(f"unsafe asset path: {rel!r}")
    if len(rel) > MAX_TEMPLATE_PATH_LEN:
        raise ValueError("asset path too long")
    for root in roots:
        candidate = (root / rel).resolve()
        root_resolved = root.resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            continue
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"asset not found in roots: {rel}")


def validate_job_id(job_id: str) -> str:
    jid = (job_id or "").strip()
    if not JOB_ID_RE.match(jid):
        raise ValueError(f"invalid job id: {job_id!r}")
    return jid


def validate_vars(vars_dict: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, val in (vars_dict or {}).items():
        k = str(key).strip()
        if k not in ALLOWED_VAR_KEYS:
            raise ValueError(f"disallowed var key: {k}")
        out[k] = sanitize_text(str(val))
    return out


def validate_existing_file(path_str: str, roots: list[Path]) -> Path:
    """Ensure an absolute path to an existing file stays under configured roots."""
    if not path_str or not path_str.strip():
        raise ValueError("empty path")
    p = Path(path_str).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"file not found: {p}")
    for root in roots:
        try:
            p.relative_to(root.resolve())
            return p
        except ValueError:
            continue
    raise ValueError(f"path outside allowed roots: {p}")


def safe_subprocess_arg(arg: str) -> str:
    """Reject args that look like shell metacharacters."""
    if any(c in arg for c in ";|&$`<>"):
        raise ValueError("unsafe subprocess argument")
    return arg


def substitute_vars(text: str, vars: dict[str, str]) -> str:
    def repl(m: Match[str]) -> str:
        key = m.group(1)
        return vars.get(key, m.group(0))
    return re.sub(r"\{(\w+)\}", repl, text)
