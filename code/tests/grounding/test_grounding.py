"""Grounding tests — the anti-hallucination guard (mirrors FrameFlow's grounding layer).

Every output row the system produces over the sample set must:
  - use only allowed values for claim_status / issue_type / severity / risk_flags
  - use an object_part valid for its claim_object
  - reference supporting_image_ids that actually exist in the claim's image set
  - pass through user_id / image_paths / user_claim / claim_object unchanged

These run the real adjudicator with a FakeProvider deliberately scripted to HALLUCINATE
(a non-existent image ID, an out-of-vocabulary object_part, a bad enum). The point is to
prove the adjudicator's repair/grounding layer scrubs bad model output before it reaches
output.csv — not just that a well-behaved model happens to comply.
"""

from __future__ import annotations

from claimreview.adjudicator.adjudicator import adjudicate_claim
from claimreview.io.images import image_id_from_path, split_image_paths
from claimreview.prompts.strategy_a_zero_shot import build_system_prompt
from claimreview.providers.fake_provider import FakeProvider
from claimreview.schema.output_schema import (
    INPUT_PASSTHROUGH_COLUMNS,
    OBJECT_PARTS,
    OUTPUT_COLUMNS,
    split_semicolon,
    validate_row,
)

# Adversarial model output: a hallucinated image ID, an out-of-vocab part, bad enums,
# and a forbidden risk_flags combo. A correct adjudicator must scrub ALL of this.
_HALLUCINATED_FIELDS = {
    "evidence_standard_met": "TRUE",                 # wrong case -> normalized
    "evidence_standard_met_reason": "",              # empty -> filled
    "risk_flags": "none;blurry_image;teleported",    # 'none' mixed + bogus token
    "issue_type": "exploded",                        # out of vocab -> unknown
    "object_part": "flux_capacitor",                 # out of vocab -> unknown
    "claim_status": "approved",                      # out of vocab -> not_enough_information
    "claim_status_justification": "   ",             # blank -> filled
    "supporting_image_ids": "img_1;img_99999",       # img_99999 never exists -> grounded out
    "valid_image": "yes",                            # not a bool -> 'false'
    "severity": "catastrophic",                      # out of vocab -> unknown
}


def _adjudicate_all(sample_dataset, fields: dict) -> list[dict]:
    provider = FakeProvider(fields)
    rows = []
    for claim in sample_dataset["claims"]:
        rows.append(
            adjudicate_claim(
                claim,
                sample_dataset["user_history"],
                sample_dataset["requirements"],
                provider,
                build_system_prompt(claim["claim_object"]),
                sample_dataset["dataset_root"],
            )
        )
    return rows


def test_supporting_image_ids_exist_in_claim(sample_dataset):
    rows = _adjudicate_all(sample_dataset, _HALLUCINATED_FIELDS)
    assert rows, "no sample claims adjudicated"
    for row in rows:
        claim_ids = {image_id_from_path(p) for p in split_image_paths(row["image_paths"])}
        cited = split_semicolon(row["supporting_image_ids"])
        # 'none' is the sentinel for "no supporting image"; otherwise every cited ID must
        # be a real image attached to THIS claim — never the hallucinated img_99999.
        for image_id in cited:
            if image_id == "none":
                continue
            assert image_id in claim_ids, (
                f"hallucinated supporting_image_id {image_id!r} not in {sorted(claim_ids)}"
            )


def test_only_allowed_values_emitted(sample_dataset):
    rows = _adjudicate_all(sample_dataset, _HALLUCINATED_FIELDS)
    assert rows
    for row in rows:
        problems = validate_row(row, row["claim_object"])
        assert problems == [], f"row failed schema validation: {problems}"
        assert row["object_part"] in OBJECT_PARTS[row["claim_object"]]
        # Adversarial input had no valid enum values, so everything collapses to safe defaults.
        assert row["claim_status"] == "not_enough_information"
        assert row["issue_type"] == "unknown"
        assert row["object_part"] == "unknown"
        assert row["severity"] == "unknown"
        assert "teleported" not in row["risk_flags"]


def test_passthrough_columns_unchanged(sample_dataset):
    rows = _adjudicate_all(sample_dataset, _HALLUCINATED_FIELDS)
    for claim, row in zip(sample_dataset["claims"], rows, strict=True):
        for col in INPUT_PASSTHROUGH_COLUMNS:
            assert row[col] == claim[col], f"passthrough column {col} mutated"
        assert list(row.keys()) == OUTPUT_COLUMNS  # 14 columns, exact order


def test_clean_model_output_is_grounded(sample_dataset, fake_generated_fields):
    """A well-behaved model that cites a real image keeps it; a clean run stays valid."""
    rows = _adjudicate_all(sample_dataset, fake_generated_fields)
    for row in rows:
        assert validate_row(row, row["claim_object"]) == []
