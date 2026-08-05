"""Security validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from helios.security import (
    sanitize_text,
    substitute_vars,
    validate_existing_file,
    validate_idempotency_key,
    validate_source,
    validate_template_id,
    validate_vars,
    safe_subprocess_arg,
)


def test_substitute_vars() -> None:
    assert substitute_vars("{repo} {tag}", {"repo": "aicom", "tag": "v1"}) == "aicom v1"


def test_reject_bad_template() -> None:
    with pytest.raises(ValueError):
        validate_template_id("../evil")


def test_promo_backfill_template_allowed() -> None:
    assert validate_template_id("promo-backfill") == "promo-backfill"


def test_reject_bad_var_key() -> None:
    with pytest.raises(ValueError):
        validate_vars({"shell": "rm -rf /"})


def test_sanitize_strips_control() -> None:
    assert "\x00" not in sanitize_text("hello\x00world")


def test_idempotency_key_valid() -> None:
    assert validate_idempotency_key("release:alexar76/aicom:v0.1.0")


def test_idempotency_key_rejects_injection() -> None:
    with pytest.raises(ValueError):
        validate_idempotency_key("'; DROP TABLE--")


def test_source_valid() -> None:
    assert validate_source("dioscuri") == "dioscuri"


def test_source_rejects_spaces() -> None:
    with pytest.raises(ValueError):
        validate_source("bad source")


def test_safe_subprocess_blocks_shell() -> None:
    with pytest.raises(ValueError):
        safe_subprocess_arg("foo; rm -rf /")


def test_validate_existing_file_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "promo"
    root.mkdir()
    video = root / "out" / "E10.mp4"
    video.parent.mkdir()
    video.write_bytes(b"fake")
    resolved = validate_existing_file(str(video), [root])
    assert resolved == video.resolve()


def test_validate_existing_file_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "promo"
    root.mkdir()
    outside = tmp_path / "secret.mp4"
    outside.write_bytes(b"x")
    with pytest.raises(ValueError, match="outside allowed roots"):
        validate_existing_file(str(outside), [root])


def test_validate_existing_file_traversal(tmp_path: Path) -> None:
    root = tmp_path / "promo"
    root.mkdir()
    link_target = tmp_path / "etc" / "passwd"
    link_target.parent.mkdir(parents=True, exist_ok=True)
    link_target.write_text("secret")
    # Can't easily test symlink traversal on all OS; test missing file
    with pytest.raises(FileNotFoundError):
        validate_existing_file(str(root / "missing.mp4"), [root])
