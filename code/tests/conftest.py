"""Pytest bootstrap: hermetic env + a FakeProvider so unit tests never hit a real API.

Sets dummy env vars before app import and exposes fixtures for canned model output.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

# Repo root = code/tests/ -> code/ -> repo
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "dataset"


@pytest.fixture
def dataset_dir() -> Path:
    return DATASET_DIR


@pytest.fixture
def has_dataset() -> bool:
    return (DATASET_DIR / "claims.csv").is_file()


@pytest.fixture
def fake_generated_fields() -> dict:
    """A schema-valid set of the 10 generated fields for use in tests."""
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


@pytest.fixture
def fake_provider(fake_generated_fields):
    """A FakeProvider returning canned, schema-valid fields (no network/API)."""
    from claimreview.providers.fake_provider import FakeProvider

    return FakeProvider(fake_generated_fields)


@pytest.fixture
def sample_dataset(has_dataset):
    """Loaded sample inputs (claims, history, requirements) + dataset root, or skip.

    Skips the test if the sample dataset is not checked out, so the suite stays green in
    minimal/CI checkouts that ship only the code.
    """
    sample_csv = DATASET_DIR / "sample_claims.csv"
    if not sample_csv.is_file():
        pytest.skip("sample_claims.csv not present")

    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )

    claims = read_sample_claims(str(sample_csv))
    history = read_user_history(str(DATASET_DIR / "user_history.csv"))
    requirements = read_evidence_requirements(str(DATASET_DIR / "evidence_requirements.csv"))
    return {
        "claims": claims,
        "user_history": history,
        "requirements": requirements,
        "dataset_root": str(DATASET_DIR),
    }
