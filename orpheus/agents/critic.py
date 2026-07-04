"""Agent ⑤ Critic (proposal: self-correction / 자율성).

Judges each iteration and, on failure, attributes the cause and emits a Directive
that re-steers a specific upstream stage — the mechanism behind ORPHEUS's closed
loop. Deterministic rules cover the common failure modes; an LLM (if present) can
add nuance but never overrides a safety-relevant verdict.
"""
from __future__ import annotations
from collections import Counter
from ..core.schemas import Candidate, Verdict, Directive


class Critic:
    name = "critic"

    def __init__(self, llm=None):
        self.llm = llm

    def run(self, scored: list[Candidate], survivors: list[Candidate],
            iteration: int, max_iterations: int) -> Verdict:
        # success: at least one gate-passing candidate with acceptable feasibility
        good = [c for c in survivors if c.passed_gates and (c.clinical_feasibility or 0) >= 0.6]
        if good:
            best = max(good, key=lambda c: c.overall)
            return Verdict(converged=True, success=True,
                           reason=(f"수렴: '{best.scorecard.parent_drug}'가 모든 게이트를 "
                                   f"통과하고 임상 타당성 {best.clinical_feasibility} 확보."))

        if iteration + 1 >= max_iterations:
            return Verdict(converged=True, success=False,
                           reason="반복 예산 소진 — 현재까지 최선 후보 반환(부분 성공).")

        # attribute the dominant failure across evaluated candidates
        if not scored:
            return Verdict(
                converged=False,
                reason="가설 단계에서 타깃 겹침이 없어 후보 없음 → 대체 타깃 탐색 지시.",
                directive=Directive(stage="hypothesis",
                                    instruction="대체 타깃/경로로 재가설",
                                    params={"avoid_targets": []}))

        fail_reasons: Counter = Counter()
        for c in scored:
            if not c.scorecard.admet_pass:
                for f in c.scorecard.admet_detail.get("failed", []):
                    fail_reasons[f] += 1
            if len(c.scorecard.structural_alerts) > 0:
                fail_reasons["structural_alerts"] += 1

        if fail_reasons:
            top_fail, _ = fail_reasons.most_common(1)[0]
            if top_fail == "logp<=5":
                return Verdict(
                    converged=False,
                    reason="지배적 실패 원인=logP 과다 → 분자 최적화에 극성↑ 유사체 탐색 지시.",
                    directive=Directive(stage="optimizer",
                                        instruction="더 극성인 유사체 탐색(logP 감소)",
                                        params={"polar_bias": True, "n_analogs": 6}))
            if top_fail in ("mw<=500", "tpsa<=140", "rotb<=10", "hbd<=5", "hba<=10"):
                return Verdict(
                    converged=False,
                    reason=f"지배적 실패 원인={top_fail} → 물성 개선 유사체 재탐색 지시.",
                    directive=Directive(stage="optimizer",
                                        instruction="물성 위반 완화 유사체 탐색",
                                        params={"n_analogs": 6}))
            # otherwise, weak binding across the board -> try alternate targets
        return Verdict(
            converged=False,
            reason="전반적 결합/물성 약함 → 대체 타깃으로 재가설 지시.",
            directive=Directive(stage="hypothesis",
                                instruction="대체 타깃/경로로 재가설",
                                params={"avoid_targets": []}))
