"""Batch runner: iterate claims -> adjudicate each -> collect rows.

Applies operational resilience around each claim: cache lookup, retry-with-backoff, and a
throttle between live calls. One claim's failure never aborts the batch — after retries are
exhausted it emits a safe degraded row (valid_image=false, manual_review_required) and moves
on. The deployable API endpoint calls `adjudicate_claim` directly (one claim, no batch loop),
so the core logic stays shared.

Instrumentation (model calls, tokens, cache hits, auth calls, elapsed, images) is collected
in `BatchStats` to feed the graded operational analysis in evaluation_report.md.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from claimreview.adjudicator.adjudicator import adjudicate_claim, degraded_fields
from claimreview.authenticity.detector import DEFAULT_THRESHOLD, AuthenticityDetector
from claimreview.context.assembler import format_history
from claimreview.io.images import split_image_paths
from claimreview.pipeline.cache import ResponseCache
from claimreview.pipeline.retry import with_backoff
from claimreview.pipeline.throttle import sleep_ms
from claimreview.providers.base import VisionProvider
from claimreview.schema.output_schema import (
    GENERATED_COLUMNS,
    INPUT_PASSTHROUGH_COLUMNS,
    OUTPUT_COLUMNS,
)


class CountingProvider(VisionProvider):
    """Wrap a provider to tally calls and tokens (for the operational report)."""

    def __init__(self, inner: VisionProvider) -> None:
        self._inner = inner
        self.name = inner.name
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def adjudicate(self, system_prompt, context, images):
        self.calls += 1
        result = self._inner.adjudicate(system_prompt, context, images)
        self.input_tokens += result.input_tokens or 0
        self.output_tokens += result.output_tokens or 0
        return result


@dataclass
class BatchStats:
    claims: int = 0
    images: int = 0
    cache_hits: int = 0
    model_calls: int = 0
    auth_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    failures: int = 0
    elapsed_s: float = 0.0


@dataclass
class BatchResult:
    rows: list[dict]
    stats: BatchStats


def _row_from_generated(claim: dict, generated: dict) -> dict:
    row = {col: claim.get(col, "") for col in INPUT_PASSTHROUGH_COLUMNS}
    row.update(generated)
    return {col: row[col] for col in OUTPUT_COLUMNS}


def run_batch(
    claims: list[dict],
    user_history: dict[str, dict],
    requirements: list[dict],
    provider: VisionProvider,
    system_prompt_for: Callable[[str], str],
    dataset_root: str,
    *,
    detector: AuthenticityDetector | None = None,
    auth_threshold: float = DEFAULT_THRESHOLD,
    throttle_ms: int = 0,
    max_retries: int = 3,
    cache: ResponseCache | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> BatchResult:
    """Process all claims into output rows (input order). Returns rows + BatchStats."""
    counting = CountingProvider(provider)
    stats = BatchStats(claims=len(claims))
    rows: list[dict] = []
    total = len(claims)
    start = time.monotonic()
    # Cache identity must include the model that produced a row, else switching providers
    # (e.g. fake -> gemini) would wrongly reuse stale cached results for the same claim.
    provider_id = f"{provider.name}:{getattr(provider, 'model', '')}"

    for idx, claim in enumerate(claims):
        stats.images += len(split_image_paths(claim.get("image_paths", "")))
        claim_object = claim.get("claim_object", "")
        system_prompt = system_prompt_for(claim_object)

        key = None
        if cache is not None and cache.enabled:
            history_text = format_history(user_history.get(claim.get("user_id")))
            key = ResponseCache.make_key(
                provider_id,
                system_prompt,
                claim.get("image_paths", ""),
                claim.get("user_claim", ""),
                claim_object,
                history_text,
            )
            cached = cache.get(key)
            if cached is not None:
                stats.cache_hits += 1
                rows.append(_row_from_generated(claim, cached))
                if on_progress:
                    on_progress(idx + 1, total)
                continue

        def _do(_claim=claim, _sp=system_prompt):
            return adjudicate_claim(
                _claim, user_history, requirements, counting, _sp, dataset_root,
                detector=detector, auth_threshold=auth_threshold,
            )

        try:
            row = with_backoff(_do, max_retries=max_retries)
        except Exception as exc:  # noqa: BLE001 — resilience: never abort the batch
            stats.failures += 1
            row = _row_from_generated(
                claim,
                degraded_fields(f"Adjudication failed after retries: {type(exc).__name__}"),
            )

        if key is not None:
            cache.set(key, {col: row[col] for col in GENERATED_COLUMNS})
        rows.append(row)
        if throttle_ms:
            sleep_ms(throttle_ms)
        if on_progress:
            on_progress(idx + 1, total)

    stats.elapsed_s = time.monotonic() - start
    stats.model_calls = counting.calls
    stats.input_tokens = counting.input_tokens
    stats.output_tokens = counting.output_tokens
    if detector is not None:
        stats.auth_calls = int(getattr(detector, "calls", 0))
    return BatchResult(rows=rows, stats=stats)
