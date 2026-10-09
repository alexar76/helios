"""Per-repo visuals — courses/Factory must not leak onto oracles/twins."""

from __future__ import annotations

from helios.visuals_catalog import (
    FACTORY,
    PLATON,
    coerce_asset_for_repo,
    primary_visual,
    visuals_for_repo,
)


def test_dioscuri_not_courses() -> None:
    hero, still = visuals_for_repo("dioscuri")
    assert "course" not in hero
    assert hero != FACTORY


def test_courses_keep_course_hero() -> None:
    hero, still = visuals_for_repo("aimarket-courses")
    assert hero == "course-hero-16x9.png"
    assert still == "course-hero-16x9.png"


def test_platon_not_factory() -> None:
    hero, still = visuals_for_repo("platon")
    assert hero == PLATON
    assert still == "platon-cosmos.png"
    assert hero != FACTORY
    assert still != FACTORY


def test_oracles_not_factory() -> None:
    hero, _ = visuals_for_repo("oracles")
    assert hero == PLATON
    assert hero != FACTORY


def test_coerce_rewrites_factory_on_platon() -> None:
    assert coerce_asset_for_repo("hero-demo-preview.gif", "platon") == PLATON
    assert coerce_asset_for_repo("hero-demo-preview.gif", "oracles") == PLATON
    assert coerce_asset_for_repo("hero-demo-preview.gif", "dioscuri") != FACTORY
    assert coerce_asset_for_repo("course-hero-16x9.png", "theoros") != "course-hero-16x9.png"
    assert coerce_asset_for_repo("course-hero-16x9.png", "aimarket-courses") == "course-hero-16x9.png"


def test_coerce_keeps_factory_for_hub() -> None:
    assert coerce_asset_for_repo("hero-demo-preview.gif", "aimarket-hub") == FACTORY
    assert coerce_asset_for_repo("hero-demo-preview.gif", "argus") == FACTORY


def test_topic_platon_without_repo() -> None:
    assert primary_visual("", "Platon 32D chaos VRF") == PLATON
    assert primary_visual("", "Factory pipeline storefront") == FACTORY
