"""Strategy B — rules + few-shot examples.

Same persona and truth hierarchy as Strategy A, plus an explicit decision rubric and a few
WORKED examples covering each claim_status class. Hypothesis: this improves Macro-F1 on the
minority classes (contradicted / not_enough_information), which one-shot rules tend to miss.

Leakage note: the worked examples are HAND-WRITTEN illustrations, NOT rows copied from
sample_claims.csv (the eval set) or claims.csv (the test set). So evaluating either strategy
on the full sample set stays fair — the answers are not pre-baked into the prompt.
"""

from __future__ import annotations

from claimreview.prompts import strategy_a_zero_shot as _a

NAME = "b_rules_fewshot"

_RUBRIC = """

=== DECISION RUBRIC (apply after the Four Rules) ===
- claim_status = supported: the image clearly shows the claimed damage on the claimed part.
- claim_status = contradicted: the image clearly shows the claimed part is INTACT/undamaged,
  OR shows a different object/part than claimed. Add risk_flag `claim_mismatch` (and
  `wrong_object`/`wrong_object_part` when relevant).
- claim_status = not_enough_information: the claimed part is not visible, the image is
  unusable (blurry/cropped/dark/glare), or evidence is otherwise insufficient. Set
  evidence_standard_met=false and the matching quality risk_flag.
- severity: none (no damage) / low (cosmetic only) / medium (notable, may affect function) /
  high (severe or structural) / unknown (cannot tell).
- Always set user_history_risk when history shows elevated risk, but never let it change
  claim_status on its own (Rule R3).

=== WORKED EXAMPLES (illustrative; reason the same way on the real claim) ===
Example 1 — car, clear damage:
  Conversation: "Customer: long scratch on my front left door from a parking lot."
  Image shows a deep scratch across the door panel.
  -> {"evidence_standard_met": true, "risk_flags": "none", "issue_type": "scratch",
      "object_part": "door", "claim_status": "supported",
      "supporting_image_ids": "img_1", "valid_image": true, "severity": "low"}

Example 2 — laptop, part not visible:
  Conversation: "Customer: my laptop hinge is broken." Image shows the laptop closed from
  the top; the hinge is not visible.
  -> {"evidence_standard_met": false, "risk_flags": "cropped_or_obstructed;damage_not_visible",
      "issue_type": "unknown", "object_part": "hinge", "claim_status": "not_enough_information",
      "supporting_image_ids": "none", "valid_image": true, "severity": "unknown"}

Example 3 — package, claim contradicted by the image:
  Conversation: "Customer: the box arrived crushed and torn." Image shows an intact,
  undamaged sealed box.
  -> {"evidence_standard_met": true, "risk_flags": "claim_mismatch", "issue_type": "none",
      "object_part": "box", "claim_status": "contradicted",
      "supporting_image_ids": "img_1", "valid_image": true, "severity": "none"}
"""


def build_system_prompt(claim_object: str) -> str:
    """Strategy A's persona + rules, extended with the rubric and worked examples."""
    return _a.build_system_prompt(claim_object) + _RUBRIC


def build_user_content(context) -> str:
    """Same dynamic context block as Strategy A."""
    return _a.build_user_content(context)
