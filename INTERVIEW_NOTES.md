# ClaimLens — Voice-Interview Prep

Prep notes for the AI voice-judge interview. NOT part of `code.zip`. Speak from these; don't read them out.

---

## 1. The 30-second pitch
> "ClaimLens verifies damage claims for cars, laptops, and packages. It reads the claim
> conversation, the submitted photos, the user's history, and the minimum-evidence rules, then
> decides whether the images **support**, **contradict**, or **don't sufficiently prove** the
> claim — with a short, image-grounded justification and risk flags. The core principle:
> **images are the primary source of truth**; the conversation only says what to check; history is
> risk context that never overrides what the photos show."

## 2. How it works (architecture, ~45s)
- **One model call per claim**, structured JSON out → 10 generated fields + 4 passed-through = the exact 14-column `output.csv`.
- **Pipeline:** load images → assemble context (transcript + user history + evidence requirements) → vision model adjudicates → **repair/ground** the fields → **authenticity** merge → write CSV.
- **Provider-agnostic** (Gemini / Claude / OpenAI behind one interface); runs on `gemini-3-flash-preview`.
- **Grounding guard (anti-hallucination):** `supporting_image_ids` is filtered to IDs that actually exist in the claim; a `supported`/`contradicted` verdict can never cite `none`.
- **Authenticity:** C2PA / SynthID **provenance** — deterministic, zero API cost, zero false positives on real photos. Fabricated images → flagged + routed appropriately.
- **Resilience:** SHA-256 response cache (free idempotent reruns), 4.5s throttle, exponential backoff on 429/503, and per-claim failure isolation (one bad claim degrades to a safe manual-review row, never aborts the batch).

## 3. The iteration story — *lead with this, it's the strongest part*
A disciplined, measured search, not one lucky prompt:
1. **Strategy sweep** — 3 prompt strategies on cheap `gemini-2.5-flash-lite` → picked zero-shot "rules of engagement" (A).
2. **Found the wall:** `contradicted` F1 = 0 — the model *never* contradicted. **Model sweep** (strategy fixed) proved it was a **model** ceiling: `gemini-3-flash-preview` was the only model that detected contradictions. (`gemini-2.5-pro` broke — empty output with thinking disabled.)
3. **Error analysis** of the remaining misses → dominant failure was **multi-image over-contradiction**: the model fused the whole image set and called a claim false because one photo looked different.
4. **Prompt refinement (D, image-grounded):** inventory each image separately → anchor the verdict to the image that shows the *claimed part* → image-set inconsistency isn't itself a contradiction. **Macro-F1 0.585 → 0.833.**
5. **Tried a verification pass** to push further → measured it → it *lowered* the score → **didn't ship it.** (Knowing what *not* to add is a result too.)

## 4. Numbers to know cold
- **Macro-F1 0.833, accuracy 0.80** on the 20-row labeled sample (final config: `d_image_grounded` + `gemini-3-flash-preview`).
- Per class: supported F1 0.83 · contradicted F1 0.67 (recall 0.80) · NEI F1 1.00.
- Test set: **44 claims, 1 call each, ≈$0.062 total (~$0.0014/claim), ~395s**, 82 images, 0 failures.
- Primary metric is **Macro-F1**, not accuracy — because classes are imbalanced (supported ≫ contradicted > NEI), so accuracy alone would hide the minority classes.

## 5. Honest limitations (say these *before* they ask — it builds trust)
- **Small eval set:** 20 labeled rows → each row is 5% of accuracy; metrics are noisy.
- **Overfit risk:** strategy D was tuned from error analysis on that same sample, so 0.833 likely flatters it a little.
- **Watch-item:** the test set comes out **70% contradicted** vs the sample's 25% base rate → probably some residual over-contradiction we can't measure without test labels. The 3 hardest remaining errors are all multi-image inconsistency cases.
- **Bias direction:** errors lean toward *skepticism* — the safer direction for fraud triage.

## 6. Likely questions → crisp answers
- **"How do you stop hallucinated evidence?"** → IDs are grounded to the real image set; verdict/citation consistency is enforced in a repair layer after the model.
- **"How does history not override the images?"** → It can only raise a `user_history_risk` flag and color wording; rule R3 forbids it from changing `claim_status`. A clean photo from a risky user is still supported.
- **"Cost & latency at scale?"** → linear, 1 call/claim, ~$0.0014/claim; cache + throttle + backoff handle rate limits; batch-friendly.
- **"Why Gemini / can you switch?"** → provider-agnostic by design; Gemini chosen *empirically* (only model that detected contradictions on this task), not by default.
- **"How did you evaluate?"** → labeled sample, Macro-F1 + per-class precision/recall + confusion matrices, plus reproducible experiment scripts for the strategy/model/prompt sweeps and the error analysis.
- **"Biggest weakness / what's next?"** → multi-image over-contradiction; next lever is validating on more labels and possibly per-image evidence binding, not a second re-vote (we tested that — it didn't help).

## 7. One-liner to close on
> "It's not just a model call — it's a measured pipeline. Every decision (model, prompt,
> even what we *rejected*) is backed by an A/B on labeled data and is reproducible."
