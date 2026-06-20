"""Deployable single-claim API (Core + full deploy).

A thin FastAPI wrapper that reuses the SAME core as the batch runner — the "bifurcate
compute" pattern: a real-time endpoint for one claim, while bulk processing runs via
code/main.py. Suitable for Render / Railway / Fly (long-lived ASGI). Deploy notes in
api/README.md.

POST /verify-claim  -> { user_id?, user_claim, claim_object, and EITHER
                         image_paths (server-side, relative to dataset root)
                         OR images: [{ id?, mime_type?, data_b64 }] (inline) }
                       returns the 10 generated fields (schema-valid).
GET  /health        -> liveness + which provider/model/strategy is live.

Run locally:
    uvicorn api.app:app --reload --port 8000   (from code/, with PYTHONPATH=src)
"""

from __future__ import annotations

import base64
import os
import sys
from functools import lru_cache
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from claimreview.adjudicator.adjudicator import adjudicate_with_images  # noqa: E402
from claimreview.authenticity.factory import get_authenticity_detector  # noqa: E402
from claimreview.config import Settings  # noqa: E402
from claimreview.io.csv_io import read_evidence_requirements, read_user_history  # noqa: E402
from claimreview.io.images import LoadedImage, load_images  # noqa: E402
from claimreview.pipeline.retry import is_transient, with_backoff  # noqa: E402
from claimreview.providers.registry import get_provider  # noqa: E402
from claimreview.schema.output_schema import GENERATED_COLUMNS  # noqa: E402

DATASET_ROOT = str(REPO_ROOT / "dataset")
DEFAULT_STRATEGY = os.environ.get("CLAIMREVIEW_STRATEGY", "d_image_grounded")
# Comma-separated allowlist for browser clients; "*" by default (no credentials are used).
CORS_ORIGINS = os.environ.get("CLAIMREVIEW_CORS_ORIGINS", "*").split(",")


class InlineImage(BaseModel):
    id: str | None = None
    mime_type: str = "image/jpeg"
    data_b64: str


class ClaimRequest(BaseModel):
    user_id: str = ""
    user_claim: str = Field(..., description="the claim conversation transcript")
    claim_object: str = Field(..., description="car | laptop | package")
    image_paths: str | None = Field(None, description="semicolon-separated server-side paths")
    images: list[InlineImage] | None = Field(None, description="inline base64 images")


@lru_cache(maxsize=1)
def _runtime():
    """Build provider + detector + reference data once and cache for the process."""
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    settings = Settings.load()
    provider = get_provider(settings)
    detector = get_authenticity_detector()
    user_history = read_user_history(str(REPO_ROOT / "dataset" / "user_history.csv"))
    requirements = read_evidence_requirements(
        str(REPO_ROOT / "dataset" / "evidence_requirements.csv")
    )
    from claimreview.prompts import STRATEGIES

    strategy = STRATEGIES[DEFAULT_STRATEGY]
    return settings, provider, detector, user_history, requirements, strategy


def _load_inline(images: list[InlineImage]) -> list[LoadedImage]:
    loaded: list[LoadedImage] = []
    for i, img in enumerate(images):
        try:
            base64.b64decode(img.data_b64, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"image {i}: invalid base64") from exc
        image_id = img.id or f"img_{i + 1}"
        loaded.append(LoadedImage(image_id, f"{image_id}", img.mime_type, img.data_b64))
    return loaded


def create_app() -> FastAPI:
    app = FastAPI(title="Claim Review API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        settings, provider, detector, *_ = _runtime()
        return {
            "status": "ok",
            "provider": provider.name,
            "model": getattr(provider, "model", None),
            "strategy": DEFAULT_STRATEGY,
            "authenticity": detector.name if detector else "off",
        }

    @app.post("/verify-claim")
    async def verify_claim(req: ClaimRequest):
        if req.claim_object not in {"car", "laptop", "package"}:
            raise HTTPException(status_code=400, detail="claim_object must be car|laptop|package")
        _, provider, detector, user_history, requirements, strategy = _runtime()

        if req.images:
            images = _load_inline(req.images)
            image_paths = ";".join(i.rel_path for i in images)
        elif req.image_paths:
            images = load_images(req.image_paths, DATASET_ROOT)
            image_paths = req.image_paths
        else:
            raise HTTPException(status_code=400, detail="provide image_paths or images")

        claim = {
            "user_id": req.user_id,
            "image_paths": image_paths,
            "user_claim": req.user_claim,
            "claim_object": req.claim_object,
        }
        try:
            # Same resilience as the batch runner: retry transient provider errors (429/503).
            row = with_backoff(
                lambda: adjudicate_with_images(
                    claim, user_history, requirements, provider,
                    strategy.build_system_prompt(req.claim_object), images, detector=detector,
                )
            )
        except Exception as exc:  # noqa: BLE001
            status = 503 if is_transient(exc) else 502
            raise HTTPException(status_code=status, detail=f"adjudication failed: {exc}") from exc
        return {k: row[k] for k in GENERATED_COLUMNS}

    return app


app = create_app()
