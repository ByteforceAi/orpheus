"""Thin LLM wrapper around the Anthropic API, with a graceful offline mode.

Design choice: ORPHEUS must RUN today without any API key. The deterministic
agent logic (target overlap, RDKit, rule-based ADMET) is the source of truth for
the demo and the retrospective-rediscovery benchmark. The LLM, when a key is
present (`ANTHROPIC_API_KEY`), is used to ENRICH reasoning — broader hypothesis
generation, nuanced clinical triage, sharper critique — never to fabricate the
quantitative results. At 본선 this is where the provided API credits plug in.
"""
from __future__ import annotations
from . import ledger  # noqa: F401  (kept for symmetry / future logging hooks)
from ..config import LLM_MODEL, llm_online


class LLM:
    def __init__(self, model: str = LLM_MODEL):
        self.model = model
        self.online = llm_online()
        self._client = None
        if self.online:
            try:
                import anthropic
                self._client = anthropic.Anthropic()
            except Exception:
                # any import/credential problem -> fall back to offline, never crash
                self.online = False

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> str | None:
        """Return model text, or None when offline (callers must handle None)."""
        if not self.online or self._client is None:
            return None
        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        except Exception:
            return None
