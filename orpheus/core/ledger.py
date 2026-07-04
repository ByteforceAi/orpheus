"""Provenance Ledger — append-only record of every step in a run.

This is the backbone of ORPHEUS's transparency guarantee (proposal §5): every
agent action logs its model, mode, seed, inputs, and outputs. In demo/본선 the UI
renders this as a reasoning graph. Here it is written as JSON-lines to
`artifacts/<run_id>/ledger.jsonl` and mirrored to an in-memory list.
"""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, run_id: str | None, artifact_dir: Path, model: str, online: bool, seed: int):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.model = model
        self.mode = "online-llm" if online else "offline-deterministic"
        self.seed = seed
        self.records: list[dict] = []
        self.dir = artifact_dir / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "ledger.jsonl"
        # start fresh
        self.path.write_text("", encoding="utf-8")

    def log(self, iteration: int, agent: str, action: str,
            inputs: Any = None, outputs: Any = None, note: str = "") -> None:
        rec = {
            "ts": round(time.time(), 3),
            "run_id": self.run_id,
            "iteration": iteration,
            "agent": agent,
            "action": action,
            "model": self.model,
            "mode": self.mode,
            "seed": self.seed,
            "inputs": _summ(inputs),
            "outputs": _summ(outputs),
            "note": note,
        }
        self.records.append(rec)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def save_result(self, result: dict) -> Path:
        p = self.dir / "result.json"
        p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return p


def _summ(x: Any, limit: int = 240) -> Any:
    """Compact, JSON-safe summary of arbitrary inputs/outputs for the log."""
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        s = str(x)
        return s if len(s) <= limit else s[:limit] + "…"
    if isinstance(x, dict):
        return {k: _summ(v, 80) for k, v in list(x.items())[:12]}
    if isinstance(x, (list, tuple)):
        return [_summ(v, 80) for v in list(x)[:12]]
    # dataclass or object: best-effort
    for attr in ("name", "drug", "smiles", "target", "instruction", "reason"):
        if hasattr(x, attr):
            return f"{type(x).__name__}({attr}={getattr(x, attr)!r})"
    return type(x).__name__
