"""CALLIOPE script parsing tests."""

from __future__ import annotations

import pytest

from helios.calliope import parse_script


def test_parse_script_valid() -> None:
    data = {
        "title": "ARGUS agent demo",
        "description": "Open source personal agent.",
        "tags": ["AIAgents"],
        "topic": "ARGUS overview",
        "repos": ["argus"],
        "demo_url": "https://magic-ai-factory.com/argus/",
        "segments": [
            {
                "vo": "Meet ARGUS — your personal agent with a WARDEN firewall.",
                "caption": "ARGUS",
                "visual": {"type": "card", "color": "#0b0e17", "text": "ARGUS"},
            },
            {
                "vo": "Try the live demo on magic-ai-factory.com.",
                "caption": "LIVE DEMO",
                "visual": {"type": "card", "color": "#0b0e17", "text": "DEMO"},
            },
        ],
    }
    script = parse_script(data)
    assert script.title == "ARGUS agent demo"
    assert len(script.segments) == 2
    assert script.segments[0]["caption"] == "ARGUS"
    assert script.defaults["aspect"] == "9:16"
    assert "Shorts" in script.tags
    # Black cards are rewritten to product visuals (Ken Burns image/gif).
    assert script.segments[0]["visual"]["type"] == "image"
    assert script.segments[0]["visual"]["path"].endswith((".png", ".gif"))


def test_parse_script_rejects_empty_segments() -> None:
    with pytest.raises(ValueError, match="no segments"):
        parse_script({"title": "x", "segments": []})


def test_parse_script_sanitizes_visual_path() -> None:
    data = {
        "title": "t",
        "segments": [
            {
                "vo": "Hello world from the ecosystem.",
                "visual": {"type": "image", "path": "/etc/passwd"},
            },
        ],
    }
    script = parse_script(data)
    assert ".." not in script.segments[0]["visual"]["path"]
    assert not script.segments[0]["visual"]["path"].startswith("/")
    assert script.segments[0]["visual"]["path"] in {
        "hero-demo-preview.gif",
        "course-hero-16x9.png",
        "alien-monitor-hero.gif",
        "aicom-landing-hero.gif",
        "pulse-floor.png",
        "platon-umbral-hero.gif",
        "platon-cosmos.png",
        "platon-main-view.png",
    }


def test_parse_script_rejects_factory_gif_on_platon() -> None:
    data = {
        "title": "Platon: The 32D Chaos Oracle",
        "topic": "Platon chaos VRF verifiable randomness",
        "repos": ["platon", "oracles"],
        "segments": [
            {
                "vo": "Platon returns signed chaos-VRF anyone can verify offline.",
                "visual": {"type": "image", "path": "hero-demo-preview.gif"},
            },
        ],
    }
    script = parse_script(data)
    assert script.segments[0]["visual"]["path"] == "platon-umbral-hero.gif"
    assert script.segments[0]["visual"]["path"] != "hero-demo-preview.gif"


def test_parse_script_rejects_course_hero_on_acex_topic() -> None:
    data = {
        "title": "ACEX Pulse Terminal: Live Agent Pricing",
        "topic": "ACEX Pulse Terminal live pricing and proof-of-audit",
        "repos": ["acex", "pulse-terminal"],
        "segments": [
            {
                "vo": "Watch live agent pricing on the Pulse Terminal.",
                "visual": {"type": "image", "path": "course-hero-16x9.png"},
            },
            {
                "vo": "CapShare NAV and proof-of-audit on the floor.",
                "visual": {"type": "image", "path": "course-hero-16x9.png"},
            },
        ],
    }
    script = parse_script(data)
    paths = [s["visual"]["path"] for s in script.segments]
    assert "course-hero-16x9.png" not in paths
    assert paths[0] == "pulse-floor.png"


def test_parse_script_keeps_course_hero_for_courses() -> None:
    data = {
        "title": "Free AI Agent Economy Courses",
        "topic": "aimarket-courses academies",
        "repos": ["aimarket-courses"],
        "segments": [
            {
                "vo": "Ten open academies with Colab labs.",
                "visual": {"type": "image", "path": "course-hero-16x9.png"},
            },
        ],
    }
    script = parse_script(data)
    assert script.segments[0]["visual"]["path"] == "course-hero-16x9.png"