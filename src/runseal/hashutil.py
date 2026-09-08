"""Hashing helpers for runseal."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> tuple[str, int]:
    h, size = hashlib.sha256(), 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def seal_id_for(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "seal_id" and not str(k).startswith("_")}
    return sha256_bytes(canonical_json(body).encode("utf-8"))
