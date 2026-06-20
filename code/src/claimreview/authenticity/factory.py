"""Construct the configured authenticity detector, or None when disabled.

Kept separate from the provider registry so the authenticity backend is selected and
toggled independently. Modes (CLAIMREVIEW_AUTH_MODE):

  * ensemble   (default) — C2PA provenance (free, deterministic) + memoized Gemini VLM.
                Provenance settles obvious AI cheaply; the VLM covers the rest.
  * provenance — C2PA only. Zero added API cost; catches signed/watermarked AI content;
                never false-positives on real photos. Safest for the graded batch.
  * vlm        — Gemini VLM only (memoized).

Disable entirely with CLAIMREVIEW_AUTH_ENABLED=false. The VLM backends need a Gemini key;
provenance mode needs none.
"""

from __future__ import annotations

import os

from claimreview.authenticity.detector import (
    AuthenticityDetector,
    MemoizingAuthenticityDetector,
)
from claimreview.authenticity.ensemble import EnsembleAuthenticityDetector
from claimreview.authenticity.provenance import C2PAProvenanceDetector


def _gemini_detector(env: dict) -> AuthenticityDetector | None:
    api_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    from claimreview.authenticity.gemini_detector import GeminiAuthenticityDetector

    inner = GeminiAuthenticityDetector(api_key=api_key, model=env.get("CLAIMREVIEW_AUTH_MODEL"))
    return MemoizingAuthenticityDetector(inner)


def get_authenticity_detector(env: dict | None = None) -> AuthenticityDetector | None:
    """Return the configured authenticity detector, or None if disabled/unconfigured."""
    e = os.environ if env is None else env

    raw = str(e.get("CLAIMREVIEW_AUTH_ENABLED", "true")).strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return None

    mode = str(e.get("CLAIMREVIEW_AUTH_MODE", "ensemble")).strip().lower()
    provenance = C2PAProvenanceDetector()

    if mode == "provenance":
        return provenance
    if mode == "vlm":
        return _gemini_detector(e)

    # default: ensemble (provenance first, then VLM for whatever provenance can't settle)
    gemini = _gemini_detector(e)
    if gemini is None:
        return provenance   # no key -> deterministic provenance is still useful on its own
    return EnsembleAuthenticityDetector([provenance, gemini])
