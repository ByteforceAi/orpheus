"""Binding-affinity SURROGATE.

*** PLACEHOLDER — swap for real docking (AutoDock Vina) at 본선. ***

We do not have receptor structures or a docking binary in the demo environment, so
affinity is estimated deterministically from (a) 2D similarity to the parent
approved drug — the known active for the target — and (b) a small reproducible,
target-seeded perturbation. This yields a sensible, *reproducible* pseudo-pKi that
preserves relative ranking without pretending to be a physics-based score. Every
ScoreCard flags `affinity_is_surrogate=True` so this is never mistaken for a
measurement.

Real-docking drop-in: implement `affinity(smiles, target, parent_smiles)` to run
Vina against the target's PDB pocket and return the (negated) binding energy.
"""
from __future__ import annotations
import hashlib
from .chem import tanimoto


def _seeded_jitter(smiles: str, target: str) -> float:
    h = hashlib.sha256(f"{target}|{smiles}".encode()).digest()
    # map first byte to [-0.75, +0.75]
    return (h[0] / 255.0 - 0.5) * 1.5


def affinity(smiles: str, target: str, parent_smiles: str) -> float:
    """Return a surrogate pseudo-pKi (higher = stronger). Range ~ [4, 11]."""
    sim = tanimoto(smiles, parent_smiles)          # 0..1, parent==1.0
    base = 6.0 + 4.5 * sim                          # parent ~ 10.5, dissimilar ~ 6
    return round(max(4.0, min(11.0, base + _seeded_jitter(smiles, target))), 2)
