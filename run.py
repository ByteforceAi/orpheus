#!/usr/bin/env python3
"""ORPHEUS CLI.

  python run.py --disease "Pulmonary Arterial Hypertension"   # run the closed loop
  python run.py --eval                                        # retrospective rediscovery
  python run.py --list                                        # list seed diseases

Runs fully offline (deterministic). Set ANTHROPIC_API_KEY to enable LLM
enrichment of hypothesis/clinical/critic reasoning.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orpheus.core.orchestrator import Orchestrator
from orpheus.core import knowledge
from evals.retrospective import run_benchmark

C = {"h": "\033[1;36m", "b": "\033[1m", "d": "\033[2m", "g": "\033[32m",
     "y": "\033[33m", "x": "\033[0m"}


def _c(s, k):
    return f"{C[k]}{s}{C['x']}"


def print_run(res: dict) -> None:
    print(_c("\n╔═ ORPHEUS ─ closed-loop repurposing run", "h"))
    print(f"  run_id  : {res['run_id']}")
    print(f"  mode    : {res['mode']}   model: {res['model']}")
    print(f"  disease : {_c(res['disease'], 'b')}   targets: {', '.join(res['disease_targets'])}")
    status_disp = {
        "converged": _c("converged ✓", "g"),
        "partial": _c("partial (best-so-far under budget)", "y"),
        "no_viable_candidate": _c("no viable candidate — refused to fabricate", "y"),
    }.get(res.get("status", ""), res.get("status", ""))
    print(f"  loop    : {res['iterations']} iteration(s) · {status_disp}")

    print(_c("\n── reasoning trace (Critic-driven) ──", "h"))
    for t in res["trace"]:
        head = f"  [{t['iteration']}] hits={t['top_hits']}  scored={t['n_scored']}  survivors={t['n_survivors']}"
        print(head)
        print(_c(f"       critic: {t['critic']}", "d"))

    bc = res["best_candidate"]
    print(_c("\n── final candidate card ──", "h"))
    if not bc:
        print("  (no candidate)")
        return
    tag = _c("approved drug (repurposing)", "g") if bc["is_parent_approved_drug"] \
        else _c("novel analog", "y")
    print(f"  {_c(bc['drug'], 'b')}  →  {_c(res['disease'], 'b')}   [{tag}]")
    print(f"  target        : {bc['target']}   (hypothesis confidence {bc['hypothesis_confidence']})")
    print(f"  SMILES        : {bc['smiles']}")
    aff = bc["affinity_surrogate_pKi"]
    print(f"  affinity      : ~pKi {aff}  " + _c("(SURROGATE — swap for docking)", "d"))
    d = bc["descriptors"]
    print(f"  descriptors   : MW {d['MW']} · logP {d['logP']} · TPSA {d['TPSA']} · "
          f"QED {d['QED']} · SA {d['SA_score']}")
    print(f"  ADMET gate    : {_c('PASS', 'g') if bc['admet_pass'] else _c('FAIL', 'y')}"
          + (f"  failed={bc['admet_failed_rules']}" if bc['admet_failed_rules'] else ""))
    print(f"  alerts        : {len(bc['structural_alerts'])} "
          f"{bc['structural_alerts'] if bc['structural_alerts'] else ''}")
    print(f"  clinical      : feasibility {bc['clinical_feasibility']} · risk {bc['clinical_risk']}")
    print(_c(f"    {bc['clinical_notes']}", "d"))
    print(f"  overall score : {_c(bc['overall_score'], 'b')}")
    print(_c(f"\n  ledger: {res['ledger_path']}", "d"))


def print_eval(res: dict) -> None:
    s = res["summary"]
    print(_c("\n╔═ Retrospective-rediscovery benchmark (§4)", "h"))
    print(f"  gold pairs : {s['n_gold_pairs']}")
    print(f"  Recall@1   : {_c(s['recall_at_1'], 'b')}")
    print(f"  Recall@3   : {_c(s['recall_at_3'], 'b')}")
    print(f"  MRR        : {_c(s['mrr'], 'b')}")
    print(f"  mean rank  : {s['mean_rank']}")
    print(_c("\n── per-pair ──", "h"))
    print(f"  {'drug':<14}{'disease':<38}{'tgt':<10}{'rank':<6}top-3")
    for r in res["rows"]:
        rank = r["rank"] if r["rank"] else "—"
        print(f"  {r['drug']:<14}{r['disease']:<38}{r['shared_target']:<10}{str(rank):<6}{r['top3']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="ORPHEUS — orphan-disease drug repurposing agent")
    ap.add_argument("--disease", "-d", help="disease name to run the closed loop on")
    ap.add_argument("--eval", action="store_true", help="run retrospective-rediscovery benchmark")
    ap.add_argument("--list", action="store_true", help="list seed diseases")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of pretty output")
    a = ap.parse_args()

    if a.list:
        print("Seed diseases:")
        for n in knowledge.disease_names():
            print("  -", n)
        return
    if a.eval:
        res = run_benchmark()
        print(json.dumps(res, ensure_ascii=False, indent=2)) if a.json else print_eval(res)
        return
    if a.disease:
        res = Orchestrator().run(a.disease)
        print(json.dumps(res, ensure_ascii=False, indent=2)) if a.json else print_run(res)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
