"""Schema contract tests — these can pass as soon as the schema is implemented."""

from __future__ import annotations

import pytest

from claimreview.schema.output_schema import (
    GENERATED_COLUMNS,
    INPUT_PASSTHROUGH_COLUMNS,
    OUTPUT_COLUMNS,
    normalize_bool,
    repair_generated_fields,
    split_risk_flags,
    validate_row,
)


def test_output_has_14_columns_in_order():
    assert OUTPUT_COLUMNS == INPUT_PASSTHROUGH_COLUMNS + GENERATED_COLUMNS
    assert len(OUTPUT_COLUMNS) == 14
    assert OUTPUT_COLUMNS[0] == "user_id"
    assert OUTPUT_COLUMNS[-1] == "severity"


def _valid_row() -> dict:
    return {
        "evidence_standard_met": "true",
        "evidence_standard_met_reason": "Rear bumper visible; dent verifiable.",
        "risk_flags": "none",
        "issue_type": "dent",
        "object_part": "rear_bumper",
        "claim_status": "supported",
        "claim_status_justification": "img_1 shows a dent on the rear bumper.",
        "supporting_image_ids": "img_1",
        "valid_image": "true",
        "severity": "medium",
    }


def test_valid_row_passes():
    assert validate_row(_valid_row(), "car") == []


def test_supported_without_valid_citation_falls_back_to_image_set():
    # Model said 'supported' but cited a non-existent / wrongly-formatted id -> grounding
    # would wipe it to 'none'. The consistency guard must instead cite the real image set,
    # never leaving a 'supported' verdict with supporting_image_ids='none'.
    fields = {
        "evidence_standard_met": True,
        "evidence_standard_met_reason": "Damage visible.",
        "risk_flags": "none",
        "issue_type": "dent",
        "object_part": "front_bumper",
        "claim_status": "supported",
        "claim_status_justification": "The images clearly show the dent.",
        "supporting_image_ids": "none",  # model cited nothing usable
        "valid_image": True,
        "severity": "medium",
    }
    out = repair_generated_fields(fields, "car", {"img_1", "img_2", "img_3"})
    assert out["claim_status"] == "supported"
    assert out["supporting_image_ids"] == "img_1;img_2;img_3"  # natural order, all cited


def test_contradicted_with_unusable_images_keeps_none():
    # When the image set is unusable (valid_image=false, e.g. AI-generated), a contradicted
    # verdict legitimately cites 'none' — the guard must NOT fabricate citations.
    fields = {
        "claim_status": "contradicted",
        "supporting_image_ids": "none",
        "valid_image": False,
        "evidence_standard_met": False,
        "risk_flags": "non_original_image",
    }
    out = repair_generated_fields(fields, "laptop", {"img_1", "img_2"})
    assert out["claim_status"] == "contradicted"
    assert out["valid_image"] == "false"
    assert out["supporting_image_ids"] == "none"


def test_not_enough_information_may_cite_none():
    fields = {
        "claim_status": "not_enough_information",
        "supporting_image_ids": "none",
        "valid_image": False,
        "evidence_standard_met": False,
    }
    out = repair_generated_fields(fields, "car", {"img_1"})
    assert out["supporting_image_ids"] == "none"


@pytest.mark.parametrize("value,expected", [
    (True, "true"), (False, "false"), ("True", "true"), (" FALSE ", "false"),
    ("yes", None), ("", None), (1, None),
])
def test_normalize_bool(value, expected):
    assert normalize_bool(value) == expected


def test_split_risk_flags():
    assert split_risk_flags("blurry_image; wrong_angle ;") == ["blurry_image", "wrong_angle"]
    assert split_risk_flags("none") == ["none"]


def test_bad_claim_status_rejected():
    row = _valid_row()
    row["claim_status"] = "approved"
    assert any("claim_status" in p for p in validate_row(row, "car"))


def test_object_part_must_match_object():
    # 'screen' is a laptop part, invalid for a car claim.
    row = _valid_row()
    row["object_part"] = "screen"
    assert any("object_part" in p for p in validate_row(row, "car"))
    # ...but valid for a laptop.
    row2 = _valid_row()
    row2["object_part"] = "screen"
    row2["issue_type"] = "crack"
    assert validate_row(row2, "laptop") == []


def test_unknown_risk_flag_rejected():
    row = _valid_row()
    row["risk_flags"] = "blurry_image;teleported"
    assert any("unknown risk_flags" in p for p in validate_row(row, "car"))


def test_none_not_combined_with_other_flags():
    row = _valid_row()
    row["risk_flags"] = "none;blurry_image"
    assert any("none" in p for p in validate_row(row, "car"))


def test_missing_field_reported():
    row = _valid_row()
    del row["severity"]
    assert any("severity" in p for p in validate_row(row, "car"))
