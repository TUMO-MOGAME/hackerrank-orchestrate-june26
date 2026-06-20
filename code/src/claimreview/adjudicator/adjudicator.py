"""Adjudicator: turn one claim into one validated output row.

Orchestrates a single claim end-to-end (no batching concerns here):
  load images -> assemble context -> provider.adjudicate(system_prompt, context, images)
  -> repair/clamp/ground the 10 generated fields -> merge the 4 passthrough columns.

Batching, throttling, retry and caching live in pipeline/ so this stays pure and
unit-testable with a FakeProvider. Provider/transport errors are intentionally NOT
caught here — they propagate so the pipeline's retry layer can act on them. The only
in-adjudicator degradation is for claims with no usable images (no point spending a
model call), which yields a safe, schema-valid `not_enough_information` row.
"""

from __future__ import annotations

from claimreview.authenticity.detector import (
    DEFAULT_THRESHOLD,
    AuthenticityDetector,
    apply_authenticity,
)
from claimreview.context.assembler import assemble_context
from claimreview.io.images import LoadedImage, load_images
from claimreview.providers.base import VisionProvider
from claimreview.schema.output_schema import (
    INPUT_PASSTHROUGH_COLUMNS,
    OUTPUT_COLUMNS,
    repair_generated_fields,
)


def degraded_fields(reason: str, *, risk_flag: str = "manual_review_required") -> dict:
    """A safe, schema-valid set of the 10 generated fields for an un-adjudicable claim.

    Used when no usable images could be loaded: nothing is asserted about damage, the
    image set is marked unusable, and the claim is routed to manual review.
    """
    return {
        "evidence_standard_met": "false",
        "evidence_standard_met_reason": reason,
        "risk_flags": risk_flag,
        "issue_type": "unknown",
        "object_part": "unknown",
        "claim_status": "not_enough_information",
        "claim_status_justification": reason,
        "supporting_image_ids": "none",
        "valid_image": "false",
        "severity": "unknown",
    }


def adjudicate_claim(
    claim: dict,
    user_history: dict[str, dict],
    requirements: list[dict],
    provider: VisionProvider,
    system_prompt: str,
    dataset_root: str,
    *,
    detector: AuthenticityDetector | None = None,
    auth_threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Produce one fully-populated, schema-valid output row (14 columns) for a claim.

    `system_prompt` is the already-rendered system instruction for this claim's
    `claim_object` (the runner calls the strategy's ``build_system_prompt`` per object).
    The returned dict is keyed by all 14 OUTPUT_COLUMNS in order, with the 4 input
    columns passed through verbatim.

    If `detector` is given, every loaded image is also screened for AI-generation /
    manipulation and the verdict is merged into the graded fields (risk_flags,
    valid_image, claim_status) via the conservative `apply_authenticity` policy.
    """
    images = load_images(claim.get("image_paths", ""), dataset_root)
    return adjudicate_with_images(
        claim, user_history, requirements, provider, system_prompt, images,
        detector=detector, auth_threshold=auth_threshold,
    )


def adjudicate_with_images(
    claim: dict,
    user_history: dict[str, dict],
    requirements: list[dict],
    provider: VisionProvider,
    system_prompt: str,
    images: list[LoadedImage],
    *,
    detector: AuthenticityDetector | None = None,
    auth_threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """Core adjudication for already-loaded images (shared by the batch runner and the API).

    Same contract as `adjudicate_claim` but takes pre-loaded `images` instead of reading them
    from disk — so the deployable endpoint can pass inline (base64) images while the batch
    path reads files. Degrades safely to a manual-review row when `images` is empty.
    """
    claim_object = claim.get("claim_object", "")
    if not images:
        generated = degraded_fields(
            "No usable images could be loaded for this claim; cannot adjudicate from images."
        )
    else:
        context = assemble_context(claim, user_history, requirements)
        valid_image_ids = {img.image_id for img in images}
        result = provider.adjudicate(system_prompt, context, images)
        generated = repair_generated_fields(result.fields, claim_object, valid_image_ids)
        if detector is not None:
            verdicts = detector.assess(images)
            generated = apply_authenticity(generated, verdicts, threshold=auth_threshold)

    row = {col: claim.get(col, "") for col in INPUT_PASSTHROUGH_COLUMNS}
    row.update(generated)
    return {col: row[col] for col in OUTPUT_COLUMNS}
