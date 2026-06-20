# Deployable single-claim API

Thin FastAPI wrapper over the same core used by the batch runner. The contract
deliverable does **not** require deployment — this is a differentiator (Core + full deploy).

## Endpoints
- `GET /health` → `{status, provider, model, strategy, authenticity}` (liveness + live config).
- `POST /verify-claim` → returns the 10 generated fields (schema-valid, repaired/grounded).
  Body: `user_id?`, `user_claim`, `claim_object` (`car|laptop|package`), and EITHER
  `image_paths` (semicolon-separated, server-side, relative to the dataset root) OR
  `images: [{ id?, mime_type?, data_b64 }]` (inline base64). Transient provider errors
  (429/503) are retried with backoff; a terminal failure returns 503/502.

## Local
```bash
cd code
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.app:app --reload --port 8000
# GET  http://localhost:8000/health
# POST http://localhost:8000/verify-claim  (see example below)
```

Example request (inline image):
```bash
curl -s localhost:8000/verify-claim -H 'content-type: application/json' -d '{
  "user_id": "user_001",
  "user_claim": "Customer: rear bumper has a dent after parking.",
  "claim_object": "car",
  "images": [{"id": "img_1", "mime_type": "image/jpeg", "data_b64": "<base64>"}]
}'
```

## Deploy targets
- **Render / Railway / Fly.io** (recommended): long-lived ASGI, no function timeout —
  start command `uvicorn api.app:app --host 0.0.0.0 --port $PORT`. Set provider + API key
  as environment variables in the dashboard.
- **Vercel**: possible via an ASGI adapter, but Hobby functions cap at 60s — keep the
  endpoint to a single claim (fine) and run bulk processing locally via `main.py`.

Set env vars: `CLAIMREVIEW_PROVIDER`, `CLAIMREVIEW_MODEL`, the matching `*_API_KEY`,
`CLAIMREVIEW_AUTH_MODE` (default `provenance`), `CLAIMREVIEW_STRATEGY` (default
`a_zero_shot`). Never commit secrets.

> Status: implemented and smoke-tested (offline `TestClient` + live Gemini). Cloud deploy
> is a one-command start; the platform account/secrets are the user's to provision.
