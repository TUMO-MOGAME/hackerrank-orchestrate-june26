"""Per-claim context assembly.

For each claim, builds the textual context block the model reasons over:
  - the user_claim chat transcript (may be multilingual, e.g. Hindi/Hinglish)
  - the matched user_history profile (risk context only — never overrides images)
  - the relevant evidence_requirements (by claim_object, plus rules that apply to 'all')

The truth hierarchy is enforced in the PROMPT (see prompts/), not here; this module
only gathers and formats the inputs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimContext:
    user_id: str
    claim_object: str
    user_claim: str
    history_text: str                # formatted history, or "No prior history on file."
    evidence_requirements_text: str  # matched minimum_image_evidence lines
    image_paths: str


def select_evidence_requirements(claim_object: str, requirements: list[dict]) -> list[dict]:
    """Pick rows whose claim_object matches the claim's object (or the universal 'all').

    Issue-family ('applies_to') is not filtered here because the issue is unknown before
    the model inspects the images — all applicable rules are surfaced and the prompt lets
    the model apply the relevant one.
    """
    return [
        r for r in requirements
        if r.get("claim_object") in (claim_object, "all")
    ]


def format_history(history: dict | None) -> str:
    """Render a user_history row into a compact risk-context block."""
    if not history:
        return "No prior history on file."
    flags = history.get("history_flags", "none")
    summary = history.get("history_summary", "")
    return (
        f"past_claims={history.get('past_claim_count', '0')}, "
        f"accepted={history.get('accept_claim', '0')}, "
        f"manual_review={history.get('manual_review_claim', '0')}, "
        f"rejected={history.get('rejected_claim', '0')}, "
        f"last_90_days={history.get('last_90_days_claim_count', '0')}; "
        f"flags={flags}; summary={summary}"
    )


def format_requirements(requirements: list[dict]) -> str:
    """Render selected evidence requirements as bullet lines."""
    if not requirements:
        return "No specific evidence requirements; apply general reviewability."
    return "\n".join(
        f"- ({r.get('applies_to', 'general')}) {r.get('minimum_image_evidence', '')}"
        for r in requirements
    )


def assemble_context(
    claim: dict,
    user_history: dict[str, dict],
    requirements: list[dict],
) -> ClaimContext:
    """Build the ClaimContext for one claim row."""
    claim_object = claim["claim_object"]
    selected = select_evidence_requirements(claim_object, requirements)
    return ClaimContext(
        user_id=claim["user_id"],
        claim_object=claim_object,
        user_claim=claim["user_claim"],
        history_text=format_history(user_history.get(claim["user_id"])),
        evidence_requirements_text=format_requirements(selected),
        image_paths=claim["image_paths"],
    )
