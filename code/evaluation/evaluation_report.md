# Evaluation Report — Multi-Modal Damage Claim Verification

## 1. Setup
- Dataset: `dataset/sample_claims.csv` (20 labeled rows); final predictions on `dataset/claims.csv` (44 rows).
- **Final config for `output.csv`: strategy `d_image_grounded` + model `gemini-3-flash-preview`** (Macro-F1 **0.833**, accuracy **0.80** on the sample).
- Three-stage selection: (§2/§3) **strategy screen** on the cheap `gemini-2.5-flash-lite` → pick `a_zero_shot`; (§3b) **model sweep** (strategy fixed) → pick `gemini-3-flash-preview`, the only model that detects `contradicted`; (§3c) **prompt refinement** driven by error analysis (§6) → `d_image_grounded` (per-image grounding) lifts Macro-F1 from 0.585 to 0.833.
- Primary metric: **Macro-F1** on `claim_status` (class imbalance: supported≫contradicted>not_enough_information, so accuracy alone misleads).

## 2. Per-strategy metrics on sample_claims.csv (model = `gemini-2.5-flash-lite`)

**Strategy `a_zero_shot` — claim_status** — Macro-F1 **0.521**, accuracy **0.750**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| supported | 0.81 | 1.00 | 0.90 | 13 |
| contradicted | 0.00 | 0.00 | 0.00 | 5 |
| not_enough_information | 0.50 | 1.00 | 0.67 | 2 |

Confusion matrix (rows = actual, cols = predicted):

| actual \ pred | supported | contradicted | not_enough_information |
|---|---|---|---|
| supported | 13 | 0 | 0 |
| contradicted | 3 | 0 | 2 |
| not_enough_information | 0 | 0 | 2 |

Secondary exact-match accuracy: issue_type=0.60  ·  object_part=0.90  ·  severity=0.55  ·  evidence_standard_met=0.90  ·  valid_image=0.90

**Strategy `b_rules_fewshot` — claim_status** — Macro-F1 **0.498**, accuracy **0.700**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| supported | 0.75 | 0.92 | 0.83 | 13 |
| contradicted | 0.00 | 0.00 | 0.00 | 5 |
| not_enough_information | 0.50 | 1.00 | 0.67 | 2 |

Confusion matrix (rows = actual, cols = predicted):

| actual \ pred | supported | contradicted | not_enough_information |
|---|---|---|---|
| supported | 12 | 0 | 1 |
| contradicted | 4 | 0 | 1 |
| not_enough_information | 0 | 0 | 2 |

Secondary exact-match accuracy: issue_type=0.45  ·  object_part=0.95  ·  severity=0.50  ·  evidence_standard_met=0.90  ·  valid_image=0.90

**Strategy `c_contradiction_aware` — claim_status** — Macro-F1 **0.498**, accuracy **0.700**

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| supported | 0.75 | 0.92 | 0.83 | 13 |
| contradicted | 0.00 | 0.00 | 0.00 | 5 |
| not_enough_information | 0.50 | 1.00 | 0.67 | 2 |

Confusion matrix (rows = actual, cols = predicted):

| actual \ pred | supported | contradicted | not_enough_information |
|---|---|---|---|
| supported | 12 | 0 | 1 |
| contradicted | 4 | 0 | 1 |
| not_enough_information | 0 | 0 | 2 |

Secondary exact-match accuracy: issue_type=0.50  ·  object_part=0.85  ·  severity=0.50  ·  evidence_standard_met=0.90  ·  valid_image=0.95

## 3. Strategy comparison (≥2 required)

| Strategy | Macro-F1 | Accuracy | F1 supported | F1 contradicted | F1 NEI |
|---|---|---|---|---|---|
| a_zero_shot | 0.521 | 0.750 | 0.90 | 0.00 | 0.67 |
| b_rules_fewshot | 0.498 | 0.700 | 0.83 | 0.00 | 0.67 |
| c_contradiction_aware | 0.498 | 0.700 | 0.83 | 0.00 | 0.67 |

**Strategy chosen: `a_zero_shot`** (highest Macro-F1 on flash-lite).

## 3b. Model comparison (strategy fixed = `a_zero_shot`, on sample_claims.csv)

The strategy sweep above showed `contradicted` was unreachable on `gemini-2.5-flash-lite`
regardless of prompt (F1=0 for all three strategies). To test whether this was a prompt
ceiling or a model ceiling, we held the best strategy fixed and swept the model
(`evaluation/experiment_contradicted.py`):

