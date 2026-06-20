# Approach & Solution Walkthrough

How this damage-claim verification system was designed, what was built, why, and how it was
validated. For *how to run it*, see [README.md](README.md); for the full metrics + operational
analysis, see [evaluation/evaluation_report.md](evaluation/evaluation_report.md).

---

## 1. The problem (restated)
Given, per claim: a chat transcript, one or more images, the user's claim history, and a minimum
evidence checklist — decide whether the **images** *support*, *contradict*, or *don't sufficiently
prove* the claim, and emit 14 structured columns (issue type, object part, severity, risk flags,
supporting image IDs, grounded justifications, …). **Images are the primary source of truth**; the
conversation only defines *what to check*; history is risk context that must not override the photos.

## 2. Architecture
A provider-agnostic vision pipeline. **One model call per claim** returns the 10 generated fields as
structured JSON; the 4 input columns pass through → the exact 14-column `output.csv`.

```
read CSVs ─▶ assemble context ─▶ vision model (per-object prompt) ─▶ repair/ground fields
            (transcript+history+reqs)                                 ─▶ authenticity merge ─▶ CSV row
```

The same core (`adjudicator.adjudicate_with_images`) backs **two entry points** ("bifurcate
compute"): the batch runner (`main.py` → `output.csv`) and a deployable single-claim API
(`api/app.py`). Module map:

| Layer | Responsibility |
|---|---|
| `schema/` | the 14-column contract, allowed values, and the **repair** safety net |
| `io/` | CSV read/write (exact column order) + image load/base64 |
| `context/` | per-claim context assembly (transcript + history + evidence requirements) |
| `providers/` | one `VisionProvider` interface; Gemini / Anthropic / OpenAI / Fake adapters |
| `prompts/` | the prompt strategies (A–D) + the verification prompt |
| `adjudicator/` | one claim → one validated row |
| `authenticity/` | C2PA / SynthID provenance (+ optional VLM ensemble) |
| `pipeline/` | batch runner · SHA-256 cache · retry/backoff · throttle |

## 3. What was implemented — and why
- **Truth hierarchy in the prompt (rules R1–R4):** images primary; conversation = scope; history =
  risk only; decline when insufficient. *Why:* encodes the spec's decision rules directly so the
  model can't be talked out of the evidence by the customer's words or a risky history.
- **Repair / grounding layer:** clamps every field to the allowed vocabulary, **grounds
  `supporting_image_ids` to IDs that truly exist** in the claim, and enforces verdict↔citation
  consistency (a `supported`/`contradicted` decision on usable images can never cite `none`).
  *Why:* guarantees a schema-valid, non-hallucinated row regardless of model wobble.
- **Authenticity = provenance-first (C2PA / SynthID):** deterministic local parsing of the image
  bytes, zero API cost, zero false positives on real photos; an optional VLM ensemble is available.
  *Why:* fabricated/AI-generated evidence is a core fraud signal and shouldn't cost a model call.
- **Operational resilience:** SHA-256 response cache (free, idempotent reruns), throttle + 2/4/8s
  exponential backoff for rate limits, and per-claim failure isolation (one bad claim degrades to a
  safe manual-review row, never aborts the batch). *Why:* free-tier RPM limits + reproducibility.

## 4. How the final configuration was chosen (measured, reproducible)
Not one lucky prompt — a three-stage search, each step backed by an A/B on the labeled sample:

1. **Strategy screen** (cheap `gemini-2.5-flash-lite`): A (zero-shot rules) vs B (few-shot) vs C
   (contradiction-gate) → **A** wins. → `evaluation/main.py --compare`
2. **Model sweep** (strategy fixed): flash-lite *never* predicts `contradicted` (F1 = 0);
   `gemini-3-flash-preview` does; `gemini-2.5-pro` breaks (empty output w/ thinking disabled). So
   `contradicted` was a **model** ceiling, not a prompt bug. → `experiment_contradicted.py`
3. **Error analysis → prompt refinement:** A's dominant failure was *multi-image over-contradiction*
   (fusing the whole image set and calling a claim false because one photo differs). Strategy **D
   (image-grounded)** — inventory each image, anchor the verdict to the image of the *claimed part*
   — lifted Macro-F1 **0.585 → 0.833**. → `experiment_strategy.py`, `error_analysis.py`
4. **Verification pass (rejected):** a second-opinion pass to push further — implemented, measured,
   and it *lowered* Macro-F1, so it was **not shipped**. Knowing what not to add is a result too.
   → `experiment_verify.py`

**Final: `d_image_grounded` + `gemini-3-flash-preview` + provenance authenticity.**

## 5. Results (sample_claims.csv, 20 labeled rows)
Macro-F1 **0.833**, accuracy **0.80** — supported F1 0.83 · contradicted F1 0.67 (recall 0.80) ·
NEI F1 1.00. Test set: 44 claims, 1 call each, ≈$0.062, ~395 s. Full breakdown in the report.

## 6. Honest limitations
- **Small eval set:** 20 labeled rows → each row is 5% of accuracy; metrics are noisy.
- **Overfit risk:** strategy D was shaped by error analysis on that same sample.
- **Watch-item:** the test set comes out 70% `contradicted` vs the sample's 25% base rate — likely
  some residual over-contradiction we can't measure without test labels. The remaining hard cases
  are multi-image inconsistency. Net error direction is *skepticism* — the safer bias for fraud.

## 7. Reproduce
```bash
cd code
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY
python evaluation/main.py --compare        # strategies → evaluation_report.md
python main.py                             # → ../output.csv
python evaluation/error_analysis.py        # the §6 error breakdown
# the experiment_*.py scripts reproduce the model/strategy/verification A/Bs
```
