# STATUS — live board (read first, update last)

Challenge: HackerRank Orchestrate (June 2026) — Multi-Modal Damage Claim Verification.
Participant: Tumo Olorato Mogame (SOLO). Ends **2026-06-20 11:00 IST (07:30 SAST)**.

## Phase tracker
- [x] Recon: official repo cloned, problem statement + AGENTS.md + dataset reviewed.
- [x] Decisions locked: Python · provider-agnostic (anthropic/gemini/openai) · core + full deploy · web + mobile.
- [x] **Backend structure scaffolded** (code/ modules stubbed, tests/CI/gate in place).
- [x] **Front-end structure scaffolded** (apps/web Next.js + apps/mobile Expo + packages/shared).
- [x] Step 0: transcript logging + onboarding ("I agree") — DONE (log.txt, agreement recorded).
- [x] Step 1: schema validation + CSV/image I/O + context assembly + config.load — DONE
      (30 unit tests pass, ruff clean; verified on real data: 44 claims / 47 users / 82 images).
- [x] Step 2: provider interface + registry + FakeProvider + Anthropic adapter — DONE
      (structured-output JSON schema builder; Anthropic uses output_config.format + prompt
      caching, model claude-opus-4-8, lazy SDK import; 39 tests pass, all offline).
- [ ] Step 3: adjudicator + prompt strategy A (+ grounding tests).
- [ ] Step 4: pipeline (throttle/retry/cache) + main.py → run on sample.
- [ ] Step 5: evaluation metrics + strategy B + comparison + report.
- [ ] Step 6: run on claims.csv → output.csv (44 rows, validated).
- [ ] Step 7: FastAPI endpoint + deploy (Render/Railway/Fly).
- [ ] Step 8: web (Next.js) + mobile (Expo) clients over the API; deploy web (Vercel).
- [ ] Submission: code.zip = code/ only (exclude venv/node_modules/dataset) + output.csv + log.txt.
      Public repo + deployed demo showcase web/mobile.

## Current focus
Step 1 done (deterministic foundation green). Supabase = optional demo layer (creds pending
from Tumo) — must not block graded core. README polish to keep current.

## Next action
Step 3 — adjudicator (context -> provider -> validated row) + prompt strategy A
(persona + Rules R1-R4 + allowed vocab) + enable the grounding tests.

## Git
- origin = github.com/TUMO-MOGAME/hackerrank-orchestrate-june26 (fork); upstream = original.
- NOT pushed yet (keeping solution private during the build). Local HEAD == fork main.
- pre-push gate enabled (core.hooksPath=.githooks).

## Log
- 2026-06-19 — Cloned official repo, corrected scope (no Vercel/Supabase required; solo;
  44 test + 20 sample claims). Locked stack (Python, provider-agnostic, core+deploy+web/mobile).
  Scaffolded code/ + apps/web + apps/mobile + packages/shared with stubs, tests, CI, pre-push gate, docs.
  Set up mandatory transcript log + onboarding. Connected fork remote (no push). ruff+pytest green.
