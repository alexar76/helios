"""CALLIOPE — HELIOS screenwriter & creative director.

Named after the Muse of epic poetry. Grounds every script in MNEMOSYNE (DIOSCURI's
ecosystem knowledge): GitHub READMEs, releases, live demo state.

Charter:
- Generates voiceover + segment structure for NEW ecosystem videos.
- Backfill (PromoMaterials) stays human-authored — Calliope does not rewrite it.
- All uploads remain private-first; operator approves in Studio.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from helios.config import HeliosConfig
from helios.knowledge.aegis import wrap_corpus, wrap_user
from helios.knowledge.github_fetch import corpus_from_fetch, fetch_allowlist
from helios.knowledge.mnemosyne import MnemosyneReader
from helios.llm import LlmBudgetExceeded, LlmClient
from helios.queue import QueueStore
from helios.seasons import current_season, parse_seasons
from helios.security import sanitize_text, validate_template_id
from helios.visuals_catalog import (
    COURSE as _COURSE_HERO,
    coerce_asset_for_repo,
    primary_visual,
    visual_pool,
)

CALLIOPE_SYSTEM = """You are CALLIOPE — Muse of epic poetry and screenwriter for @My-AI-Factory,
the YouTube channel of the alexar76 open-source AI agent economy (AICOM / AIMarket).

Your job: write short-form ecosystem explainers (40–90 seconds VO) grounded ONLY in the
reference corpus below. Never invent features, URLs, or metrics not in the corpus.

Tone: clear, technical-but-accessible, MIT open-source, no hype/clickbait, English VO.

Output JSON only:
{
  "title": "YouTube title ≤100 chars",
  "description": "2-4 sentences + links from corpus",
  "tags": ["AIAgents", "OpenSource", ...],
  "topic": "one-line topic",
  "repos": ["repo-names-mentioned"],
  "demo_url": "https://... or empty",
  "segments": [
    {
      "vo": "spoken narration, 1-2 sentences",
      "caption": "SHORT ON-SCREEN TEXT",
      "visual": {
        "type": "image",
        "path": "hero-demo-preview.gif",
        "kenburns": true
      }
    }
  ]
}

Rules for segments:
- 3 to 5 segments; total VO ~80–220 words.
- Prefer visual.type "image" or "video" with REAL product visuals — NEVER a plain black card.
- Pick visual.path that MATCHES the repos/topic (wrong product on screen = failed video):
  - aimarket-courses / academy → course-hero-16x9.png ONLY
  - aicom-landing / dioscuri / theoros → aicom-landing-hero.gif (or alien-monitor-hero.gif)
  - alien-monitor / aicom / metis / helios → alien-monitor-hero.gif
  - acex / pulse-terminal → pulse-floor.png
  - platon / oracles / gaia / chronos / VRF / chaos → platon-umbral-hero.gif or platon-cosmos.png
  - aimarket-hub / argus / factory pipeline → hero-demo-preview.gif (Factory UI ONLY)
