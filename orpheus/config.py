"""Central configuration: data paths, evaluator thresholds, loop settings.

Every tunable lives here so the pipeline's behaviour is transparent and reproducible.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
# ledger/output location; overridable so hosts with a read-only app dir stay happy
ARTIFACT_DIR = Path(os.environ.get("ORPHEUS_ARTIFACT_DIR", str(ROOT / "artifacts")))

# ---- reproducibility ----
SEED = 20260703

# ---- closed-loop settings ----
MAX_ITERATIONS = 4          # Critic-driven re-planning budget
TOP_HYPOTHESES = 3          # how many (target, drug) hypotheses to carry per round
ANALOGS_PER_HIT = 4         # analogs the optimizer proposes around each hit (plus the parent)

# ---- drug-likeness / ADMET gates (rule-based; swap for ML surrogate at 본선) ----
ADMET_RULES = {
    "mw_max": 500.0,        # Lipinski
    "logp_max": 5.0,        # Lipinski
    "hbd_max": 5,           # Lipinski
    "hba_max": 10,          # Lipinski
    "tpsa_max": 140.0,      # Veber (oral absorption)
    "rotb_max": 10,         # Veber
}
# a candidate must satisfy at least this many of the 6 rules to pass the ADMET gate
ADMET_MIN_PASS = 5

# structural-alert tolerance (PAINS + Brenk); candidates above this are flagged, not auto-killed
MAX_STRUCTURAL_ALERTS = 2

# ---- LLM (optional; offline deterministic fallback is fully functional) ----
LLM_MODEL = os.environ.get("ORPHEUS_MODEL", "claude-sonnet-4-6")
def llm_online() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
