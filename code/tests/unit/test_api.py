"""Deployable API smoke tests — offline (fake provider, authenticity disabled)."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

CODE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE_ROOT))        # so `import api.app`
sys.path.insert(0, str(CODE_ROOT / "src"))

# Force the offline fake provider + no authenticity BEFORE the app builds its runtime.
os.environ["CLAIMREVIEW_PROVIDER"] = "fake"
os.environ["CLAIMREVIEW_AUTH_ENABLED"] = "false"

from api.app import _runtime, create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from claimreview.schema.output_schema import GENERATED_COLUMNS, validate_row  # noqa: E402


@pytest.fixture
def client():
    _runtime.cache_clear()
    return TestClient(create_app())


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["provider"] == "fake"


def test_verify_claim_inline_image(client):
    img_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake-jpeg").decode("ascii")
    payload = {
        "user_id": "u1",
        "user_claim": "rear bumper has a dent",
        "claim_object": "car",
        "images": [{"id": "img_1", "mime_type": "image/jpeg", "data_b64": img_b64}],
    }
    r = client.post("/verify-claim", json=payload)
    assert r.status_code == 200
    fields = r.json()
    assert set(fields.keys()) == set(GENERATED_COLUMNS)
    assert validate_row(fields, "car") == []


def test_verify_claim_rejects_bad_object(client):
    r = client.post("/verify-claim", json={"user_claim": "x", "claim_object": "boat",
                                           "images": [{"data_b64": "QQ=="}]})
    assert r.status_code == 400


def test_verify_claim_requires_images(client):
    r = client.post("/verify-claim", json={"user_claim": "x", "claim_object": "car"})
    assert r.status_code == 400
