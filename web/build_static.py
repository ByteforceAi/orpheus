#!/usr/bin/env python3
"""Pre-compute ORPHEUS outputs into static JSON for the replay (Vercel-only) demo.

Runs the retrospective benchmark and a closed-loop run for every seed disease,
writing the results to web/static/data/. Commit those JSON files so a purely
static host (Vercel) can serve a working demo with no backend. Re-run whenever the
seed data or engine changes.

    python web/build_static.py
"""
from __future__ import annotations
import json, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orpheus.core.orchestrator import Orchestrator
from orpheus.core import knowledge
from evals.retrospective import run_benchmark

OUT = ROOT / "web" / "static" / "data"


def _slug(s: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in s.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    diseases = knowledge.disease_names()

    manifest = {"mode": "replay",
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "diseases": [{"name": d, "slug": _slug(d)} for d in diseases]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    (OUT / "eval.json").write_text(
        json.dumps(run_benchmark(), ensure_ascii=False, indent=2), encoding="utf-8")

    for d in diseases:
        res = Orchestrator().run(d)
        (OUT / f"run_{_slug(d)}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        tag = "candidate" if res["best_candidate"] else "no-candidate"
        print(f"  baked run_{_slug(d)}.json  [{res['status']}, {tag}]")

    print(f"\nWrote {len(diseases)} runs + eval + manifest to {OUT}")


if __name__ == "__main__":
    main()
