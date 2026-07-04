# ORPHEUS live demo — portable container.
# Works on Hugging Face Spaces (Docker SDK), Render, Railway, Fly.io, Cloud Run.
FROM python:3.12-slim

# RDKit wheels are self-contained; libgomp1 covers the OpenMP runtime they link.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY . .

# hosts inject $PORT; HF Spaces defaults to 7860. Ledger goes to a writable path.
ENV PORT=7860 ORPHEUS_ARTIFACT_DIR=/tmp/orpheus-artifacts
EXPOSE 7860

CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT}"]
