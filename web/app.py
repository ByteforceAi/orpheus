"""ORPHEUS web app (live mode).

Wraps the existing engine (no logic duplicated) behind a small JSON API and serves
the single-page UI. Deploy this as a Docker container (Hugging Face Spaces / Render /
Railway / Cloud Run). For a Vercel-only static site, the same UI runs in "replay"
mode against pre-built JSON — see web/build_static.py.

Run locally:
    pip install -r requirements-web.txt
    uvicorn web.app:app --reload --port 8000
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# make the repo root importable (so `orpheus` and `evals` resolve)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# keep the provenance ledger on a writable path regardless of host
os.environ.setdefault("ORPHEUS_ARTIFACT_DIR", "/tmp/orpheus-artifacts")

from fastapi import FastAPI, HTTPException          # noqa: E402
from fastapi.responses import JSONResponse           # noqa: E402
from fastapi.staticfiles import StaticFiles          # noqa: E402

from orpheus.core.orchestrator import Orchestrator   # noqa: E402
from orpheus.core import knowledge                    # noqa: E402
from evals.retrospective import run_benchmark         # noqa: E402

app = FastAPI(title="ORPHEUS", version="0.1.0",
              description="Orphan-disease drug-repurposing agent — BYTEFORCE")

STATIC = Path(__file__).resolve().parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "live", "service": "orpheus"}


@app.get("/api/diseases")
def diseases():
    return {"diseases": knowledge.disease_names()}


@app.get("/api/run")
def run(disease: str):
    try:
        return Orchestrator().run(disease)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.get("/api/eval")
def evaluate():
    return run_benchmark()


# serve the UI + any pre-built data at the root (registered AFTER the API routes)
if STATIC.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
else:  # pragma: no cover
    @app.get("/")
    def _root():
        return JSONResponse({"error": "static UI not found"}, status_code=500)
