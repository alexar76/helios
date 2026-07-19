"""Queue script_path validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from helios.queue import QueueStore


def test_enqueue_calliope_script_path(tmp_path: Path) -> None:
    data = tmp_path / "data"
    scripts = data / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "calliope_test.yaml"
    script.write_text("id: calliope-episode\nsegments: []\n", encoding="utf-8")
    store = QueueStore(data, file_roots=[])
    job = store.enqueue(
        template="calliope-episode",
        vars={"topic": "test", "script_id": "calliope_test"},
        script_path=str(script),
        phase="creator",
        idempotency_key="calliope:test:1",
    )
    assert job.script_path == str(script.resolve())
    assert job.phase == "creator"


def test_enqueue_rejects_script_outside_data(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    evil = tmp_path / "evil.yaml"
    evil.write_text("x", encoding="utf-8")
    store = QueueStore(data, file_roots=[])
    with pytest.raises(ValueError, match="data/scripts"):
        store.enqueue(
            template="calliope-episode",
            script_path=str(evil),
            idempotency_key="calliope:evil:1",
        )
