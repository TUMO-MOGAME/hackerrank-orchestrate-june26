"""Deterministic offline provider for tests and demos.

Returns a schema-valid decision without any network/API call. The defaults are valid
for ANY claim_object (object_part='unknown', issue_type='unknown'), so tests and
offline `--provider fake` runs never hit a real model. Override `fields` to script a
specific decision in a test.
"""

from __future__ import annotations

from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage
from claimreview.providers.base import AdjudicationResult, VisionProvider

_DEFAULT_FIELDS = {
    "evidence_standard_met": False,
    "evidence_standard_met_reason": "Offline fake provider — no model inspection performed.",
    "risk_flags": "manual_review_required",
    "issue_type": "unknown",
    "object_part": "unknown",
    "claim_status": "not_enough_information",
    "claim_status_justification": "Fake provider returns a neutral, schema-valid decision.",
    "supporting_image_ids": "none",
    "valid_image": True,
    "severity": "unknown",
}


class FakeProvider(VisionProvider):
    name = "fake"

    def __init__(self, fields: dict | None = None) -> None:
        self._fields = dict(_DEFAULT_FIELDS if fields is None else fields)

    def adjudicate(
        self,
        system_prompt: str,
        context: ClaimContext,
        images: list[LoadedImage],
    ) -> AdjudicationResult:
        return AdjudicationResult(fields=dict(self._fields), input_tokens=0, output_tokens=0)
