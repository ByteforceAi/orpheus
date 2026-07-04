"""Agent ② Molecular Optimizer (proposal 분야 2, RDKit core).

For a repurposing hit, the parent approved drug is itself the primary candidate
(repurposing reuses known-safe molecules). Around it we enumerate a small set of
single-point analogs to (a) demonstrate the optimization loop and (b) give the
evaluator a neighbourhood to rank. A Critic directive `polar_bias` biases analog
generation toward polarity-increasing edits — the chemistry-level response to an
"logP too high / ADMET failed" re-plan.
"""
from __future__ import annotations
from ..tools import chem
from ..config import ANALOGS_PER_HIT


class OptimizerAgent:
    name = "optimizer"

    def run(self, parent_smiles: str, directive_params: dict | None = None) -> list[dict]:
        params = directive_params or {}
        polar = bool(params.get("polar_bias", False))
        n = int(params.get("n_analogs", ANALOGS_PER_HIT))

        candidates: list[dict] = []
        parent_canon = chem.canonical(parent_smiles)
        if parent_canon:
            candidates.append({"smiles": parent_canon, "edit": "parent", "is_analog": False})
        for a in chem.generate_analogs(parent_smiles, n, polar_bias=polar):
            candidates.append({"smiles": a["smiles"], "edit": a["edit"], "is_analog": True})
        return candidates
