# CLAUDE.md — ORPHEUS project constitution

> Instructions for any AI agent (Claude Code lead + sub-agents) working in this repo.
> Read this fully before editing. It encodes the architecture, the contracts between
> the five agents, and the invariants that must never be broken.

## 1. What this is

**ORPHEUS** — *Orphan-disease Repurposing via Planning, Hypothesis, Evaluation &
Updating System.* A multi-agent **closed loop** that proposes **drug-repurposing**
candidates for **rare / orphan diseases**, scoped deliberately to **already-approved
drugs** (known human safety). Team: **BYTEFORCE**. Built for the 4th JUMP AI
(fourth.py) competition, 분야 4 (융합) = fields 1+2 with a thin field-3 layer.

The pitch in one line: reuse the vast, under-exploited space of safe approved drugs
to find rare-disease treatments — with an agent that **fails, attributes the cause,
and re-plans**, logging every step for full transparency.

## 2. Architecture (the loop)

```
disease
  → ① hypothesis    (agents/hypothesis.py)  disease → target → approved-drug hits
  → ② optimizer     (agents/optimizer.py)   RDKit analogs around each hit
  → ③ evaluator     (agents/evaluator.py)   descriptors · ADMET · alerts · SA · affinity(surrogate)
  → ④ clinical      (agents/clinical.py)    feasibility / risk triage (NO trial design)
  → ⑤ critic        (agents/critic.py)      converge? or attribute failure + Directive
      ↺ re-plan the named upstream stage, up to config.MAX_ITERATIONS
orchestrator (core/orchestrator.py) drives the loop; ledger (core/ledger.py) records everything.
```

## 3. Agent contracts (do not change signatures casually)

All shared types live in `orpheus/core/schemas.py`. Each agent is independently
testable because its I/O is a dataclass there.

| Agent | File | Input → Output | Offline behaviour (must always work) | Online (LLM) adds |
|---|---|---|---|---|
| ① Hypothesis | `agents/hypothesis.py` | `(disease, targets)` → `list[Hypothesis]` | rank approved drugs by **target overlap** with disease | broader pathway links, richer rationale — **never changes the numeric ranking** |
| ② Optimizer | `agents/optimizer.py` | `(parent_smiles, params)` → `list[{smiles,edit,is_analog}]` | parent + RDKit single-point analogs; `polar_bias` on directive | (future) generative analogs |
| ③ Evaluator | `agents/evaluator.py` | `(smiles, target, parent…)` → `ScoreCard` | RDKit descriptors + rule ADMET + PAINS/Brenk + SA + **surrogate** affinity | — |
| ④ Clinical | `agents/clinical.py` | `Candidate` → `Candidate` | feasibility from dev-path (approved parent ≫ novel analog) | one-sentence regulatory nuance |
| ⑤ Critic | `agents/critic.py` | `(scored, survivors, it)` → `Verdict(+Directive)` | rule-based failure attribution & re-plan | nuance only; **never overrides a safety verdict** |

## 4. Hard invariants (NEVER break these)

1. **Offline must keep working.** No API key ⇒ the full pipeline and the benchmark
   still run deterministically. The LLM only *enriches*; it is never required.
2. **Surrogate honesty.** Binding affinity is a placeholder (`tools/docking.py`).
   Every `ScoreCard.affinity_is_surrogate` stays `True` until real docking replaces
   it. Never present a surrogate as a measurement. Keep the "computed vs inferred"
   separation (proposal §5).
3. **Approved-drug scope = safety.** ORPHEUS repurposes approved drugs; it does **not**
   generate novel hazardous synthesis routes. If you add a synthesis feature, gate it
   behind structural alerts + a controlled/dual-use block. (proposal §5)
4. **No fabrication without basis.** If hypothesis finds no target overlap, the loop
   returns **no candidate** (status `no_viable_candidate`) — it must not invent one.
   See the IPF distractor disease.
5. **Everything is logged.** Every agent action calls `ledger.log(...)`. The Provenance
   Ledger is the transparency guarantee; do not add silent steps.
6. **Gold pairs are held out.** `data/gold_repurposing.json` is read ONLY by
   `evals/retrospective.py`, never by the agents. Do not leak answers into the KB used
   at inference.
7. **Reproducibility.** Seed lives in `config.SEED`; the surrogate is deterministic.
   Keep runs reproducible.

## 5. Tools

- `tools/chem.py` — RDKit: `descriptors`, `tanimoto`, `structural_alerts`,
  `generate_analogs`, `sa_score`. All real.
- `tools/admet.py` — Lipinski + Veber rule gate. Interface: `evaluate(desc) -> (pass, detail)`.
- `tools/docking.py` — **surrogate** affinity. Real-docking drop-in point.

## 6. Run / test

```bash
python3 -m venv .venv && source .venv/bin/activate     # Ubuntu/WSL: avoid PEP 668; enables `python`
pip install -r requirements.txt                        # RDKit ships cp314 wheels; Py3.14 OK
python run.py --list                                    # seed diseases
python run.py -d "Pulmonary Arterial Hypertension"      # closed loop + candidate card
python run.py --eval                                    # retrospective rediscovery (Recall@k, MRR)
python tests/test_smoke.py                              # smoke tests (no network)
export ANTHROPIC_API_KEY=...                            # optional: enable LLM enrichment
```

Artifacts (ledger + result) are written to `artifacts/<run_id>/`.

## 7. 본선 swap-ins (the roadmap; keep interfaces stable)

- **Real docking**: replace `tools/docking.py:affinity(...)` with AutoDock Vina against
  the target PDB pocket. Keep the same signature; flip `affinity_is_surrogate` to False.
- **Real data at scale**: replace `core/knowledge.py` loaders with ChEMBL / DrugBank /
  Open Targets clients. Expand `data/` beyond the seed set.
- **Live LLM**: already wired via `core/llm.py`; plug the provided competition credits
  into `ANTHROPIC_API_KEY`. Use it for hypothesis breadth, clinical nuance, critique.
- **Demo UI**: render the ledger as the Reasoning Graph / Decision Timeline (proposal §6).
- **Bigger benchmark**: grow `data/gold_repurposing.json` with more held-out pairs to
  make Recall/MRR a stronger, less-saturated signal.

## 8. Conventions

- Python ≥ 3.10, standard library + RDKit + anthropic only. Type hints on public funcs.
- Keep agents pure-ish: no cross-agent imports except via `schemas` and `tools`.
- **Commits**: Conventional Commits — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`,
  `chore:`. One logical change per commit. Reference the loop stage when relevant,
  e.g. `feat(optimizer): BRICS-based analog enumeration`.
- When you touch an agent, update or add a smoke test in `tests/test_smoke.py`.
