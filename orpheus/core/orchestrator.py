"""Orchestrator — the ORPHEUS closed loop.

    disease → ① hypothesis → ② optimize(RDKit) → ③ evaluate → ④ clinical triage
            → ⑤ Critic verdict → (converge | re-plan upstream) ↺

Every step is written to the Provenance Ledger. On non-convergence the Critic's
Directive re-steers a specific stage (more-polar analogs, or an alternative
target) and the loop repeats up to `MAX_ITERATIONS`.
"""
from __future__ import annotations
from ..config import (ARTIFACT_DIR, LLM_MODEL, SEED, MAX_ITERATIONS,
                      TOP_HYPOTHESES, llm_online)
from ..core.ledger import Ledger
from ..core.llm import LLM
from ..core import knowledge
from ..core.schemas import Candidate, to_dict
from ..agents.hypothesis import HypothesisAgent
from ..agents.optimizer import OptimizerAgent
from ..agents.evaluator import EvaluatorAgent
from ..agents.clinical import ClinicalScreener
from ..agents.critic import Critic


class Orchestrator:
    def __init__(self, run_id: str | None = None):
        self.llm = LLM()
        self.ledger = Ledger(run_id, ARTIFACT_DIR, LLM_MODEL, llm_online(), SEED)
        self.hypothesis = HypothesisAgent(self.llm)
        self.optimizer = OptimizerAgent()
        self.evaluator = EvaluatorAgent()
        self.clinical = ClinicalScreener(self.llm)
        self.critic = Critic(self.llm)

    def run(self, disease_name: str) -> dict:
        L = self.ledger
        disease = knowledge.find_disease(disease_name)
        if disease is None:
            raise ValueError(f"unknown disease '{disease_name}'. "
                             f"known: {knowledge.disease_names()}")
        dz, targets = disease["name"], disease["targets"]
        L.log(0, "orchestrator", "start",
              inputs={"disease": dz, "targets": targets, "mode": L.mode})

        hyp_params: dict = {"avoid_targets": []}
        opt_params: dict = {}
        trace: list[dict] = []
        best: Candidate | None = None

        for it in range(MAX_ITERATIONS):
            # ① hypothesis
            hyps = self.hypothesis.run(dz, targets, hyp_params)
            L.log(it, "hypothesis", "rank",
                  inputs={"avoid": hyp_params.get("avoid_targets")},
                  outputs=[f"{h.drug}:{'/'.join(h.shared_targets)} (c={h.confidence})"
                           for h in hyps[:TOP_HYPOTHESES]])
            scored: list[Candidate] = []

            # ② optimize + ③ evaluate
            for h in hyps[:TOP_HYPOTHESES]:
                mols = self.optimizer.run(h.drug_smiles, opt_params)
                L.log(it, "optimizer", "analogs",
                      inputs={"hit": h.drug, "polar_bias": opt_params.get("polar_bias", False)},
                      outputs=[f"{m['edit']}:{m['smiles']}" for m in mols])
                for m in mols:
                    sc = self.evaluator.run(m["smiles"], h.target, h.drug,
                                            h.drug_smiles, m["is_analog"])
                    cand = Candidate(scorecard=sc, hypothesis=h,
                                     passed_gates=self.evaluator.passes_gates(sc))
                    scored.append(cand)
            L.log(it, "evaluator", "scorecards",
                  outputs=[f"{c.scorecard.parent_drug}"
                           f"{'*' if not c.scorecard.is_analog else '~'} "
                           f"aff={c.scorecard.affinity_surrogate} "
                           f"admet={'P' if c.scorecard.admet_pass else 'F'} "
                           f"alerts={len(c.scorecard.structural_alerts)}"
                           for c in scored])

            # ④ clinical triage on gate-passers
            survivors = [c for c in scored if c.passed_gates]
            for c in survivors:
                self.clinical.run(c)
            L.log(it, "clinical", "triage",
                  outputs=[f"{c.scorecard.parent_drug}: feas={c.clinical_feasibility} "
                           f"risk={c.clinical_risk}" for c in survivors])

            # track best-so-far
            pool = survivors or scored
            if pool:
                cand_best = max(pool, key=lambda c: c.overall)
                if best is None or cand_best.overall > best.overall:
                    best = cand_best

            # ⑤ Critic
            verdict = self.critic.run(scored, survivors, it, MAX_ITERATIONS)
            L.log(it, "critic", "verdict",
                  outputs={"converged": verdict.converged, "reason": verdict.reason,
                           "directive": (verdict.directive.instruction
                                         if verdict.directive else None)})
            trace.append({
                "iteration": it,
                "n_hypotheses": len(hyps),
                "top_hits": [h.drug for h in hyps[:TOP_HYPOTHESES]],
                "n_scored": len(scored),
                "n_survivors": len(survivors),
                "converged": verdict.converged,
                "success": verdict.success,
                "critic": verdict.reason,
            })

            if verdict.converged:
                break

            # apply directive -> steer next iteration
            d = verdict.directive
            if d and d.stage == "optimizer":
                opt_params = dict(d.params)
            elif d and d.stage == "hypothesis":
                exhausted = {h.target for h in hyps[:TOP_HYPOTHESES]}
                hyp_params["avoid_targets"] = list(
                    set(hyp_params.get("avoid_targets", [])) | exhausted)
                opt_params = {}

        success = bool(trace and trace[-1]["success"] and best is not None)
        if success:
            status = "converged"
        elif best is not None:
            status = "partial"          # returned best-so-far under budget
        else:
            status = "no_viable_candidate"   # no molecular basis — refused to fabricate

        result = {
            "run_id": L.run_id,
            "mode": L.mode,
            "model": L.model,
            "disease": dz,
            "disease_targets": targets,
            "iterations": len(trace),
            "status": status,
            "converged": success,
            "best_candidate": (self._card(best) if best else None),
            "trace": trace,
            "ledger_path": str(L.path),
        }
        L.save_result(result)
        return result

    @staticmethod
    def _card(c: Candidate) -> dict:
        sc = c.scorecard
        return {
            "drug": sc.parent_drug,
            "is_parent_approved_drug": not sc.is_analog,
            "smiles": sc.smiles,
            "target": sc.target,
            "affinity_surrogate_pKi": sc.affinity_surrogate,
            "affinity_is_surrogate": sc.affinity_is_surrogate,
            "descriptors": {"MW": sc.mw, "logP": sc.logp, "HBD": sc.hbd, "HBA": sc.hba,
                            "TPSA": sc.tpsa, "RotB": sc.rotb, "QED": sc.qed,
                            "SA_score": sc.sa_score},
            "admet_pass": sc.admet_pass,
            "admet_failed_rules": sc.admet_detail.get("failed", []),
            "structural_alerts": sc.structural_alerts,
            "clinical_feasibility": c.clinical_feasibility,
            "clinical_risk": c.clinical_risk,
            "clinical_notes": c.clinical_notes,
            "hypothesis_confidence": c.hypothesis.confidence,
            "overall_score": c.overall,
        }
