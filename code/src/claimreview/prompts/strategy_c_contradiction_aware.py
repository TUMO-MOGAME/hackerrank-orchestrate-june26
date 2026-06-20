"""Strategy C — contradiction-aware (iteration on A).

Targets the measured weakness: Strategies A and B score F1=0.00 on `contradicted` — the
model never predicts it, defaulting to `supported` (without checking the SPECIFIC claimed
damage is present) or `not_enough_information`. C keeps A's persona + Four Rules and adds a
STATUS DECISION GATE that (1) makes `supported` require the exact claimed damage to be
visible, and (2) gives `contradicted` concrete, first-class triggers — without flooding it
(the part must be clearly visible to contradict).
"""

from __future__ import annotations

from claimreview.prompts import strategy_a_zero_shot as _a

NAME = "c_contradiction_aware"

_GATE = """

=== STATUS DECISION GATE (decide claim_status in THIS order) ===
First identify, from the conversation, the EXACT claim: which part, and what specific damage.
Then walk these gates top to bottom and stop at the first that matches:

1. Is the claimed object/part actually visible and the image usable?
   - NO  -> claim_status = not_enough_information (set evidence_standard_met=false + the
            quality/visibility risk flag). Do not guess. STOP.

2. The claimed part IS visible. Does the image show a DIFFERENT object or a different part
   than claimed (e.g. claim says "windshield" but the photo is a door)?
   - YES -> claim_status = contradicted; add `claim_mismatch` (and `wrong_object` /
            `wrong_object_part`). STOP.

3. The claimed part is visible. Is the SPECIFIC claimed damage actually present on it?
   - The part is visible but looks INTACT / undamaged, or shows clearly different damage
     than claimed -> claim_status = contradicted; add `claim_mismatch`. STOP.
   - The exact claimed damage IS clearly present -> claim_status = supported. STOP.
   - The part is visible but you cannot tell whether the damage is present (too small,
     glare, angle) -> claim_status = not_enough_information.

KEY CORRECTION: `supported` is NOT the default. Choose it ONLY when you can SEE the specific
claimed damage on the claimed part. If the claimed part is clearly visible and you do NOT
see that damage, the correct answer is `contradicted`, NOT `supported` and NOT
`not_enough_information`. `contradicted` is a normal, expected outcome — use it whenever the
visible evidence is inconsistent with the claim.
"""


def build_system_prompt(claim_object: str) -> str:
    """Strategy A's persona + Four Rules, plus the explicit status decision gate."""
    return _a.build_system_prompt(claim_object) + _GATE


def build_user_content(context) -> str:
    """Same dynamic context block as Strategy A."""
    return _a.build_user_content(context)
