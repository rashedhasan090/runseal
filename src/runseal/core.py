"""Core sealing and verification logic for runseal."""
from __future__ import annotations
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runseal.hashutil import canonical_json, seal_id_for, sha256_bytes, sha256_file

__all__ = [
    "canonical_json",
    "collect_env",
    "run_and_seal",
    "seal_id_for",
    "track_files",
    "verify_receipt",
]

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def track_files(paths: list[str], cwd: Path) -> list[dict[str, Any]]:
    tracked: list[dict[str, Any]] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = cwd / p
        p = p.resolve()
        if not p.is_file():
            raise FileNotFoundError(f"tracked path is not a file: {p}")
        digest, size = sha256_file(p)
        try:
            rel = str(p.relative_to(cwd))
        except ValueError:
            rel = str(p)
        tracked.append({"path": rel, "sha256": digest, "size": size})
    tracked.sort(key=lambda x: x["path"])
    return tracked

def collect_env(keys: list[str]) -> dict[str, str | None]:
    return {k: os.environ.get(k) for k in sorted(set(keys))}

def run_and_seal(
    argv: list[str],
    *,
    label: str | None = None,
    track: list[str] | None = None,
    env_keys: list[str] | None = None,
    store_output: bool = False,
    outdir: Path | None = None,
    capture_limit: int = 64_000,
) -> dict[str, Any]:
    if not argv:
        raise ValueError("command argv must be non-empty")
    cwd = Path.cwd().resolve()
    outdir = (outdir or (cwd / ".runseals")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tracked = track_files(track or [], cwd)
    env_snapshot = collect_env(env_keys or [])
    started = time.perf_counter()
    started_at = _utc_now()
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=False, check=False)
    finished_at = _utc_now()
    duration_ms = int(round((time.perf_counter() - started) * 1000))
    stdout, stderr = proc.stdout or b"", proc.stderr or b""
    for fd, blob in ((1, stdout), (2, stderr)):
        if blob:
            try:
                os.write(fd, blob)
            except OSError:
                pass
    receipt: dict[str, Any] = {
        "schema": "runseal/v1",
        "label": label,
        "command": argv,
        "cwd": str(cwd),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "exit_code": int(proc.returncode),
        "tracked_files": tracked,
        "env": env_snapshot,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
    }
    if store_output:
        receipt["stdout_preview"] = stdout[:capture_limit].decode("utf-8", errors="replace")
        receipt["stderr_preview"] = stderr[:capture_limit].decode("utf-8", errors="replace")
        receipt["output_truncated"] = len(stdout) > capture_limit or len(stderr) > capture_limit
    receipt["seal_id"] = seal_id_for(receipt)
    path = outdir / f"{receipt['seal_id'][:16]}.json"
    path.write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    receipt["_written_to"] = str(path)
    return receipt

def verify_receipt(path: Path) -> tuple[bool, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    if data.get("schema") != "runseal/v1":
        problems.append(f"unexpected schema: {data.get('schema')!r}")
    if data.get("seal_id") != seal_id_for(data):
        problems.append("seal_id mismatch (receipt was altered)")
    cwd = Path(data.get("cwd") or Path.cwd())
    for item in data.get("tracked_files") or []:
        rel, expected = item.get("path"), item.get("sha256")
        if not rel or not expected:
            problems.append("tracked_files entry missing path/sha256")
            continue
        p = Path(rel) if Path(rel).is_absolute() else cwd / rel
        if not p.is_file():
            problems.append(f"missing tracked file: {rel}")
            continue
        digest, _ = sha256_file(p)
        if digest != expected:
            problems.append(f"hash drift for {rel}")
    return (len(problems) == 0), problems
