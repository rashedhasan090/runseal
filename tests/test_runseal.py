from __future__ import annotations

import json
import sys
from pathlib import Path

from runseal.core import run_and_seal, seal_id_for, verify_receipt
from runseal.cli import main


def test_run_and_verify(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracked = tmp_path / "input.txt"
    tracked.write_text("alpha\n", encoding="utf-8")

    receipt = run_and_seal(
        [sys.executable, "-c", "print(open('input.txt').read().strip())"],
        label="unit",
        track=["input.txt"],
        store_output=True,
        outdir=tmp_path / "seals",
    )
    assert receipt["exit_code"] == 0
    assert receipt["label"] == "unit"
    assert receipt["tracked_files"][0]["sha256"]
    assert receipt["stdout_sha256"]
    assert seal_id_for(receipt) == receipt["seal_id"]

    path = Path(receipt["_written_to"])
    ok, problems = verify_receipt(path)
    assert ok, problems

    data = json.loads(path.read_text(encoding="utf-8"))
    data["exit_code"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    ok, problems = verify_receipt(path)
    assert not ok
    assert any("seal_id" in p for p in problems)


def test_cli_run_and_verify(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "f.txt").write_text("x\n", encoding="utf-8")
    code = main(
        ["run", "--label", "cli", "--track", "f.txt", "--", sys.executable, "-c", "print(1)"]
    )
    assert code == 0
    seals = list((tmp_path / ".runseals").glob("*.json"))
    assert len(seals) == 1
    assert main(["verify", str(seals[0])]) == 0


def test_hash_drift_detected(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracked = tmp_path / "input.txt"
    tracked.write_text("one\n", encoding="utf-8")
    receipt = run_and_seal(
        [sys.executable, "-c", "print(0)"],
        track=["input.txt"],
        outdir=tmp_path / "seals",
    )
    path = Path(receipt["_written_to"])
    tracked.write_text("two\n", encoding="utf-8")
    ok, problems = verify_receipt(path)
    assert not ok
    assert any("hash drift" in p for p in problems)
