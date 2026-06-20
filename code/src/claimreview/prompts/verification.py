"""Verification strategy — an independent second-opinion pass on `claim_status`.

A first adjudicator (strategy A) already produced a full decision. This prompt drives a
SECOND, independent look whose only job is to get `claim_status` right, as a calibration
check against the first pass. It is deliberately even-handed: the known failure mode of the
strong model is *over-contradiction* (calling `contradicted` when the images are merely
unclear / a different angle), so this prompt makes `contradicted` EARN its place while still
catching genuine refutations.

It reuses the standard 10-field structured schema (so the provider/repair/cache layers are
unchanged); only `claim_status` (and its supporting ids/justification) are consumed by the
reconciliation step. Independent by design — it is NOT told the first pass's verdict, to avoid
anchoring bias.
"""

from __future__ import annotations

from claimreview.context.assembler import ClaimContext
from claimreview.schema.output_schema import (
    CLAIM_STATUS,
    ISSUE_TYPES,
    OBJECT_PARTS,
    RISK_FLAGS,
    SEVERITY,
)

NAME = "verification"


def _vocab(values: set[str]) -> str:
    return ", ".join(sorted(values))


def build_system_prompt(claim_object: str) -> str:
    """Return the verification system instruction for a given claim object."""
    parts = OBJECT_PARTS.get(claim_object, {"unknown"})
    return f"""You are a senior claims auditor performing an INDEPENDENT second review of a \
{claim_object} damage claim. A junior reviewer has already given a verdict; your job is to \
decide the correct `claim_status` from scratch, looking only at the images and the claim. \
Be fair and evidence-driven, not adversarial.

=== HOW TO DECIDE claim_status (the only field that matters here) ===

SUPPORTED — the images clearly show the specific damage the customer claims, on the claimed
object and part. Reasonable real-world photos count; do not demand perfection.

CONTRADICTED — reserve this for when the images POSITIVELY PROVE the claim is false. Valid
reasons: the images show a different object or a different part than claimed; the claimed part
is clearly visible and plainly undamaged; or the authenticity check proved the image is
fabricated. A contradiction needs affirmative proof, not just absence of a clear shot.

NOT_ENOUGH_INFORMATION — the honest default whenever the images cannot settle it: the relevant
part isn't clearly visible, the photo is blurry / cropped / dark / wrong angle, or the damage
is simply ambiguous. **Do NOT mark `contradicted` for "I can't see the damage" — that is
`not_enough_information`.** Likewise do not mark `supported` if you are guessing.

Key calibration rule: the most common mistake is over-calling `contradicted`. If you find
yourself contradicting because the damage is hard to see (rather than because the images prove
the claim false), choose `not_enough_information` instead.

User history is risk context only and never changes the visual verdict.

=== ALLOWED VALUES (use the closest match; never invent a value) ===
claim_status: {_vocab(CLAIM_STATUS)}
issue_type: {_vocab(ISSUE_TYPES)}
object_part (for a {claim_object}): {_vocab(parts)}
severity: {_vocab(SEVERITY)}
risk_flags (semicolon-separated subset, or `none`): {_vocab(RISK_FLAGS)}

Fill every field consistently with your verdict. `supporting_image_ids` must be a subset of the
submitted image IDs, or `none`. Write a one-sentence, image-grounded justification. Return only
the required fields."""


def build_user_content(context: ClaimContext) -> str:
    """Same per-claim context block as strategy A (kept aligned for inspection)."""
    return (
        f"CLAIM OBJECT: {context.claim_object}\n\n"
        f"USER CONVERSATION (claim transcript):\n{context.user_claim}\n\n"
        f"USER HISTORY (risk context only — does not override images):\n{context.history_text}\n\n"
        f"MINIMUM EVIDENCE REQUIREMENTS:\n{context.evidence_requirements_text}\n\n"
        "Independently decide the claim_status strictly from the attached images."
    )
