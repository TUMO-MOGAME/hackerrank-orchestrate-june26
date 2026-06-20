"""Output contract: the 14 columns of output.csv, their order, and allowed values.

This module is the single source of truth for the submission schema defined in
`problem_statement.md`. The exact column ORDER below is mandatory — the evaluator
checks it. Allowed-value lists are used both to constrain the model (structured
output / prompt) and to validate every produced row before it is written.

NOTE: structure only — validation logic is stubbed (TODO in build step 1).
"""

from __future__ import annotations

# --- Column order (MUST match problem_statement.md exactly) -------------------
# First 4 are passed through verbatim from the input claims.csv row.
INPUT_PASSTHROUGH_COLUMNS = [
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
]

# The 10 fields the system generates per claim.
GENERATED_COLUMNS = [
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity",
]

OUTPUT_COLUMNS = INPUT_PASSTHROUGH_COLUMNS + GENERATED_COLUMNS  # 14, in order

# --- Allowed values (from problem_statement.md "Allowed values") --------------
CLAIM_OBJECTS = {"car", "laptop", "package"}

CLAIM_STATUS = {"supported", "contradicted", "not_enough_information"}

ISSUE_TYPES = {
    "dent", "scratch", "crack", "glass_shatter", "broken_part", "missing_part",
    "torn_packaging", "crushed_packaging", "water_damage", "stain", "none", "unknown",
}

SEVERITY = {"none", "low", "medium", "high", "unknown"}

OBJECT_PARTS = {
    "car": {
        "front_bumper", "rear_bumper", "door", "hood", "windshield", "side_mirror",
        "headlight", "taillight", "fender", "quarter_panel", "body", "unknown",
    },
    "laptop": {
        "screen", "keyboard", "trackpad", "hinge", "lid", "corner", "port", "base",
        "body", "unknown",
    },
    "package": {
        "box", "package_corner", "package_side", "seal", "label", "contents", "item",
        "unknown",
    },
}

# risk_flags is a semicolon-separated subset of these (or "none").
RISK_FLAGS = {
    "none", "blurry_image", "cropped_or_obstructed", "low_light_or_glare",
    "wrong_angle", "wrong_object", "wrong_object_part", "damage_not_visible",
    "claim_mismatch", "possible_manipulation", "non_original_image",
    "text_instruction_present", "user_history_risk", "manual_review_required",
}


def generated_fields_json_schema(claim_object: str) -> dict:
    """JSON Schema for the 10 generated fields, used to constrain structured output.

    object_part is enum-constrained to the values valid for `claim_object`. risk_flags
    and supporting_image_ids are free strings (semicolon-separated) since they are lists;
    the prompt enforces their vocabulary and validate_row double-checks. Booleans are real
    JSON booleans; the adjudicator normalizes them to 'true'/'false' for the CSV.
    """
    parts = sorted(OBJECT_PARTS.get(claim_object, {"unknown"}))
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(GENERATED_COLUMNS),
        "properties": {
            "evidence_standard_met": {"type": "boolean"},
            "evidence_standard_met_reason": {"type": "string"},
            "risk_flags": {"type": "string"},
            "issue_type": {"type": "string", "enum": sorted(ISSUE_TYPES)},
            "object_part": {"type": "string", "enum": parts},
            "claim_status": {"type": "string", "enum": sorted(CLAIM_STATUS)},
            "claim_status_justification": {"type": "string"},
            "supporting_image_ids": {"type": "string"},
            "valid_image": {"type": "boolean"},
            "severity": {"type": "string", "enum": sorted(SEVERITY)},
        },
    }


BOOL_STRINGS = {"true", "false"}


