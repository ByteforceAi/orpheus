"""Rule-based ADMET / drug-likeness gate.

Applies Lipinski (MW, logP, HBD, HBA) and Veber (TPSA, rotatable bonds) rules on
top of the RDKit descriptor panel. A candidate passes if it satisfies at least
`ADMET_MIN_PASS` of the six rules. This is intentionally simple and fully
transparent; at 본선 it can be replaced by a learned ADMET surrogate trained on
public data — the interface (`evaluate(desc) -> (pass, detail)`) stays identical.
"""
from __future__ import annotations
from ..config import ADMET_RULES, ADMET_MIN_PASS


def evaluate(desc: dict) -> tuple[bool, dict]:
    r = ADMET_RULES
    checks = {
        "mw<=500":    desc["mw"] <= r["mw_max"],
        "logp<=5":    desc["logp"] <= r["logp_max"],
        "hbd<=5":     desc["hbd"] <= r["hbd_max"],
        "hba<=10":    desc["hba"] <= r["hba_max"],
        "tpsa<=140":  desc["tpsa"] <= r["tpsa_max"],
        "rotb<=10":   desc["rotb"] <= r["rotb_max"],
    }
    n_pass = sum(checks.values())
    detail = {
        "checks": checks,
        "n_pass": n_pass,
        "required": ADMET_MIN_PASS,
        # which specific rules failed — used by the Critic for failure attribution
        "failed": [k for k, ok in checks.items() if not ok],
    }
    return n_pass >= ADMET_MIN_PASS, detail
