"""CSV I/O tests — read the real dataset, round-trip the output schema."""

from __future__ import annotations

import csv

import pytest

from claimreview.io.csv_io import (
    read_claims,
    read_evidence_requirements,
    read_user_history,
    write_output,
)
from claimreview.schema.output_schema import OUTPUT_COLUMNS


def test_read_claims_has_input_columns(dataset_dir, has_dataset):
    if not has_dataset:
        pytest.skip("dataset not present")
    rows = read_claims(str(dataset_dir / "claims.csv"))
    assert len(rows) == 44
    assert set(rows[0]) >= {"user_id", "image_paths", "user_claim", "claim_object"}
    assert all(r["claim_object"] in {"car", "laptop", "package"} for r in rows)


def test_read_user_history_keyed_by_id(dataset_dir, has_dataset):
    if not has_dataset:
        pytest.skip("dataset not present")
    hist = read_user_history(str(dataset_dir / "user_history.csv"))
    assert "user_001" in hist
    assert "history_summary" in hist["user_001"]


def test_read_evidence_requirements(dataset_dir, has_dataset):
    if not has_dataset:
        pytest.skip("dataset not present")
    reqs = read_evidence_requirements(str(dataset_dir / "evidence_requirements.csv"))
    assert any(r["claim_object"] == "all" for r in reqs)
    assert any(r["claim_object"] == "car" for r in reqs)


def test_write_output_preserves_column_order(tmp_path):
    row = {c: "x" for c in OUTPUT_COLUMNS}
    out = tmp_path / "output.csv"
    n = write_output(str(out), [row, row])
    assert n == 2
    with out.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == OUTPUT_COLUMNS


def test_write_output_rejects_incomplete_row(tmp_path):
    bad = {"user_id": "u"}  # missing the rest
    with pytest.raises(ValueError):
        write_output(str(tmp_path / "o.csv"), [bad])
