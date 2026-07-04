"""Smoke tests — run with:  python -m pytest -q   (or)   python tests/test_smoke.py

They assert the pipeline is wired correctly and produces sane, reproducible output.
No network / API key required.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orpheus.tools import chem, admet, docking
from orpheus.core import knowledge
from orpheus.core.orchestrator import Orchestrator
from evals.retrospective import run_benchmark


def test_seed_smiles_all_valid():
    for d in knowledge.drugs():
        assert chem.mol(d["smiles"]) is not None, f"bad SMILES: {d['name']}"


def test_descriptors_and_admet():
    desc = chem.descriptors("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
    assert 175 < desc["mw"] < 185
    ok, detail = admet.evaluate(desc)
    assert ok and "checks" in detail


def test_analog_generation():
    analogs = chem.generate_analogs("c1ccccc1O", 4)  # phenol
    assert 1 <= len(analogs) <= 4
    for a in analogs:
        assert chem.mol(a["smiles"]) is not None


def test_affinity_surrogate_parent_is_high():
    p = "CC(=O)Oc1ccccc1C(=O)O"
    assert docking.affinity(p, "PTGS1", p) >= 9.5  # parent ~ identical -> strong


def test_closed_loop_runs_and_converges():
    res = Orchestrator().run("Pulmonary Arterial Hypertension")
    assert res["best_candidate"] is not None
    assert res["best_candidate"]["drug"] == "Sildenafil"  # correct repurposing hit
    assert res["iterations"] >= 1


def test_benchmark_metrics_reasonable():
    b = run_benchmark()
    s = b["summary"]
    assert s["n_gold_pairs"] == 5
    assert s["mrr"] > 0.5           # gold drugs recovered near the top


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); passed += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
