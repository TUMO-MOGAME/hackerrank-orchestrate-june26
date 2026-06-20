"""Authenticity detector interface, verdict type, memoization, and the merge policy.

The merge policy is the single place that decides how an authenticity verdict changes the
graded output. It is deliberately CONSERVATIVE: only high-confidence AI-generation flips
fields, because the real claim images are genuine photos and false positives would add
wrong `non_original_image` flags and hurt the score. Calibrate the threshold against
`evaluation/authenticity_eval.py`.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from claimreview.io.images import LoadedImage
from claimreview.schema.output_schema import split_semicolon

# Default decision threshold: flag only when the detector is clearly confident.
DEFAULT_THRESHOLD = 0.7


@dataclass(frozen=True)
class ImageAuthenticity:
    """Per-image verdict from a detector."""

    image_id: str
    ai_generated: bool          # True = looks AI-generated / manipulated, not a real photo
    confidence: float           # 0.0–1.0 confidence in `ai_generated`
    signals: list[str] = field(default_factory=list)  # short human-readable cues


class AuthenticityDetector(ABC):
    """Interface every authenticity backend implements."""

    name: str = "base"

    @abstractmethod
    def assess(self, images: list[LoadedImage]) -> list[ImageAuthenticity]:
        """Return one verdict per input image, in the same order."""
        raise NotImplementedError


class FakeAuthenticityDetector(AuthenticityDetector):
    """Offline detector for tests/demos: returns a fixed verdict (default: all real)."""

    name = "fake"

    def __init__(
        self,
        *,
        ai_generated: bool = False,
        confidence: float = 0.0,
        signals: list[str] | None = None,
    ) -> None:
        self._ai = ai_generated
        self._conf = confidence
        self._signals = signals or []

    def assess(self, images: list[LoadedImage]) -> list[ImageAuthenticity]:
        return [
            ImageAuthenticity(img.image_id, self._ai, self._conf, list(self._signals))
            for img in images
        ]


class MemoizingAuthenticityDetector(AuthenticityDetector):
    """Wrap a detector and cache verdicts by image CONTENT hash.

    The same image shared across many claims (or repeated in a batch) is assessed once.
    Cache is in-memory for the process; the pipeline can layer a persistent cache later.
    """

    def __init__(self, inner: AuthenticityDetector) -> None:
        self._inner = inner
        self.name = f"memoized:{inner.name}"
        self._cache: dict[str, ImageAuthenticity] = {}
        self.calls = 0  # number of images actually sent to the inner detector (for reporting)

    @staticmethod
    def _key(img: LoadedImage) -> str:
        return hashlib.sha256(img.data_b64.encode("ascii")).hexdigest()

    def assess(self, images: list[LoadedImage]) -> list[ImageAuthenticity]:
        # Unique, still-uncached content keys — deduped WITHIN this batch too, so the same
        # bytes appearing twice in one call only costs one inner assessment.
        pending: dict[str, LoadedImage] = {}
        for img in images:
            key = self._key(img)
            if key not in self._cache and key not in pending:
                pending[key] = img
        if pending:
            todo = list(pending.values())
            self.calls += len(todo)
            for img, verdict in zip(todo, self._inner.assess(todo), strict=True):
                self._cache[self._key(img)] = verdict
        # Re-key the cached verdicts to each requested image's own ID (same bytes may appear
        # under different image_ids across claims).
        out: list[ImageAuthenticity] = []
        for img in images:
            v = self._cache[self._key(img)]
            out.append(
                ImageAuthenticity(img.image_id, v.ai_generated, v.confidence, list(v.signals))
            )
        return out


def flagged_verdicts(
    verdicts: list[ImageAuthenticity], *, threshold: float = DEFAULT_THRESHOLD
) -> list[ImageAuthenticity]:
    """Verdicts that clear the confidence bar for being treated as AI-generated."""
    return [v for v in verdicts if v.ai_generated and v.confidence >= threshold]


def apply_authenticity(
    generated: dict,
    verdicts: list[ImageAuthenticity],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Merge authenticity verdicts into the (already-repaired) generated fields.

    If any image is confidently AI-generated/manipulated, the evidence cannot be trusted:
    raise `non_original_image` + `possible_manipulation`, mark the image set unusable,
    route to manual review, and downgrade a `supported` verdict to
    `not_enough_information`. Returns a new dict; leaves input untouched when nothing fires.
    """
    flagged = flagged_verdicts(verdicts, threshold=threshold)
    if not flagged:
        return generated

    g = dict(generated)
    flags = set(split_semicolon(g.get("risk_flags", ""))) - {"none"}
    flags.update({"non_original_image", "possible_manipulation", "manual_review_required"})
    g["risk_flags"] = ";".join(sorted(flags))
    g["valid_image"] = "false"
    if g.get("claim_status") == "supported":
        g["claim_status"] = "not_enough_information"
    g["supporting_image_ids"] = "none"

    cues = sorted({s for v in flagged for s in v.signals})[:3]
    ids = ", ".join(sorted({v.image_id for v in flagged}))
    note = (
        f"Authenticity check flagged likely AI-generated/manipulated image(s) [{ids}]"
        + (f": {'; '.join(cues)}" if cues else "")
        + "; evidence not trusted, routed to manual review. "
    )
    g["claim_status_justification"] = (note + str(g.get("claim_status_justification", "")))[:600]
    return g
