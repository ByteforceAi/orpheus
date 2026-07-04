"""Agent ③ Evaluator (proposal 분야: 평가).

Turns a molecule into a ScoreCard: RDKit descriptors, rule-based ADMET gate,
PAINS/Brenk structural alerts, SA score, and a SURROGATE binding affinity. Keeps
computed values and the (surrogate) affinity clearly separated so nothing inferred
is mistaken for a measurement (proposal §5).
"""
from __future__ import annotations
from ..tools import chem, admet, docking
from ..core.schemas import ScoreCard
from ..config import MAX_STRUCTURAL_ALERTS


class EvaluatorAgent:
    name = "evaluator"

    def run(self, smiles: str, target: str, parent_drug: str, parent_smiles: str,
            is_analog: bool) -> ScoreCard:
        d = chem.descriptors(smiles)
        admet_pass, admet_detail = admet.evaluate(d)
        alerts = chem.structural_alerts(smiles)
        aff = docking.affinity(smiles, target, parent_smiles)
        return ScoreCard(
            smiles=smiles,
            parent_drug=parent_drug,
            target=target,
            mw=d["mw"], logp=d["logp"], hbd=d["hbd"], hba=d["hba"],
            tpsa=d["tpsa"], rotb=d["rotb"], qed=d["qed"], sa_score=d["sa_score"],
            admet_pass=admet_pass,
            admet_detail=admet_detail,
            structural_alerts=alerts,
            affinity_surrogate=aff,
            affinity_is_surrogate=True,
            is_analog=is_analog,
        )

    @staticmethod
    def passes_gates(sc: ScoreCard) -> bool:
        return sc.admet_pass and len(sc.structural_alerts) <= MAX_STRUCTURAL_ALERTS
