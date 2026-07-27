"""Configuration: env-first secrets, helios.config.yaml for tuning."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__version__ = "0.1.0"

DEFAULT_CONFIG_NAME = "helios.config.yaml"


def _env(key: str, default: str = "") -> str:
    file_key = f"{key}_FILE"
    if file_key in os.environ:
        p = Path(os.environ[file_key])
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return os.environ.get(key, default)


@dataclass
class LlmConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    fallback_provider: str = ""
    fallback_model: str = ""
    fallback_base_url: str = ""
    fallback_api_key: str = ""
    max_calls_per_day: int = 200


@dataclass
class HeliosConfig:
    data_dir: Path
    config_path: Path
    dry_run: bool
    channel_handle: str
    default_category: str
    default_language: str
    max_uploads_per_day: int
    max_job_retries: int
    asset_roots: list[Path]
    templates_dir: Path
    promo_materials_dir: Path | None
    github_owner: str
    repos_allowlist: list[str]
    webhook_url: str
    notify_on_status: list[str]
    worker_poll_interval_sec: int
    llm: LlmConfig
    director_enabled: bool
    calliope_enabled: bool
    calliope_editorial_enabled: bool
    calliope_scout_interval_days: int
    calliope_weekly_enqueue_quota: int
    calliope_scout_ideas_per_run: int
    calliope_auto_enqueue_per_run: int
    calliope_backfill_pause_threshold: int
    mnemosyne_path: Path | None
    youtube_client_secret: Path | None
    youtube_token: Path | None
    api_key: str
    http_port: int
    auto_approve: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def file_roots(cfg: HeliosConfig) -> list[Path]:
    """Roots allowed for pre-rendered upload paths (backfill / ingest)."""
    roots = [r.resolve() for r in cfg.asset_roots]
    if cfg.promo_materials_dir:
        roots.append(cfg.promo_materials_dir.resolve())
    return roots


_LLM_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-sonnet-4-20250514",
        "key_env": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "openai-compatible": {
        "base_url": "http://127.0.0.1:8080/v1",
        "model": "default",
        "key_env": "HELIOS_LLM_API_KEY",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "llama3.1",
        "key_env": "",
    },
    "lmstudio": {
        "base_url": "http://127.0.0.1:1234/v1",
        "model": "local-model",
        "key_env": "",
    },
    "llamacpp": {
        "base_url": "http://127.0.0.1:8080/v1",
        "model": "local-model",
        "key_env": "",
    },
}


def _resolve_llm(prefix: str = "HELIOS_LLM") -> LlmConfig:
    provider = (_env(f"{prefix}_PROVIDER") or "deepseek").lower()
    preset = _LLM_PRESETS.get(provider, _LLM_PRESETS["openai-compatible"])
    model = _env(f"{prefix}_MODEL") or preset["model"]
    base_url = _env(f"{prefix}_BASE_URL") or preset["base_url"]
    key_env = preset.get("key_env") or ""
    api_key = _env(key_env) if key_env else _env(f"{prefix}_API_KEY")

    fb_provider = _env(f"{prefix}_FALLBACK_PROVIDER")
    fb = LlmConfig(provider=provider, model=model, base_url=base_url, api_key=api_key)
    if fb_provider:
        fb_preset = _LLM_PRESETS.get(fb_provider.lower(), _LLM_PRESETS["openai-compatible"])
        fb.fallback_provider = fb_provider
        fb.fallback_model = _env(f"{prefix}_FALLBACK_MODEL") or fb_preset["model"]
        fb.fallback_base_url = _env(f"{prefix}_FALLBACK_BASE_URL") or fb_preset["base_url"]
        fb_key_env = fb_preset.get("key_env") or ""
        fb.fallback_api_key = _env(fb_key_env) if fb_key_env else _env(f"{prefix}_FALLBACK_API_KEY")
    fb.max_calls_per_day = int(_env("HELIOS_LLM_MAX_CALLS_PER_DAY", "200"))
    return fb


def load_config(config_path: Path | None = None) -> HeliosConfig:
    cfg_file = config_path or Path(_env("HELIOS_CONFIG", DEFAULT_CONFIG_NAME))
    raw: dict[str, Any] = {}
    if cfg_file.exists():
        raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}

    data_dir = Path(_env("HELIOS_DATA_DIR", "./data"))
    channel = raw.get("channel", {})
    limits = raw.get("limits", {})
    notify = raw.get("notify", {})
    worker = raw.get("worker", {})
    director = raw.get("director", {})
    calliope = raw.get("calliope", {})
    github = raw.get("github", {})

    roots = [Path(p) for p in raw.get("asset_roots", [])]
    promo = raw.get("promo_materials_dir")
    promo_path = Path(promo) if promo else None

    yt_secret = _env("YOUTUBE_CLIENT_SECRET")
    yt_token = _env("YOUTUBE_TOKEN")
    secret_path = Path(yt_secret) if yt_secret else None
    token_path = Path(yt_token) if yt_token else None

    dioscuri_data = _env("DIOSCURI_DATA_DIR")
    mnemo_env = _env("HELIOS_MNEMOSYNE_PATH")
    mnemo_cfg = calliope.get("mnemosyne_path")
    mnemo_path: Path | None = None
    if mnemo_env:
        mnemo_path = Path(mnemo_env)
    elif mnemo_cfg:
        mnemo_path = Path(str(mnemo_cfg))
    elif dioscuri_data:
        mnemo_path = Path(dioscuri_data) / "mnemosyne.json"

    auto_approve = _env("HELIOS_AUTO_APPROVE", "").lower() in ("1", "true", "yes")
    if not auto_approve:
        auto_approve = bool(channel.get("auto_approve", False))

    return HeliosConfig(
        data_dir=data_dir,
        config_path=cfg_file,
        dry_run=_env("HELIOS_DRY_RUN", "0") in ("1", "true", "yes"),
        channel_handle=channel.get("handle", "@My-AI-Factory"),
        default_category=str(channel.get("default_category", "28")),
        default_language=channel.get("default_language", "en"),
        max_uploads_per_day=int(limits.get("max_uploads_per_day", 9)),
        max_job_retries=int(limits.get("max_job_retries", 2)),
        asset_roots=roots,
        templates_dir=Path(raw.get("templates_dir", "./templates")),
        promo_materials_dir=promo_path,
        github_owner=github.get("owner", "alexar76"),
        repos_allowlist=github.get("repos_allowlist", []),
        webhook_url=notify.get("webhook_url", "") or _env("HELIOS_WEBHOOK_URL"),
        notify_on_status=notify.get("on_status", ["awaiting_approval", "failed"]),
        worker_poll_interval_sec=int(worker.get("poll_interval_sec", 300)),
        llm=_resolve_llm(),
        director_enabled=bool(director.get("enabled", True)),
        calliope_enabled=bool(calliope.get("enabled", True)),
        calliope_editorial_enabled=bool(calliope.get("editorial_enabled", True)),
        calliope_scout_interval_days=int(calliope.get("scout_interval_days", 3)),
        calliope_weekly_enqueue_quota=int(calliope.get("weekly_enqueue_quota", 3)),
        calliope_scout_ideas_per_run=int(calliope.get("scout_ideas_per_run", 5)),
        calliope_auto_enqueue_per_run=int(calliope.get("auto_enqueue_per_run", 1)),
        calliope_backfill_pause_threshold=int(calliope.get("backfill_pause_threshold", 8)),
        mnemosyne_path=mnemo_path,
        youtube_client_secret=secret_path,
        youtube_token=token_path,
        api_key=_env("HELIOS_API_KEY"),
        http_port=int(_env("HELIOS_HTTP_PORT", "8791")),
        auto_approve=auto_approve,
        raw=raw,
    )


def config_summary(cfg: HeliosConfig) -> dict[str, Any]:
    return {
        "data_dir": str(cfg.data_dir),
        "dry_run": cfg.dry_run,
        "channel": cfg.channel_handle,
        "max_uploads_per_day": cfg.max_uploads_per_day,
        "director": cfg.director_enabled,
        "calliope": cfg.calliope_enabled,
        "calliope_editorial": cfg.calliope_editorial_enabled,
        "scout_interval_days": cfg.calliope_scout_interval_days,
        "weekly_enqueue_quota": cfg.calliope_weekly_enqueue_quota,
        "backfill_pause_threshold": cfg.calliope_backfill_pause_threshold,
        "mnemosyne": str(cfg.mnemosyne_path) if cfg.mnemosyne_path else None,
        "llm_provider": cfg.llm.provider,
        "auto_approve": cfg.auto_approve,
    }
