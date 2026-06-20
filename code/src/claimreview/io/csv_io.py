"""CSV reading/writing for the claim-review pipeline.

Reads the four dataset CSVs and writes output.csv with the exact 14-column order
from `schema.output_schema.OUTPUT_COLUMNS`. All fields are quoted (QUOTE_ALL) to match
the dataset style so the evaluator parses it cleanly. Uses the stdlib csv module, which
handles embedded commas/pipes/quotes in the conversation transcripts correctly.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from claimreview.schema.output_schema import OUTPUT_COLUMNS

CLAIM_INPUT_COLUMNS = ["user_id", "image_paths", "user_claim", "claim_object"]


def _read_dicts(path: str) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_claims(path: str) -> list[dict]:
    """Read claims.csv (input-only): user_id, image_paths, user_claim, claim_object."""
    rows = _read_dicts(path)
    missing = [c for c in CLAIM_INPUT_COLUMNS if rows and c not in rows[0]]
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")
    return rows


def read_sample_claims(path: str) -> list[dict]:
    """Read sample_claims.csv (inputs + expected outputs) for evaluation."""
    return _read_dicts(path)


def read_user_history(path: str) -> dict[str, dict]:
    """Read user_history.csv keyed by user_id for O(1) lookup during context assembly."""
    return {row["user_id"]: row for row in _read_dicts(path)}


def read_evidence_requirements(path: str) -> list[dict]:
    """Read evidence_requirements.csv rows (requirement_id, claim_object, applies_to, ...)."""
    return _read_dicts(path)


def write_output(path: str, rows: Iterable[dict]) -> int:
    """Write output.csv using OUTPUT_COLUMNS order exactly. Returns the row count.

    Each row must contain all 14 columns. Extra keys are ignored; missing keys raise.
    """
    count = 0
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore", quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        for row in rows:
            missing = [c for c in OUTPUT_COLUMNS if c not in row]
            if missing:
                raise ValueError(f"output row missing columns: {missing}")
            writer.writerow({c: row[c] for c in OUTPUT_COLUMNS})
            count += 1
    return count
