# Multi-Modal Damage Claim Verification — `code/`

Verifies damage claims (car / laptop / package) from images + a claim conversation +
user history + minimum evidence requirements, and emits a structured decision per claim.
Built for HackerRank Orchestrate (June 2026). See `../problem_statement.md` for the spec.

> Status: **complete and runnable.** `python main.py` reproduces `../output.csv` (44 rows,
> exact 14-column schema); `python evaluation/main.py --compare` reproduces the metrics in
> `evaluation/evaluation_report.md`. Full test suite (74 tests) green: `pytest`.
>
> 📖 **[APPROACH.md](APPROACH.md)** — the full design, what was built & why, and the measured
> strategy/model selection journey.

## Results (sample_claims.csv, 20 labeled rows)
Final config **`d_image_grounded` + `gemini-3-flash-preview`** — claim_status **Macro-F1 0.833 /
accuracy 0.80** (supported F1 0.83, contradicted F1 0.67 / recall 0.80, NEI F1 1.00). Reached via
a 3-stage search: strategy screen on cheap flash-lite → model sweep (only gemini-3 detects
`contradicted`) → error-analysis-driven prompt refinement (`d_image_grounded`: per-image grounding)
which lifted Macro-F1 0.585→0.833. See report §3/§3b/§3c and the `experiment_*.py` harnesses.
Test-set run: 44 calls, ≈155k tokens, ≈$0.062, ~395 s. Honest caveat: the refinement was tuned on
the sample, and the test set is 70% `contradicted` — likely some residual over-contradiction
(report §3c). Full operational analysis + error analysis in `evaluation/evaluation_report.md`.

## Design
Images are the primary source of truth; the conversation defines scope; user history is
risk context only and never overrides clear visual evidence. The core logic is shared by
two entry points (the "bifurcate compute" pattern):

- **Batch** (`main.py`) → reads `dataset/claims.csv`, writes `output.csv` (14 cols, exact order).
- **API** (`api/app.py`) → deployable single-claim endpoint reusing the same core.

```
src/claimreview/
  config.py            env-only settings + provider selection
  io/                  csv read/write (14-col order) · image load + base64
  context/             per-claim context assembly (history + evidence reqs + transcript)
  schema/              output contract: 14 columns + allowed values + validation
  providers/           VisionProvider interface + anthropic/gemini/openai adapters
  adjudicator/         one claim -> one validated row
  prompts/             4 strategies (A zero-shot … D image-grounded) + verification pass
  pipeline/            batch runner · throttle · retry/backoff · SHA-256 cache
evaluation/            metrics + strategy/model compare + report + experiment_*.py harnesses
api/                   FastAPI single-claim endpoint (deploy notes in api/README.md)
tests/                 unit (mocked provider) · schema · grounding
```

## Run
```bash
cd code
pip install -r requirements.txt      # or requirements-dev.txt to also run the tests
cp .env.example .env                  # set CLAIMREVIEW_PROVIDER + the matching API key

# Evaluate on labeled sample data and compare strategies -> evaluation_report.md
python evaluation/main.py --compare

# Produce final predictions for the test set -> ../output.csv
python main.py --input ../dataset/claims.csv --output ../output.csv

# Offline smoke run (no API, no cost) and the test suite
python main.py --provider fake --limit 5
pytest -q
```

## Providers
Set `CLAIMREVIEW_PROVIDER` to `anthropic`, `gemini`, or `openai`; keys via env
(`ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY`). Never hardcode secrets.

## How a claim becomes a row
1. Read `claims.csv`, join `user_history.csv` (risk context) and `evidence_requirements.csv`
   (minimum-evidence checklist) for the claim's object/issue family.
2. Load + base64 the submitted images; screen each for AI-generation/tampering (C2PA
   provenance, deterministic and local).
3. One vision-model call per claim with the object-scoped system prompt; structured JSON
   for the 10 generated fields.
4. `repair_generated_fields` clamps every field to the allowed vocabulary and **grounds**
   `supporting_image_ids` to IDs that truly exist in the claim (anti-hallucination); a
   supported/contradicted verdict can never cite `none`.
5. Authenticity verdict is merged conservatively; the 4 input columns pass through; the row
   is written in exact 14-column order.

Resilience: SHA-256 response cache (free idempotent reruns), throttle + exponential backoff
for rate limits, and per-claim failure isolation (degrades to a safe manual-review row).
