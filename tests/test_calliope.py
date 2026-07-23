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
