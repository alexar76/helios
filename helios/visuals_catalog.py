"""Per-repo product visuals — never show Factory UI over oracles/twins/courses."""

from __future__ import annotations

# Basename-only assets under HELIOS asset_roots.
COURSE = "course-hero-16x9.png"
FACTORY = "hero-demo-preview.gif"  # Magic AI-Factory dashboard ONLY
MONITOR = "alien-monitor-hero.gif"
LANDING = "aicom-landing-hero.gif"
PULSE = "pulse-floor.png"
PLATON = "platon-umbral-hero.gif"
PLATON_STILL = "platon-cosmos.png"

# Back-compat alias used in older prompts/tests
ORCHESTRATION = FACTORY

# (motion_or_hero, still) — still used for Ken Burns mid-segment on release-shorts.
_REPO: dict[str, tuple[str, str]] = {
    "aimarket-courses": (COURSE, COURSE),
    "aicom-landing": (MONITOR, MONITOR),
    "alien-monitor": (MONITOR, MONITOR),
    "aicom": (MONITOR, MONITOR),
    "metis": (MONITOR, MONITOR),
    "skopos": (MONITOR, MONITOR),
    "acex": (PULSE, PULSE),
    "pulse-terminal": (PULSE, PULSE),
    # Factory dashboard — only products that ARE the factory UI.
    "aimarket-hub": (FACTORY, FACTORY),
    "aimarket-protocol": (FACTORY, FACTORY),
    "aimarket-agent": (FACTORY, FACTORY),
    "argus": (FACTORY, FACTORY),
    "aimarket-mcp": (FACTORY, FACTORY),
    "aimarket-oracle-gateway": (MONITOR, MONITOR),
    # Oracles — NEVER factory dashboard.
    "oracles": (PLATON, PLATON_STILL),
    "platon": (PLATON, PLATON_STILL),
    "gaia": (PLATON, PLATON_STILL),
    "chronos": (PLATON, PLATON_STILL),
    "fermat": (PLATON, PLATON_STILL),
    "colony": (PLATON, PLATON_STILL),
    "murmuration": (PLATON, PLATON_STILL),
    "ablation": (PLATON, PLATON_STILL),
    "landauer": (PLATON, PLATON_STILL),
    # Twins / canon / broadcast — not courses, not the factory dashboard.
    "dioscuri": (MONITOR, MONITOR),
    "theoros": (MONITOR, MONITOR),
    "helios": (MONITOR, MONITOR),
}

# Assets that are product-specific and must not be used as "generic".
_COURSE_ONLY = frozenset({COURSE})
_FACTORY_ONLY_REPOS = frozenset({
    "aimarket-hub", "aimarket-protocol", "aimarket-agent", "argus", "aimarket-mcp",
})
_POOL = (FACTORY, MONITOR, LANDING, PULSE, COURSE, PLATON, PLATON_STILL)

_ORACLE_TOPIC = (
    "platon", "oracle", "vrf", "chaos", "random", "witness", "umbral",
    "chronos", "fermat", "colony", "murmuration", "ablation", "landauer",
    "gaia", "verifiable",
)


def normalize_repo(repo: str) -> str:
    return (repo or "").strip().split("/")[-1].lower()


def visuals_for_repo(repo: str) -> tuple[str, str]:
    """Return (hero_motion, still) basenames for a satellite repo."""
    key = normalize_repo(repo)
    if key in _REPO:
        return _REPO[key]
    # Unknown satellite: ecosystem map beats courses/factory mismatch.
    return (MONITOR, MONITOR)


def primary_visual(repo: str = "", topic: str = "") -> str:
    """Single still/gif for Calliope segments."""
    lowered = (topic or "").lower()
    key = normalize_repo(repo)
    if key:
        return visuals_for_repo(key)[0]
    if any(w in lowered for w in ("course", "academy", "colab", "certificate")):
        return COURSE
    if any(w in lowered for w in _ORACLE_TOPIC):
        return PLATON
    if any(w in lowered for w in ("pulse", "acex", "capshare", "pricing")):
        return PULSE
    if any(w in lowered for w in ("monitor", "universe", "ecosystem map", "3d")):
        return MONITOR
    if any(w in lowered for w in ("landing", "npx", "theoros", "canon", "dioscuri", "twin")):
        return LANDING
    if any(w in lowered for w in ("factory", "pipeline", "storefront", "orchestration")):
        return FACTORY
    return MONITOR


def coerce_asset_for_repo(path: str, repo: str, topic: str = "") -> str:
    """Rewrite a hard-coded wrong asset (e.g. factory GIF on Platon / courses on dioscuri)."""
    name = path.rsplit("/", 1)[-1]
    # Unresolved template braces → treat as empty.
    if not name or name.startswith("{") or "{" in name:
        name = ""
    key = normalize_repo(repo)
    hero, still = visuals_for_repo(key) if key else (primary_visual("", topic), primary_visual("", topic))
    if not key and topic:
        hero = still = primary_visual("", topic)

    # Courses asset only for courses.
    if name in _COURSE_ONLY:
        if key == "aimarket-courses" or any(w in (topic or "").lower() for w in ("course", "academy")):
            return name
        return still

    # Factory dashboard ONLY for factory-ish repos — never oracles/twins/monitor.
    if name == FACTORY:
        if key in _FACTORY_ONLY_REPOS:
            return name
        if not key and any(w in (topic or "").lower() for w in ("factory", "pipeline", "storefront")):
            return name
        return hero

    # Platon/oracle stills are fine for oracle family; don't force-rewrite.
    if name in {PLATON, PLATON_STILL, "platon-main-view.png"}:
        return name

    return name if name else hero


def visual_pool(*, allow_courses: bool) -> tuple[str, ...]:
    if allow_courses:
        return _POOL
    return tuple(a for a in _POOL if a not in _COURSE_ONLY)
