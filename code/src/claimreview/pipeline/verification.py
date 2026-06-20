"""Verification reconciliation: combine a first verdict with an independent second pass.

The second pass (prompts/verification.py) re-decides `claim_status` independently. This module
decides the FINAL status from the two opinions. Several policies are provided so the choice can
be settled empirically on the labeled sample (see evaluation/experiment_verify.py) rather than
by intuition.

Only `supported` / `contradicted` verdicts that rest on USABLE images are worth verifying:
- `not_enough_information` is already the cautious answer — re-checking cannot improve it.
- A `contradicted` driven by the authenticity layer (valid_image == false, fabricated image)
  is settled by provenance, not by visual re-reading, so it is left untouched.
"""

from __future__ import annotations

# Reconciliation policies (string keys so they can come from config/CLI).
POLICY_SECOND = "second"                       # trust the second pass outright
POLICY_AGREE_ELSE_NEI = "agree_else_nei"       # agree -> keep; any disagreement -> NEI
POLICY_DOWNGRADE_CONTRADICTION = "downgrade_contradiction"  # only relax 1st-pass contradictions

POLICIES = (POLICY_SECOND, POLICY_AGREE_ELSE_NEI, POLICY_DOWNGRADE_CONTRADICTION)

_NEI = "not_enough_information"


def should_verify(row: dict) -> bool:
    """A row is worth a second pass only if it's a decisive verdict on usable images."""
    return (
        row.get("claim_status") in ("supported", "contradicted")
        and str(row.get("valid_image")).strip().lower() == "true"
    )


def reconcile_status(first: str, second: str, policy: str) -> str:
    """Return the final claim_status given the two passes and a reconciliation policy."""
    if first == second:
        return first

    if policy == POLICY_SECOND:
        return second

    if policy == POLICY_AGREE_ELSE_NEI:
        # Two independent reviewers disagree -> we are not certain -> say so.
        return _NEI

    if policy == POLICY_DOWNGRADE_CONTRADICTION:
        # Targeted fix for over-contradiction: a 1st-pass `contradicted` only stands if the
        # second pass also contradicts; otherwise adopt the (more lenient) second opinion.
        # A 1st-pass `supported` is left as-is unless the second pass positively contradicts
        # it, in which case we step down to NEI rather than flip outright.
        if first == "contradicted":
            return second  # second is supported or NEI -> relax the contradiction
        if first == "supported" and second == "contradicted":
            return _NEI    # genuine conflict on a support call -> not certain
        return first

    raise ValueError(f"unknown reconciliation policy: {policy!r}")


def apply_verification(row: dict, second_status: str, policy: str) -> dict:
    """Return a new row with claim_status reconciled and dependent fields kept consistent.

    If the verdict changes, dependent fields are nudged to stay schema-consistent:
    - moving to `not_enough_information` clears supporting ids, lowers evidence_standard_met,
      and adds `manual_review_required`;
    - the justification is annotated so the change is auditable.
    """
    first = row.get("claim_status")
    final = reconcile_status(first, second_status, policy)
    if final == first:
        return row

    out = dict(row)
    out["claim_status"] = final
    if final == _NEI:
        out["supporting_image_ids"] = "none"
        out["evidence_standard_met"] = "false"
        flags = [f for f in str(out.get("risk_flags", "")).split(";") if f and f != "none"]
        if "manual_review_required" not in flags:
            flags.append("manual_review_required")
        out["risk_flags"] = ";".join(flags) if flags else "manual_review_required"
    out["claim_status_justification"] = (
        f"[verified: {first}->{final}] " + str(out.get("claim_status_justification", ""))
    ).strip()
    return out
