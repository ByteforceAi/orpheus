"""Loads the seed knowledge base (drugs, diseases, gold pairs).

At 본선 scale these loaders point at ChEMBL / DrugBank / Open Targets instead of
the bundled JSON; the rest of the system is agnostic to the source.
"""
from __future__ import annotations
import json
from functools import lru_cache
from ..config import DATA_DIR


@lru_cache(maxsize=1)
def drugs() -> list[dict]:
    return json.loads((DATA_DIR / "drugs.json").read_text(encoding="utf-8"))["drugs"]


@lru_cache(maxsize=1)
def diseases() -> list[dict]:
    return json.loads((DATA_DIR / "diseases.json").read_text(encoding="utf-8"))["diseases"]


@lru_cache(maxsize=1)
def gold_pairs() -> list[dict]:
    return json.loads((DATA_DIR / "gold_repurposing.json").read_text(encoding="utf-8"))["pairs"]


def find_disease(name: str) -> dict | None:
    n = name.strip().lower()
    for d in diseases():
        if d["name"].lower() == n:
            return d
    # forgiving substring match
    for d in diseases():
        if n in d["name"].lower() or d["name"].lower() in n:
            return d
    return None


def disease_names() -> list[str]:
    return [d["name"] for d in diseases()]
