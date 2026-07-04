"""Agent ① Hypothesis (proposal 분야 1).

Given a disease, propose ranked (target, approved-drug) repurposing hypotheses.

Offline (deterministic, always works): score every approved drug by the strength
of its target overlap with the disease's associated targets; rank and attach a
confidence + rationale. This is the exact signal the retrospective-rediscovery
benchmark tests.

Online (LLM present): the model may additionally surface non-obvious
pathway-level links and re-rank — but the quantitative overlap remains the anchor,
so results stay honest and reproducible.

A Critic directive `avoid_targets` lets a re-plan steer away from an exhausted
target toward alternative mechanisms.
"""
from __future__ import annotations
from ..core.schemas import Hypothesis
from ..core import knowledge


def _overlap(drug_targets: list[str], disease_targets: list[str]) -> list[str]:
    ds = set(disease_targets)
    return [t for t in drug_targets if t in ds]


def rank_drugs_for_disease(disease_name: str, disease_targets: list[str],
                           avoid_targets: set[str] | None = None) -> list[Hypothesis]:
    avoid = avoid_targets or set()
    hyps: list[Hypothesis] = []
    for d in knowledge.drugs():
        shared = [t for t in _overlap(d["targets"], disease_targets) if t not in avoid]
        if not shared:
            continue
        # confidence: fraction of disease targets hit, lightly boosted by count
        conf = min(1.0, 0.35 + 0.2 * len(shared) + 0.15 * len(shared) / max(1, len(disease_targets)))
        primary = shared[0]
        hyps.append(Hypothesis(
            disease=disease_name,
            target=primary,
            drug=d["name"],
            drug_smiles=d["smiles"],
            shared_targets=shared,
            confidence=round(conf, 3),
            rationale=(f"{d['name']} (orig: {d['original_indication']}) acts on "
                       f"{'/'.join(shared)}, which is implicated in {disease_name}."),
        ))
    hyps.sort(key=lambda h: (len(h.shared_targets), h.confidence), reverse=True)
    return hyps


class HypothesisAgent:
    name = "hypothesis"

    def __init__(self, llm=None):
        self.llm = llm

    def run(self, disease_name: str, disease_targets: list[str],
            directive_params: dict | None = None) -> list[Hypothesis]:
        avoid = set((directive_params or {}).get("avoid_targets", []))
        hyps = rank_drugs_for_disease(disease_name, disease_targets, avoid_targets=avoid)

        # optional LLM enrichment of the top rationale (never changes the ranking numbers)
        if self.llm and self.llm.online and hyps:
            sys = ("You are a cautious drug-repurposing scientist. Given a disease, its "
                   "molecular targets, and a candidate approved drug with a shared target, "
                   "write ONE sentence on the mechanistic plausibility. Do not invent facts.")
            top = hyps[0]
            txt = self.llm.complete(
                sys,
                f"Disease: {disease_name}\nDisease targets: {disease_targets}\n"
                f"Drug: {top.drug} (targets {top.shared_targets}).",
                max_tokens=120,
            )
            if txt:
                top.rationale = txt.strip()
                top.source = "llm+target-overlap"
        return hyps
