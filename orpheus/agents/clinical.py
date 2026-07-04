"""Agent ④ Clinical-Feasibility Screener (proposal 분야 3, thin).

Does NOT design trials or generate protocols (that is where hallucination risk
lives). Instead it triages surviving candidates on development feasibility and
returns a feasibility score + risk band + short rationale.

Key repurposing advantage encoded here: an *approved parent* drug carries known
human safety/PK, so the parent scores markedly higher feasibility than a novel
analog, which would re-enter preclinical safety. This is the honest, defensible
way to weave 분야 3 in.
"""
from __future__ import annotations
from ..core.schemas import Candidate


class ClinicalScreener:
    name = "clinical"

    def __init__(self, llm=None):
        self.llm = llm

    def run(self, cand: Candidate) -> Candidate:
        sc = cand.scorecard
        # base feasibility from development path
        if not sc.is_analog:
            feas = 0.85          # approved drug, label-expansion / known safety
            path = "라벨 확장 / 기존 안전성·PK 활용 (신규 IND 불필요 가능성)"
        else:
            feas = 0.45          # novel analog -> re-enter preclinical safety
            path = "신규 유사체 → 전임상 안전성 재확인 필요 (신규 IND 경로)"

        # adjust for oral drug-likeness and safety flags
        feas += 0.10 * (sc.qed - 0.5)
        feas -= 0.07 * len(sc.structural_alerts)
        feas = max(0.0, min(1.0, feas))

        risk = "낮음" if feas >= 0.7 else ("중간" if feas >= 0.45 else "높음")
        notes = (f"{path}. QED={sc.qed}, 구조경보 {len(sc.structural_alerts)}건. "
                 f"대상 타깃 {sc.target}.")

        # optional LLM nuance (regulatory considerations) — non-authoritative
        if self.llm and self.llm.online and not sc.is_analog:
            sys = ("You are a regulatory-savvy translational scientist. In ONE sentence, "
                   "note one realistic development consideration for repurposing an already "
                   "approved drug to a new indication. No fabricated specifics.")
            txt = self.llm.complete(sys, f"Drug: {sc.parent_drug}; target {sc.target}.",
                                    max_tokens=90)
            if txt:
                notes += " " + txt.strip()

        cand.clinical_feasibility = round(feas, 3)
        cand.clinical_risk = risk
        cand.clinical_notes = notes
        return cand
