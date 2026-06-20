"""Prompt strategies.

The evaluation must compare at least two strategies (problem_statement.md / README).
Each strategy is a builder that renders the system prompt (and any few-shot examples)
for a ClaimContext. Keeping them as named, versioned objects lets evaluation/compare.py
run the same claims through each and tabulate metrics.

Registered strategies:
  - strategy_a_zero_shot : minimal persona + rules of engagement, zero-shot.
  - strategy_b_rules_fewshot : adds explicit decision rubric + a few labeled examples
    drawn from sample_claims.csv (NOT from the test set).
  - strategy_c_contradiction_aware : explicit status-decision gate (contradiction-focused).
  - strategy_d_image_grounded : per-image inventory + anchor-to-claimed-part (targets the
    multi-image over-contradiction error found in error analysis).
"""

from __future__ import annotations

from claimreview.prompts import (
    strategy_a_zero_shot,
    strategy_b_rules_fewshot,
    strategy_c_contradiction_aware,
    strategy_d_image_grounded,
)

STRATEGIES = {
    "a_zero_shot": strategy_a_zero_shot,
    "b_rules_fewshot": strategy_b_rules_fewshot,
    "c_contradiction_aware": strategy_c_contradiction_aware,
    "d_image_grounded": strategy_d_image_grounded,
}