- Example visual: {"type":"image","path":"platon-umbral-hero.gif","kenburns":true}
- NEVER use course-hero-16x9.png unless the topic is actually courses/academies.
- NEVER put Factory orchestration / storefront UI on Platon, oracles, dioscuri, theoros, helios, or landing topics.
- NEVER put Platon visuals on Factory/hub-only topics.
- Use "card" only as last resort, with a BRIGHT accent color (#1a3a6b / #0f766e / #7c2d12) and short label.
- Mention live demo URLs when corpus has them.
- End with GitHub star / open-source CTA when appropriate.
"""

_CALLIOPE_VISUAL_POOL = visual_pool(allow_courses=True)
_COURSE_REPOS = frozenset({"aimarket-courses"})

PITCH_SYSTEM = """You are CALLIOPE — creative strategist for @My-AI-Factory YouTube.
Given ecosystem knowledge, propose fresh short-video topics developers would watch TODAY.

Output JSON only:
{
  "pitches": [
    {
      "topic": "short label",
      "hook": "why now, one sentence",
      "repos": ["repo"],
      "query": "search query for more context",
      "priority": 1-100
    }
  ]
}
Propose 5 pitches. Prioritize: recent releases, under-covered repos, live demos, security/MCP themes.
No duplicate of generic "what is AI" — specific to alexar76 ecosystem.
"""

SCOUT_SYSTEM = """You are CALLIOPE — editorial director for @My-AI-Factory YouTube.

Your job: keep the channel alive with FRESH video ideas mined from the ENTIRE alexar76
open-source ecosystem — not only new GitHub releases or new repos.

The MAIN programming is SEASONAL: each season has themes and focus repos. Prefer season
angles over "X v1.2 shipped" release recaps. Release notes are seasoning, not the meal.

The ecosystem is LARGE (Factory, ARGUS, WARDEN, oracles, DIOSCURI, Alien Monitor, academies,
lottery, HELIOS, THEOROS, etc.). Even when nothing shipped yesterday, there are always:
- season-theme deep dives
- repos never explained on video yet
- evergreen "how X fits the economy" angles
- live demo walkthroughs
- security/MCP/agent patterns across products
- comparisons and "why we built this" stories from README text

You receive: current season brief, full repo inventory, what's already published/queued,
MNEMOSYNE corpus samples, and optional freshly fetched README/release snippets.

Output JSON only:
{
  "pitches": [
    {
      "topic": "short label",
      "hook": "why viewers care now",
      "angle": "deep-dive|ecosystem-map|live-demo|security|season|compare",
      "repos": ["repo"],
      "query": "BM25 search query for script writing",
      "priority": 1-100,
      "evergreen": true,
      "season_fit": true
    }
  ]
}

Rules:
- Propose exactly {limit} pitches.
- At least 60% must fit the CURRENT SEASON themes/repos.
- At least half must be EVERGREEN (not tied to a release this week).
- Do NOT propose bare "repo vX.Y shipped" release shorts.
- Do NOT repeat topics already in published_episodes or queued_topics lists.
- Prefer repos with live demo URLs when available.
- MIT/open-source tone; no clickbait.
"""

MAX_SEGMENTS = 6
MAX_VO_PER_SEG = 400
MAX_CAPTION = 80


@dataclass
class Pitch:
    topic: str
    hook: str
    repos: list[str]
    query: str
    priority: int


@dataclass
class EpisodeScript:
    title: str
    description: str
    tags: list[str]
    topic: str
    repos: list[str]
    demo_url: str
    segments: list[dict[str, Any]]
    defaults: dict[str, Any] = field(
        default_factory=lambda: {"voice": "Daniel", "voice_rate": 175, "aspect": "9:16"}
    )

    def to_template_dict(self) -> dict[str, Any]:
        return {
            "id": "calliope-episode",
            "defaults": self.defaults,
            "segments": self.segments,
            "meta": {
                "topic": self.topic,
                "repos": self.repos,
                "demo_url": self.demo_url,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_template_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")


def _primary_visual_for_repos(repos: list[str], topic: str = "") -> str:
    """Pick a product visual that matches the episode's repos/topic."""
    if repos:
        return primary_visual(repos[0], topic)
    return primary_visual("", topic)


def _validate_segment(
    seg: dict[str, Any],
    *,
    index: int = 0,
    repos: list[str] | None = None,
    topic: str = "",
) -> dict[str, Any]:
    vo = sanitize_text(str(seg.get("vo", "")), max_len=MAX_VO_PER_SEG)
    caption = sanitize_text(str(seg.get("caption", vo[:MAX_CAPTION])), max_len=MAX_CAPTION).upper()
    if not vo:
        raise ValueError("segment missing vo")
    visual = seg.get("visual") or {}
    if not isinstance(visual, dict):
        visual = {}
    vtype = str(visual.get("type", "image"))
    if vtype not in ("card", "image", "video"):
        vtype = "image"

    repos = repos or []
    primary = _primary_visual_for_repos(repos, topic)
    # Cycle alternates for variety, but never default every segment to courses.
    alternates = [a for a in _CALLIOPE_VISUAL_POOL if a != primary]
    if not any(r.lower() in _COURSE_REPOS for r in repos) and "course" not in topic.lower():
        alternates = [a for a in alternates if a != "course-hero-16x9.png"]
    pool = [primary] + alternates
    fallback = pool[index % len(pool)]

    if vtype == "card" or not str(visual.get("path", "")).strip():
        rel = fallback
    else:
        rel = str(visual.get("path", fallback))
        if ".." in rel or rel.startswith("/"):
            rel = fallback
        rel = Path(rel).name
        if rel not in _CALLIOPE_VISUAL_POOL:
            rel = fallback
        # Reject course / wrong-product heroes even if the LLM picked them.
        rel = coerce_asset_for_repo(rel, repos[0] if repos else "", topic)
        if (
            rel == _COURSE_HERO
            and not any(r.lower() in _COURSE_REPOS for r in repos)
            and "course" not in topic.lower()
            and "academy" not in topic.lower()
        ):
            rel = primary

    safe_visual = {
        "type": "image",
        "path": rel,
        "kenburns": True,
        **({"loop": True} if rel.endswith(".gif") else {}),
    }
    return {"vo": vo, "caption": caption, "visual": safe_visual}


def parse_script(data: dict[str, Any]) -> EpisodeScript:
    segments_raw = data.get("segments") or []
    if not segments_raw:
        raise ValueError("script has no segments")
    title = sanitize_text(str(data.get("title", "Ecosystem update")), max_len=100)
    desc = sanitize_text(str(data.get("description", "")), max_len=4000)
    tags = [sanitize_text(str(t), max_len=40) for t in (data.get("tags") or ["AIAgents", "OpenSource"])][:15]
    topic = sanitize_text(str(data.get("topic", title)), max_len=200)
    repos = [re.sub(r"[^a-zA-Z0-9._-]", "", str(r))[:64] for r in (data.get("repos") or [])][:10]
    segments = [
        _validate_segment(s, index=i, repos=repos, topic=topic)
        for i, s in enumerate(segments_raw[:MAX_SEGMENTS])
    ]
    demo = sanitize_text(str(data.get("demo_url", "")), max_len=300)
    raw_defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    defaults: dict[str, Any] = {
        "voice": str(raw_defaults.get("voice", "Daniel"))[:40] or "Daniel",
        "voice_rate": int(raw_defaults.get("voice_rate", 175) or 175),
        # Short-form VO (40–90s) → YouTube Shorts canvas by default.
        "aspect": str(raw_defaults.get("aspect", "9:16")),
    }
    if defaults["aspect"] not in {"9:16", "shorts", "portrait", "vertical", "16:9", "landscape"}:
        defaults["aspect"] = "9:16"
    if defaults["aspect"] in {"9:16", "shorts", "portrait", "vertical"} and "Shorts" not in tags:
        tags = (tags + ["Shorts"])[:15]
    return EpisodeScript(
        title=title,
        description=desc,
        tags=tags,
        topic=topic,
        repos=repos,
        demo_url=demo,
        segments=segments,
        defaults=defaults,
    )


class Calliope:
    """Ecosystem-grounded screenwriter — reads MNEMOSYNE, writes episode scripts."""

    def __init__(self, cfg: HeliosConfig, store: QueueStore) -> None:
        self.cfg = cfg
        self.store = store
        self.llm = LlmClient(cfg.llm) if cfg.calliope_enabled else None
        mnemo_path = cfg.mnemosyne_path
        self.kb = MnemosyneReader(mnemo_path) if mnemo_path else MnemosyneReader(Path("/nonexistent"))
        self.seasons = parse_seasons(cfg.seasons_raw)

    def active_season(self):
        return current_season(self.seasons)

    def _require_llm(self) -> LlmClient:
        if not self.llm:
            raise RuntimeError("Calliope disabled — set calliope.enabled=true and LLM API key")
        return self.llm

    def _corpus_block(self, query: str, *, k: int = 8, fetch_repos: list[str] | None = None) -> str:
        if not self.kb.chunks:
            base = wrap_corpus(
                "MNEMOSYNE empty — sync DIOSCURI first or set HELIOS_MNEMOSYNE_PATH / DIOSCURI_DATA_DIR.",
                2000,
            )
        else:
            text = self.kb.corpus_for_query(query, k=k)
            demos = self.kb.repos_with_demos()
            if demos:
                demo_lines = "\n".join(f"- {repo}: {url}" for repo, url in sorted(demos.items())[:20])
                text += f"\n\nLive demo URLs:\n{demo_lines}"
            base = wrap_corpus(text, 9000)
        fetched = corpus_from_fetch(self.cfg.data_dir, repos=fetch_repos, max_chars=5000)
        if fetched:
            return base + "\n\n# Freshly fetched GitHub (Helios)\n" + wrap_corpus(fetched, 5000)
        return base

    def refresh_github(self, *, repos: list[str] | None = None) -> dict[str, Any]:
        """Fetch README + latest release for allowlisted / season repos."""
        if not self.cfg.github_fetch_enabled:
            return {"ok": False, "reason": "github_fetch_disabled", "results": []}
        season = self.active_season()
        allow = list(self.cfg.repos_allowlist) or list(self.kb.list_repos() if self.kb.chunks else [])
        focus = list(repos) if repos else []
        if not focus and season:
            focus = list(season.repos)
        if not focus:
            focus = allow[:12]
        # Prefer season/focus, then fill from allowlist.
        ordered: list[str] = []
        for r in focus + allow:
            if r and r not in ordered:
                ordered.append(r)
        results = fetch_allowlist(
            owner=self.cfg.github_owner,
            repos=ordered[:15],
            data_dir=self.cfg.data_dir,
        )
        return {
            "ok": True,
            "season": season.id if season else None,
            "fetched": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "results": [{"repo": r.repo, "ok": r.ok, "chars": r.chars, "error": r.error} for r in results],
        }

    def pitch(self, *, query: str | None = None) -> list[Pitch]:
        llm = self._require_llm()
        q = query or "ecosystem updates releases demos open source AI agents"
        corpus = self._corpus_block(q, k=10)
        recent = self.kb.recent_releases(limit=5)
        release_hint = "\n".join(f"- {c.title}: {c.text[:200]}" for c in recent) or "(no recent releases in KB)"
        user = wrap_user(
            f"Suggest 5 video topics.\nOptional focus: {q}\n\nRecent releases:\n{release_hint}",
            3000,
        )
        result = llm.json_chat([
            {"role": "system", "content": PITCH_SYSTEM + "\n\n" + corpus},
            {"role": "user", "content": user},
        ])
        pitches: list[Pitch] = []
        for p in result.get("pitches") or []:
            if not isinstance(p, dict):
                continue
            pitches.append(Pitch(
                topic=sanitize_text(str(p.get("topic", "")), max_len=120),
                hook=sanitize_text(str(p.get("hook", "")), max_len=300),
                repos=[str(r) for r in (p.get("repos") or [])][:5],
                query=sanitize_text(str(p.get("query", p.get("topic", ""))), max_len=200),
                priority=int(p.get("priority", 50)),
            ))
        pitches.sort(key=lambda x: x.priority, reverse=True)
        return pitches

    def _editorial_context(self) -> dict[str, Any]:
        """Repos in KB vs already published / queued — for scout dedup."""
        published = sorted(self.store.load_upload_state().get("videos", {}).keys())
        queued_topics: list[str] = []
        queued_repos: list[str] = []
        for job in self.store.list_jobs():
            t = job.vars.get("topic")
            if t:
                queued_topics.append(t)
            for r in job.youtube.get("tags") or []:
                if r in (self.kb.list_repos() if self.kb.chunks else []):
                    queued_repos.append(str(r))
        return {
            "repos_in_kb": self.kb.list_repos(),
            "repos_with_demos": self.kb.repos_with_demos(),
            "published_episodes": published,
            "queued_topics": queued_topics,
            "pending_jobs": self.store.pending_count(),
        }

    def scout(self, *, limit: int = 5) -> list[Pitch]:
        """Editorial scout — seasonal themes + evergreen ideas across the ecosystem."""
        llm = self._require_llm()
        ctx = self._editorial_context()
        if not ctx["repos_in_kb"]:
            raise RuntimeError("MNEMOSYNE empty — start DIOSCURI KB sync first")

        season = self.active_season()
        season_block = season.prompt_block() if season else "CURRENT SEASON: (none configured — pick the best ecosystem story)."
        focus_repos = list(season.repos) if season else []
        query = (
            " ".join(season.themes + season.repos)
            if season
            else "alexar76 ecosystem AI agents MCP security oracles monitor factory open source"
        )
        corpus = self._corpus_block(query, k=12, fetch_repos=focus_repos or None)
        inventory_lines: list[str] = []
        for repo in ctx["repos_in_kb"]:
            demo = ctx["repos_with_demos"].get(repo, "")
            digest = self.kb.repo_summary(repo, max_chunks=2)[:300]
            mark = " ★season" if repo in focus_repos else ""
            inventory_lines.append(
                f"- {repo}{mark}" + (f" demo={demo}" if demo else "") + f": {digest[:120]}…"
            )

        system = SCOUT_SYSTEM.replace("{limit}", str(limit))
        user = wrap_user(
            "Plan the next YouTube episodes for the channel.\n\n"
            + season_block
            + f"\n\nRepos in knowledge base ({len(ctx['repos_in_kb'])}):\n"
            + "\n".join(inventory_lines[:40])
            + f"\n\nAlready published episodes: {', '.join(ctx['published_episodes']) or '(none in HELIOS state)'}"
            + f"\nAlready queued topics: {', '.join(ctx['queued_topics']) or '(none)'}"
            + "\n\nFind gaps — season themes first, then under-covered repos. Skip bare release recaps.",
            5500,
        )
        result = llm.json_chat([
            {"role": "system", "content": system + "\n\n# Ecosystem corpus\n" + corpus},
            {"role": "user", "content": user},
        ])
        pitches: list[Pitch] = []
        for p in result.get("pitches") or []:
            if not isinstance(p, dict):
                continue
            pitches.append(Pitch(
                topic=sanitize_text(str(p.get("topic", "")), max_len=120),
                hook=sanitize_text(str(p.get("hook", "")), max_len=300),
                repos=[str(r) for r in (p.get("repos") or [])][:5],
                query=sanitize_text(str(p.get("query", p.get("topic", ""))), max_len=200),
                priority=int(p.get("priority", 50)),
            ))
        pitches.sort(key=lambda x: x.priority, reverse=True)

        editorial = self.cfg.data_dir / "editorial"
        editorial.mkdir(parents=True, exist_ok=True)
        log_path = editorial / "scout_log.jsonl"
        entry = {
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "season": season.id if season else None,
            "pitches": [p.__dict__ for p in pitches[:limit]],
            "context": {k: v for k, v in ctx.items() if k != "repos_with_demos"},
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return pitches[:limit]

    def scout_and_enqueue(self, *, top: int = 1, pitches: list[Pitch] | None = None) -> list[str]:
        """Scout ideas, write script + enqueue the top N (private until approve)."""
        ideas = pitches or self.scout(limit=max(top, self.cfg.calliope_scout_ideas_per_run))
        job_ids: list[str] = []
        for p in ideas[:top]:
            repo = p.repos[0] if p.repos else None
            script = self.write(topic=p.topic, query=p.query, repo=repo)
            job_ids.append(self.enqueue(script, source="calliope-scout"))
        return job_ids

    def _editorial_dir(self) -> Path:
        p = self.cfg.data_dir / "editorial"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _editorial_state_path(self) -> Path:
        return self._editorial_dir() / "state.json"

    def _load_editorial_state(self) -> dict[str, Any]:
        path = self._editorial_state_path()
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _save_editorial_state(self, state: dict[str, Any]) -> None:
        self._editorial_state_path().write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _iso_week_key(d: date | None = None) -> str:
        d = d or date.today()
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    @staticmethod
    def _days_since(iso_ts: str | None) -> float | None:
        if not iso_ts:
            return None
        try:
            dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
        except ValueError:
            return None

    def _pending_backfill_count(self) -> int:
        return sum(1 for j in self.store.list_jobs(status="pending") if j.phase == "backfill")

    def editorial_status(self) -> dict[str, Any]:
        """Operator view — quota, interval, pause reasons (no LLM)."""
        state = self._load_editorial_state()
        week = self._iso_week_key()
        enqueued_this_week = (
            int(state.get("enqueued_this_week", 0))
            if state.get("week_key") == week
            else 0
        )
        quota_left = max(0, self.cfg.calliope_weekly_enqueue_quota - enqueued_this_week)
        days = self._days_since(state.get("last_scout_at"))
        interval = self.cfg.calliope_scout_interval_days
        backfill_n = self._pending_backfill_count()
        due = days is None or days >= interval
        paused = backfill_n > self.cfg.calliope_backfill_pause_threshold
        return {
            "enabled": self.cfg.calliope_enabled and self.cfg.calliope_editorial_enabled,
            "week_key": week,
            "enqueued_this_week": enqueued_this_week,
            "weekly_quota": self.cfg.calliope_weekly_enqueue_quota,
            "quota_left": quota_left,
            "last_scout_at": state.get("last_scout_at"),
            "days_since_scout": round(days, 1) if days is not None else None,
            "scout_interval_days": interval,
            "scout_due": due and not paused,
            "pending_backfill": backfill_n,
            "backfill_pause_threshold": self.cfg.calliope_backfill_pause_threshold,
            "paused_for_backfill": paused,
            "auto_enqueue_per_run": self.cfg.calliope_auto_enqueue_per_run,
            "repos_in_kb": len(self.kb.list_repos()) if self.kb.chunks else 0,
            "season": None if not self.active_season() else {
                "id": self.active_season().id,
                "title": self.active_season().title,
                "themes": self.active_season().themes,
                "repos": self.active_season().repos,
            },
            "accept_release_shorts": self.cfg.accept_release_shorts,
            "github_fetch": self.cfg.github_fetch_enabled,
        }

    def run_editorial_if_due(self, *, force: bool = False) -> dict[str, Any]:
        """Scout on interval; enqueue up to weekly quota (growth-optimized steady state)."""
        result: dict[str, Any] = {"action": "skipped", "reason": ""}

        if not self.cfg.calliope_enabled:
            result["reason"] = "calliope_disabled"
            return result
        if not self.cfg.calliope_editorial_enabled:
            result["reason"] = "editorial_disabled"
            return result
        if self.cfg.dry_run and not force:
            result["reason"] = "dry_run"
            return result

        backfill_n = self._pending_backfill_count()
        if backfill_n > self.cfg.calliope_backfill_pause_threshold:
            result["reason"] = f"backfill_pause:{backfill_n}>{self.cfg.calliope_backfill_pause_threshold}"
            return result

        if not self.kb.chunks:
            result["reason"] = "mnemosyne_empty"
            return result

        state = self._load_editorial_state()
        week = self._iso_week_key()
        enqueued_this_week = (
            int(state.get("enqueued_this_week", 0))
            if state.get("week_key") == week
            else 0
        )
        quota_left = max(0, self.cfg.calliope_weekly_enqueue_quota - enqueued_this_week)

        days = self._days_since(state.get("last_scout_at"))
        interval = self.cfg.calliope_scout_interval_days
        if not force and days is not None and days < interval:
            result["reason"] = f"interval:{days:.1f}/{interval}d"
            return result

        try:
            if self.cfg.github_fetch_enabled:
                fetch_info = self.refresh_github()
                result["fetch"] = {
                    "fetched": fetch_info.get("fetched"),
                    "failed": fetch_info.get("failed"),
                    "season": fetch_info.get("season"),
                }
            pitches = self.scout(limit=self.cfg.calliope_scout_ideas_per_run)
        except Exception as exc:
            result["action"] = "error"
            result["reason"] = str(exc)
            return result

        state["last_scout_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_pitch_count"] = len(pitches)
        state["week_key"] = week
        season = self.active_season()
        if season:
            state["season_id"] = season.id

        job_ids: list[str] = []
        if quota_left > 0:
            enqueue_n = min(self.cfg.calliope_auto_enqueue_per_run, quota_left)
            for p in pitches[:enqueue_n]:
                repo = p.repos[0] if p.repos else None
                script = self.write(topic=p.topic, query=p.query, repo=repo)
                job_ids.append(self.enqueue(script, source="calliope-editorial"))
            enqueued_this_week += len(job_ids)
            state["enqueued_this_week"] = enqueued_this_week

        self._save_editorial_state(state)
        result["action"] = "enqueued" if job_ids else "scout_only"
        result["pitches"] = len(pitches)
        result["job_ids"] = job_ids
        result["season"] = season.id if season else None
        result["enqueued_this_week"] = enqueued_this_week
        result["quota_left"] = max(0, self.cfg.calliope_weekly_enqueue_quota - enqueued_this_week)
        return result

    def write(self, *, topic: str, query: str | None = None, repo: str | None = None) -> EpisodeScript:
        llm = self._require_llm()
        search_q = query or topic
        if repo:
            search_q = f"{repo} {search_q}"
        corpus = self._corpus_block(search_q, k=8)
        demo_url = self.kb.repos_with_demos().get(repo or "", "") if repo else ""
        user = wrap_user(
            f"Write a short YouTube episode script.\nTopic: {topic}\n"
            + (f"Focus repo: {repo}\n" if repo else "")
            + (f"Demo URL to mention if relevant: {demo_url}\n" if demo_url else ""),
            2000,
        )
        try:
            result = llm.json_chat([
                {"role": "system", "content": CALLIOPE_SYSTEM + "\n\n# Ecosystem reference\n" + corpus},
                {"role": "user", "content": user},
            ])
        except LlmBudgetExceeded as exc:
            raise RuntimeError("LLM daily budget exceeded") from exc
        if repo and not result.get("repos"):
            result["repos"] = [repo]
        if demo_url and not result.get("demo_url"):
            result["demo_url"] = demo_url
        return parse_script(result)

    def save_script(self, script: EpisodeScript) -> Path:
        sid = f"calliope_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid4().hex[:8]}"
        path = self.cfg.data_dir / "scripts" / f"{sid}.yaml"
        script.save(path)
        return path

    def enqueue(
        self,
        script: EpisodeScript,
        *,
        script_path: Path | None = None,
        source: str = "calliope",
    ) -> str:
        validate_template_id("calliope-episode")
        path = script_path or self.save_script(script)
        slug = re.sub(r"[^a-z0-9]+", "-", script.topic.lower())[:40].strip("-") or "episode"
        ikey = f"calliope:{slug}:{path.stem}"
        desc = script.description
        if script.demo_url and script.demo_url not in desc:
            desc = f"{desc}\n\nLive demo: {script.demo_url}".strip()
        job = self.store.enqueue(
            template="calliope-episode",
            vars={"topic": script.topic, "script_id": path.stem},
            youtube={
                "title": script.title,
                "description": desc,
                "tags": script.tags,
                "privacy": "private",
            },
            idempotency_key=ikey,
            source=source,
            script_path=str(path),
            phase="creator",
        )
        return job.id