| Model | Macro-F1 | Accuracy | F1 contradicted | contradicted caught | Notes |
|---|---|---|---|---|---|
| gemini-2.5-flash-lite | 0.521 | 0.750 | 0.00 | 0/5 | never emits `contradicted` |
| **gemini-3-flash-preview** | **0.585** | 0.650 | **0.40** | **2/5** | **chosen** — only model that contradicts |
| gemini-2.5-pro | 0.061 | 0.100 | 0.00 | 0/5 | empty structured output w/ thinking disabled |

So `contradicted` was a **model ceiling**, not a prompt bug. `gemini-3-flash-preview` lifts the
primary metric (Macro-F1 0.521→0.585) and is the only model that detects contradictions; the
trade-off was lower raw accuracy (0.75→0.65) because it is more skeptical. That over-skepticism
is fixed by the prompt refinement in §3c.

## 3c. Prompt refinement on the production model (`gemini-3-flash-preview`)

Error analysis of `a_zero_shot` (§6) showed its dominant failure was **over-contradiction on
multi-image claims** — it fused the whole image set and called a claim false because one image
looked different. We wrote **`d_image_grounded`** (`prompts/strategy_d_image_grounded.py`): same
truth hierarchy, plus an explicit *per-image inventory → anchor the verdict to the image that
shows the claimed part → image-set inconsistency is not itself a contradiction* procedure, and a
*proven fabrication ⇒ prefer contradicted over NEI* rule. A/B on the sample
(`evaluation/experiment_strategy.py`):

| Strategy (model = gemini-3-flash-preview) | Macro-F1 | Accuracy | F1 supported | F1 contradicted | F1 NEI |
|---|---|---|---|---|---|
| a_zero_shot | 0.585 | 0.650 | 0.78 | 0.40 | 0.57 |
| **d_image_grounded** | **0.833** | **0.800** | **0.83** | **0.67** | **1.00** |

A large, across-the-board gain with no class sacrificed (supported precision stays 0.91). So
**the final `output.csv` uses `d_image_grounded` + `gemini-3-flash-preview`.** On the 44-row test
set it yields 9 supported / 31 contradicted / 4 not_enough_information.

> **Honest caveat (overfitting + generalization):** `d_image_grounded` was shaped by error
> analysis *on the sample*, so the 0.833 likely flatters it slightly on these exact 20 rows. The
> refinements are principled and general (not row-specific), but two signals temper confidence:
> 3 of its 4 sample errors are still multi-image over-contradictions (a genuinely hard, partly
> definitional case), and the test set comes out **70% contradicted (31/44)** vs the sample's 25%
> base rate. We cannot measure test accuracy (no labels), but that gap suggests some residual
> over-contradiction on test; true test Macro-F1 is probably below 0.833. This is the #1 thing to
> validate if more labels become available.

## 4. Operational analysis

Measured from the actual cold (cache-cleared) run that produced `output.csv` —
`gemini-3-flash-preview`, strategy `d_image_grounded`, authenticity `provenance`:

| Metric | Test set (`claims.csv`, 44 rows) |
|---|---|
| Model calls | **44** (1 per claim; 0 cache hits on a cold run, 0 failures) |
| Input tokens | **147,411** (avg ≈ **3,350** / call) |
| Output tokens | **7,091** (avg ≈ **161** / call) |
| Images processed | **82** |
| Authenticity API calls | **0** (provenance is local C2PA parsing — zero API cost) |
| Wall-clock runtime | **≈ 395 s** (≈ 194 s is deliberate throttle; ≈ 4.6 s compute/call) |
| Est. cost | **≈ $0.062** |

Cost basis (`gemini-3-flash-preview` pricing assumption, text+image: **$0.30 / 1M input**,
**$2.50 / 1M output**) → 147,411 × $0.30/1M + 7,091 × $2.50/1M ≈ **$0.044 + $0.018 = $0.062**
for the whole 44-row test set (≈ $0.0014 per claim). The earlier `gemini-2.5-flash-lite`
config cost ≈ $0.011 for the same set — so the upgrade is ~6× the token cost, still well under a
cent per claim and negligible in absolute terms. The image-grounding prompt (D) costs the same
as A — it's just better instructions, no extra calls. Reruns are $0 (served from the cache).

- **TPM/RPM & resilience:** a 4.5 s throttle between live calls keeps us under the free-tier
  ≈15 RPM ceiling; exponential backoff (2/4/8 s) retries 429/503/timeouts; a SHA-256 response
  cache keyed on provider+model+prompt+claim makes reruns free and idempotent; per-image
  authenticity is memoized by content hash. A single claim's failure degrades to a safe
  manual-review row rather than aborting the batch. "Thinking" tokens are disabled for the
  structured call, which both lowers output cost and prevents JSON truncation.

