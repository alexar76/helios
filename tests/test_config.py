"""Config and file_roots tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from helios.config import file_roots, load_config


def test_file_roots_includes_promo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "helios.config.yaml"
    promo = tmp_path / "PromoMaterials"
    promo.mkdir()
    cfg_path.write_text(f"""
promo_materials_dir: {promo}
asset_roots:
  - {tmp_path / "assets"}
""")
    monkeypatch.setenv("HELIOS_CONFIG", str(cfg_path))
    monkeypatch.setenv("HELIOS_DATA_DIR", str(tmp_path / "data"))
    cfg = load_config()
    roots = file_roots(cfg)
    assert promo.resolve() in roots


def test_load_config_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HELIOS_DRY_RUN", "1")
    monkeypatch.setenv("HELIOS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HELIOS_CONFIG", str(tmp_path / "missing.yaml"))
    cfg = load_config()
    assert cfg.dry_run is True
