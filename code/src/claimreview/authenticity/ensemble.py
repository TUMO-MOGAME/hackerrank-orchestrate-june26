"""Ensemble authenticity detector: combine backends, strongest AI verdict wins.

Detectors are consulted in order. A backend that flags AI with confidence ≥ `skip_above`
(e.g. deterministic C2PA provenance) SETTLES that image — later, costlier backends (the
Gemini VLM pass) are skipped for it, saving API calls. For images no backend settles, the
final verdict is the highest-confidence AI verdict seen, or — if none flagged AI — a real
verdict carrying the highest AI-likelihood observed (still below the action threshold).
Signals from every consulted backend are merged.
"""

from __future__ import annotations

from claimreview.authenticity.detector import AuthenticityDetector, ImageAuthenticity
from claimreview.io.images import LoadedImage


class EnsembleAuthenticityDetector(AuthenticityDetector):
    def __init__(
        self,
        detectors: list[AuthenticityDetector],
        *,
        skip_above: float = 0.9,
        name: str | None = None,
    ) -> None:
        self._detectors = list(detectors)
        self._skip_above = skip_above
        self.name = name or ("ensemble:" + "+".join(d.name for d in self._detectors))

    @property
    def calls(self) -> int:
        """Total inner API calls across backends that track them (e.g. memoized Gemini)."""
        return sum(int(getattr(d, "calls", 0)) for d in self._detectors)

    def assess(self, images: list[LoadedImage]) -> list[ImageAuthenticity]:
        collected: dict[int, list[ImageAuthenticity]] = {i: [] for i in range(len(images))}
        pending = list(range(len(images)))

        for detector in self._detectors:
            if not pending:
                break
            subset = [images[i] for i in pending]
            verdicts = detector.assess(subset)
            still_pending: list[int] = []
            for i, verdict in zip(pending, verdicts, strict=True):
                collected[i].append(verdict)
                settled = verdict.ai_generated and verdict.confidence >= self._skip_above
                if not settled:
                    still_pending.append(i)
            pending = still_pending

        out: list[ImageAuthenticity] = []
        for i, img in enumerate(images):
            verdicts = collected[i]
            signals = sorted({s for v in verdicts for s in v.signals})
            ai_verdicts = [v for v in verdicts if v.ai_generated]
            if ai_verdicts:
                best = max(ai_verdicts, key=lambda v: v.confidence)
                out.append(ImageAuthenticity(img.image_id, True, best.confidence, signals))
            else:
                conf = max((v.confidence for v in verdicts), default=0.0)
                out.append(ImageAuthenticity(img.image_id, False, conf, signals))
        return out
