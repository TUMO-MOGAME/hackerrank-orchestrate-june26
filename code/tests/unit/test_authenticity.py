"""Authenticity layer: merge policy, thresholding, memoization, adjudicator integration.

All offline — no API calls. The Gemini backend's network path is not exercised; only the
pure policy/memoization logic and the adjudicator wiring (with fakes) are tested.
"""

from __future__ import annotations

from claimreview.adjudicator.adjudicator import adjudicate_claim
from claimreview.authenticity.detector import (
    AuthenticityDetector,
    FakeAuthenticityDetector,
    ImageAuthenticity,
    MemoizingAuthenticityDetector,
    apply_authenticity,
    flagged_verdicts,
)
from claimreview.io.images import LoadedImage
from claimreview.providers.fake_provider import FakeProvider
from claimreview.schema.output_schema import split_semicolon, validate_row


def _img(image_id: str, data_b64: str = "QQ==") -> LoadedImage:
    return LoadedImage(
        image_id=image_id, rel_path=f"{image_id}.jpg", mime_type="image/jpeg", data_b64=data_b64
    )


def _supported_fields() -> dict:
    return {
        "evidence_standard_met": "true",
        "evidence_standard_met_reason": "Visible.",
        "risk_flags": "none",
        "issue_type": "dent",
        "object_part": "rear_bumper",
        "claim_status": "supported",
        "claim_status_justification": "img_1 shows a dent.",
        "supporting_image_ids": "img_1",
        "valid_image": "true",
        "severity": "medium",
    }


def test_clean_verdict_leaves_fields_untouched():
    fields = _supported_fields()
    verdicts = [ImageAuthenticity("img_1", ai_generated=False, confidence=0.0)]
    assert apply_authenticity(fields, verdicts) == fields


def test_below_threshold_does_not_fire():
    verdicts = [ImageAuthenticity("img_1", ai_generated=True, confidence=0.4)]
    assert flagged_verdicts(verdicts, threshold=0.7) == []
    assert apply_authenticity(_supported_fields(), verdicts, threshold=0.7) == _supported_fields()


def test_high_confidence_ai_flips_graded_fields():
    verdicts = [
        ImageAuthenticity("img_1", ai_generated=True, confidence=0.95, signals=["warped logo"])
    ]
    out = apply_authenticity(_supported_fields(), verdicts, threshold=0.7)
    flags = set(split_semicolon(out["risk_flags"]))
    assert "non_original_image" in flags
    assert "possible_manipulation" in flags
    assert "manual_review_required" in flags
    assert "none" not in flags
    assert out["valid_image"] == "false"
    assert out["claim_status"] == "not_enough_information"   # downgraded from supported
    assert out["supporting_image_ids"] == "none"
    assert "warped logo" in out["claim_status_justification"]
    # result must still be schema-valid
    assert validate_row(out, "car") == []


def test_memoization_assesses_each_unique_image_once():
    class CountingDetector(AuthenticityDetector):
        name = "counting"

        def __init__(self):
            self.seen = 0

        def assess(self, images):
            self.seen += len(images)
            return [ImageAuthenticity(i.image_id, False, 0.1) for i in images]

    inner = CountingDetector()
    memo = MemoizingAuthenticityDetector(inner)
    # same bytes under two IDs + a repeat: only the unique content is sent to the inner detector
    a, b = _img("img_1", "AAAA"), _img("img_2", "AAAA")
    memo.assess([a, b])
    memo.assess([a])
    assert inner.seen == 1          # one unique content hash
    assert memo.calls == 1
    # but every requested image still gets a verdict carrying its own id
    out = memo.assess([a, b])
    assert [v.image_id for v in out] == ["img_1", "img_2"]


def test_adjudicator_applies_detector(tmp_path):
    # one real on-disk image so load_images returns it
    root = tmp_path
    (root / "images").mkdir()
    img_path = root / "images" / "img_1.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
    claim = {
        "user_id": "u1",
        "image_paths": "images/img_1.jpg",
        "user_claim": "rear bumper dent",
        "claim_object": "car",
    }
    detector = FakeAuthenticityDetector(
        ai_generated=True, confidence=0.99, signals=["diffusion artifacts"]
    )
    row = adjudicate_claim(
        claim, {}, [], FakeProvider(_supported_fields()), "system", str(root), detector=detector
    )
    assert row["valid_image"] == "false"
    assert "non_original_image" in row["risk_flags"]
    assert row["claim_status"] == "not_enough_information"
    assert validate_row(row, "car") == []