def normalize_bool(value) -> str | None:
    """Coerce a bool/str to the canonical CSV form 'true'/'false', or None if invalid."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        v = value.strip().lower()
        if v in BOOL_STRINGS:
            return v
    return None


def split_semicolon(value) -> list[str]:
    """Split a semicolon-separated field into trimmed, non-empty tokens (order preserved)."""
    return [t.strip() for t in str(value).split(";") if t.strip()]


def split_risk_flags(risk_flags: str) -> list[str]:
    """Split the semicolon-separated risk_flags field into trimmed, non-empty tokens."""
    return split_semicolon(risk_flags)


def repair_generated_fields(
    fields: dict, claim_object: str, valid_image_ids: set[str]
) -> dict:
    """Coerce raw model output into a schema-valid, grounded generated-fields dict.

    This is the safety net between the model and the CSV: it never raises and its result
    always passes ``validate_row`` AND the grounding tests. Specifically it
      - normalizes the two booleans to 'true'/'false' (default 'false' on garbage),
      - clamps closed enums (claim_status/issue_type/severity) to safe defaults,
      - clamps object_part to a value valid for ``claim_object`` (else 'unknown'),
      - filters risk_flags to the allowed vocab, de-dupes, and drops 'none' when other
        flags are present (default 'none' when empty),
      - GROUNDS supporting_image_ids to IDs that actually exist in this claim's image
        set (default 'none'), which is the anti-hallucination guard, and
      - guarantees the two free-text fields are non-empty.

    Closed enums are constrained at the provider layer (json_schema); this repair makes the
    guarantee hold for providers/models that don't strictly enforce the schema.
    """
    f = dict(fields or {})
    allowed_parts = OBJECT_PARTS.get(claim_object, {"unknown"})

    def _enum(key: str, allowed: set[str], default: str) -> str:
        v = f.get(key)
        return v if v in allowed else default

    # risk_flags: keep allowed tokens only, de-dupe, drop 'none' if mixed with others.
    flags = [t for t in split_semicolon(f.get("risk_flags", "")) if t in RISK_FLAGS]
    flags = list(dict.fromkeys(flags))
    if len(flags) > 1:
        flags = [t for t in flags if t != "none"]
    risk_flags = ";".join(flags) if flags else "none"

    claim_status = _enum("claim_status", CLAIM_STATUS, "not_enough_information")
    valid_image = normalize_bool(f.get("valid_image")) or "false"

    # supporting_image_ids: ground to IDs that actually exist in the claim's image set.
    cited = split_semicolon(f.get("supporting_image_ids", ""))
    grounded = list(dict.fromkeys(i for i in cited if i in valid_image_ids))
    supporting = ";".join(grounded) if grounded else "none"

    # Consistency guard: a supported/contradicted decision made on USABLE images must rest on
    # image evidence, so it cannot cite 'none'. If the model reached such a verdict but cited
    # no valid IDs (bad IDs, free text, or 'none'), fall back to the full image set rather than
    # emit a contradictory 'supported'+'none' pair. We skip this when valid_image is false (the
    # image set is unusable — e.g. AI-generated/manipulated — so 'none' is the correct citation)
    # and for not_enough_information (which legitimately cites none).
    if (
        claim_status in ("supported", "contradicted")
        and valid_image == "true"
        and supporting == "none"
        and valid_image_ids
    ):
        ordered = sorted(
            valid_image_ids,
            key=lambda s: (int("".join(c for c in s if c.isdigit()) or "0"), s),
        )
        supporting = ";".join(ordered)

    reason = str(f.get("evidence_standard_met_reason", "")).strip() or "No reason provided."
    justification = (
        str(f.get("claim_status_justification", "")).strip() or "No justification provided."
    )

    return {
        "evidence_standard_met": normalize_bool(f.get("evidence_standard_met")) or "false",
        "evidence_standard_met_reason": reason,
        "risk_flags": risk_flags,
        "issue_type": _enum("issue_type", ISSUE_TYPES, "unknown"),
        "object_part": f.get("object_part") if f.get("object_part") in allowed_parts else "unknown",
        "claim_status": claim_status,
        "claim_status_justification": justification,
        "supporting_image_ids": supporting,
        "valid_image": valid_image,
        "severity": _enum("severity", SEVERITY, "unknown"),
    }


def validate_row(row: dict, claim_object: str) -> list[str]:
    """Return a list of validation problems for a generated output row (empty = valid).

    Checks the 10 generated fields against the allowed-value contract. Does NOT check
    that supporting_image_ids exist in the claim's image set — that needs the image
    list and is asserted by the grounding tests.
    """
    problems: list[str] = []

    # Required keys present.
    for col in GENERATED_COLUMNS:
        if col not in row:
            problems.append(f"missing field: {col}")
    if problems:
        return problems

    # Booleans.
    for col in ("evidence_standard_met", "valid_image"):
        if normalize_bool(row[col]) is None:
            problems.append(f"{col} must be true/false, got {row[col]!r}")

    # Closed enums.
    if row["claim_status"] not in CLAIM_STATUS:
        problems.append(f"claim_status invalid: {row['claim_status']!r}")
    if row["issue_type"] not in ISSUE_TYPES:
        problems.append(f"issue_type invalid: {row['issue_type']!r}")
    if row["severity"] not in SEVERITY:
        problems.append(f"severity invalid: {row['severity']!r}")

    # object_part depends on claim_object.
    allowed_parts = OBJECT_PARTS.get(claim_object)
    if allowed_parts is None:
        problems.append(f"unknown claim_object: {claim_object!r}")
    elif row["object_part"] not in allowed_parts:
        problems.append(
            f"object_part {row['object_part']!r} not valid for {claim_object}"
        )

    # risk_flags: every token must be allowed; 'none' must not be mixed with others.
    flags = split_risk_flags(row["risk_flags"])
    if not flags:
        problems.append("risk_flags empty (use 'none')")
    else:
        unknown = [f for f in flags if f not in RISK_FLAGS]
        if unknown:
            problems.append(f"unknown risk_flags: {unknown}")
        if "none" in flags and len(flags) > 1:
            problems.append("risk_flags 'none' must not be combined with other flags")

    # Non-empty justification/reason text.
    for col in ("evidence_standard_met_reason", "claim_status_justification"):
        if not str(row[col]).strip():
            problems.append(f"{col} must not be empty")

    return problems