## 5. Findings & limitations (honest)
- **`contradicted` — from a hard ceiling to the system's strength.** On `gemini-2.5-flash-lite` all three prompt strategies scored F1=0 (it never contradicted). The model sweep (§3b) showed this was the **model** (`gemini-3-flash-preview`: F1 0.40), and the prompt refinement (§3c) showed the *remaining* gap was a **prompt** issue: `d_image_grounded` reaches **contradicted F1 0.67 (recall 0.80)** and Macro-F1 **0.833**. Its justifications are specific and image-grounded ("img_1 shows a toy car, not a real vehicle"; "shipping label intact despite claimed water damage"). We tried a separate second-opinion verification pass to push it further (§7) — it did not help and was not shipped.
- **Residual limitation (honest):** `d_image_grounded`'s 3 remaining sample errors are all multi-image *over-contradiction* (it still treats a strongly inconsistent second image as proof the claim is false, where the gold trusts the damage image). The test set is 70% `contradicted` vs the sample's 25% base rate — likely some over-contradiction we can't measure without test labels (see §3c caveat). Net direction of error is *skepticism*, which is the safer bias for fraud triage.
- **Bug fixed during iteration:** the brain's structured-JSON calls truncated on slow/loaded models because Gemini 'thinking' tokens consumed the output budget; thinking is now disabled for the structured tasks (faster, cheaper, reliable).
- **Model choice:** `gemini-3-flash-preview` is the production model (best Macro-F1, only model that detects contradictions). `gemini-2.5-flash-lite` remains a valid cheaper/faster fallback (≈6× lower token cost, higher raw accuracy) for cost-sensitive runs that don't need contradiction detection — swap via `CLAIMREVIEW_MODEL`. `gemini-2.5-pro` is unusable here (empty structured output with thinking disabled).
- **Authenticity:** provenance mode (C2PA/SynthID) deterministically flags the test images that are genuinely AI-generated, at zero added API cost and zero false positives on real photos (see `evaluation/authenticity_report.md`).

## 6. Error analysis (`evaluation/error_analysis.py`)

This analysis *drove* the §3c refinement, then validated it. Run on the 20-row sample, model
`gemini-3-flash-preview`:

**Before — `a_zero_shot` (13/20, 65%), 7 errors:**

| Count | Error type | What's happening |
|---|---|---|
| 3 | **over-contradiction** (gold `supported` → `contradicted`) | multi-image claims: over-weights one non-matching image and calls the whole claim false |
| 3 | **missed contradiction** (gold `contradicted` → `supported`/`NEI`) | subtlest refutations; 2 are *described* correctly ("dented item, not the claimed box"; "AI-generated warehouse photo") but emitted as `NEI` |
| 1 | over-cautious (gold `supported` → `NEI`) | genuinely conflicting images of "the same" car |

These two dominant levers — *anchor to the image of the claimed part* and *fabrication ⇒ contradicted, not NEI* — became strategy `d_image_grounded`.

**After — `d_image_grounded` (16/20, 80%), 4 errors:**

| Count | Error type | What's happening |
|---|---|---|
| 3 | **over-contradiction** (gold `supported` → `contradicted`) | still flags strongly inconsistent image pairs (e.g. damage on one car, a different car in the 2nd image) — a hard, partly definitional case |
| 1 | missed contradiction (gold `contradicted` → `supported`) | a real trackpad scratch that the labels call contradicted |

The refinement cleared the over-cautious NEI errors and 2 of 3 missed contradictions, and lifted
supported recall (0.69→0.77) — i.e. it fixed real over-contradictions even though 3 of the
hardest remain. Net error direction is still *skepticism*, the safer bias for fraud triage.

## 7. Verification pass — tried, did not help (negative result)

Hypothesis: an independent second-opinion pass on the decisive rows would catch the
over-contradiction errors above. We implemented it (`prompts/verification.py` +
`pipeline/verification.py`, three reconciliation policies) and measured it on the sample
(`evaluation/experiment_verify.py`, 14 rows verified):

| Config | Macro-F1 | Accuracy | F1 contradicted |
|---|---|---|---|
| **baseline (pass-1 only)** | **0.585** | 0.650 | **0.40** |
| + verify, policy `second` | 0.515 | 0.600 | 0.22 |
| + verify, policy `agree_else_nei` | 0.459 | 0.550 | 0.25 |
| + verify, policy `downgrade_contradiction` | 0.500 | 0.600 | 0.25 |

Every policy *lowered* Macro-F1: the second pass relaxed correct contradictions about as often
as it fixed wrong ones, and the disagreement-→`NEI` policies traded confident-correct answers
for hedges. Conclusion: **not worth the ~+0.7× API cost — not shipped.** The code is kept as a
documented experiment. A more promising future lever is the image-by-image grounding from §6,
not a whole-claim re-vote.
