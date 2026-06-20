"""Context assembly tests."""

from __future__ import annotations

from claimreview.context.assembler import (
    assemble_context,
    select_evidence_requirements,
)

REQUIREMENTS = [
    {"claim_object": "all", "applies_to": "general", "minimum_image_evidence": "general rule"},
    {"claim_object": "car", "applies_to": "dent or scratch", "minimum_image_evidence": "car rule"},
    {"claim_object": "laptop", "applies_to": "screen", "minimum_image_evidence": "laptop rule"},
]


def test_select_requirements_matches_object_or_all():
    selected = select_evidence_requirements("car", REQUIREMENTS)
    objs = {r["claim_object"] for r in selected}
    assert objs == {"car", "all"}
    assert not any(r["claim_object"] == "laptop" for r in selected)


def test_assemble_context_includes_history_and_requirements():
    claim = {
        "user_id": "user_001",
        "image_paths": "images/test/case_001/img_1.jpg",
        "user_claim": "Customer: rear bumper dent.",
        "claim_object": "car",
    }
    history = {"user_001": {
        "past_claim_count": "2", "accept_claim": "2", "manual_review_claim": "0",
        "rejected_claim": "0", "last_90_days_claim_count": "1",
        "history_flags": "none", "history_summary": "Low-risk user",
    }}
    ctx = assemble_context(claim, history, REQUIREMENTS)
    assert ctx.claim_object == "car"
    assert "Low-risk user" in ctx.history_text
    assert "car rule" in ctx.evidence_requirements_text
    assert "laptop rule" not in ctx.evidence_requirements_text


def test_assemble_context_handles_unknown_user():
    claim = {
        "user_id": "ghost", "image_paths": "x.jpg",
        "user_claim": "hi", "claim_object": "package",
    }
    ctx = assemble_context(claim, {}, REQUIREMENTS)
    assert "No prior history" in ctx.history_text
