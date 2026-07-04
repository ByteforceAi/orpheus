"""Typed data contracts passed between agents.

Keeping these explicit is what lets the five agents be developed independently:
each agent's input/output is a dataclass here, nothing implicit.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Hypothesis:
    """Output of the Hypothesis agent: a disease->target->approved-drug link."""
    disease: str
    target: str
    drug: str
    drug_smiles: str
    shared_targets: list[str]
    confidence: float                     # 0..1, from target-overlap strength
    rationale: str
    source: str = "target-overlap"        # or "llm" when online


@dataclass
class ScoreCard:
    """Output of the Evaluator: multi-property assessment of one molecule.

    `computed` values come from RDKit/tools; anything inferred is flagged so the
    reader never mistakes an assumption for a measurement.
    """
    smiles: str
    parent_drug: str
    target: str
    # computed physicochemical descriptors
    mw: float
    logp: float
    hbd: int
    hba: int
    tpsa: float
    rotb: int
    qed: float
    sa_score: float
    # gates & flags
    admet_pass: bool
    admet_detail: dict
    structural_alerts: list[str]
    affinity_surrogate: float             # pseudo-pKi (SURROGATE — swap for docking)
    affinity_is_surrogate: bool = True
    is_analog: bool = False               # False = parent drug itself


@dataclass
class Candidate:
    """A scored molecule flowing through the loop, optionally clinically triaged."""
    scorecard: ScoreCard
    hypothesis: Hypothesis
    passed_gates: bool = False
    clinical_feasibility: Optional[float] = None   # 0..1
    clinical_risk: Optional[str] = None
    clinical_notes: str = ""

    @property
    def overall(self) -> float:
        """Ranking score once all stages have run."""
        sc = self.scorecard
        base = 0.45 * sc.affinity_surrogate / 12.0 + 0.25 * sc.qed
        base += 0.15 * (1.0 - min(sc.sa_score, 10.0) / 10.0)
        base += 0.15 * self.hypothesis.confidence
        if self.clinical_feasibility is not None:
            base = 0.7 * base + 0.3 * self.clinical_feasibility
        penalty = 0.05 * len(sc.structural_alerts)
        return round(max(0.0, base - penalty), 4)


@dataclass
class Directive:
    """Critic -> orchestrator feedback that steers the next loop iteration."""
    stage: str                            # "hypothesis" | "optimizer" | "done"
    instruction: str
    params: dict = field(default_factory=dict)


@dataclass
class Verdict:
    """Critic's judgement at the end of an iteration."""
    converged: bool                       # stop looping?
    reason: str
    success: bool = False                 # True only for a real (candidate-found) convergence
    directive: Optional[Directive] = None


def to_dict(obj) -> dict:
    return asdict(obj)
