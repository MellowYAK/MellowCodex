"""Regression: local repair tests must not reuse stale bytecode across revisions."""
import asyncio
import os
import time

from hub.development.runner import run_pytest


def test_separate_pytest_runs_never_share_stale_pycache(tmp_path):
    source = tmp_path / "a.py"
    case = tmp_path / "test_a.py"
    source.write_text("value=1", encoding="utf-8")
    case.write_text("from a import value\ndef test_value(): assert value == 2", encoding="utf-8")
    # Same timestamp and byte length intentionally reproduce the observed
    # pre-existing run_pytest bytecode cache collision.
    old_second = int(time.time()) - 10
    os.utime(source, (old_second, old_second))
    first = asyncio.run(run_pytest(tmp_path, ["test_a.py"], 30))
    assert first["exit_code"] != 0
    source.write_text("value=2", encoding="utf-8")
    os.utime(source, (old_second, old_second))
    second = asyncio.run(run_pytest(tmp_path, ["test_a.py"], 30))
    assert second["exit_code"] == 0, second["output"]
