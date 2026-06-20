"""Pipeline: retry/backoff, cache, and batch runner (offline with fakes)."""

from __future__ import annotations

import pytest

from claimreview.authenticity.detector import FakeAuthenticityDetector
from claimreview.pipeline.cache import ResponseCache
from claimreview.pipeline.retry import is_transient, with_backoff
from claimreview.pipeline.runner import run_batch
from claimreview.prompts.strategy_a_zero_shot import build_system_prompt
from claimreview.providers.base import AdjudicationResult, VisionProvider
from claimreview.providers.fake_provider import FakeProvider
from claimreview.schema.output_schema import OUTPUT_COLUMNS, validate_row

# --- retry ---------------------------------------------------------------------------

def test_backoff_retries_then_succeeds():
    calls = {"n": 0}
    slept = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 service unavailable")
        return "ok"

    out = with_backoff(flaky, max_retries=3, sleeper=slept.append)
    assert out == "ok"
    assert calls["n"] == 3
    assert slept == [2.0, 4.0]   # 2s then 4s before the 3rd (successful) attempt


def test_backoff_gives_up_after_max_retries():
    def always_503():
        raise RuntimeError("503 unavailable")

    with pytest.raises(RuntimeError):
        with_backoff(always_503, max_retries=2, sleeper=lambda _s: None)


def test_non_transient_not_retried():
    calls = {"n": 0}

    def bad_request():
        calls["n"] += 1
        raise ValueError("400 invalid argument")

    with pytest.raises(ValueError):
        with_backoff(bad_request, max_retries=3, sleeper=lambda _s: None)
    assert calls["n"] == 1   # raised immediately, no retries


def test_is_transient_detects_codes_and_messages():
    assert is_transient(RuntimeError("429 too many requests"))
    assert is_transient(TimeoutError("deadline exceeded"))
    assert not is_transient(ValueError("bad schema"))


# --- cache ---------------------------------------------------------------------------

def test_cache_roundtrip_and_key_stability(tmp_path):
    cache = ResponseCache(str(tmp_path / "c.sqlite"), enabled=True)
    k1 = ResponseCache.make_key("sys", "img", "claim", "car")
    k2 = ResponseCache.make_key("sys", "img", "claim", "car")
    assert k1 == k2
    assert k1 != ResponseCache.make_key("sys", "img", "claim", "laptop")
    assert cache.get(k1) is None
    cache.set(k1, {"claim_status": "supported"})
    assert cache.get(k1)["claim_status"] == "supported"
    cache.close()


def test_disabled_cache_is_noop(tmp_path):
    cache = ResponseCache(str(tmp_path / "c.sqlite"), enabled=False)
    k = ResponseCache.make_key("a")
    cache.set(k, {"x": 1})
    assert cache.get(k) is None


# --- runner ----------------------------------------------------------------------------

def _sample_claims(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "img_1.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")
    return [
        {"user_id": "u1", "image_paths": "images/img_1.jpg",
         "user_claim": "rear bumper dent", "claim_object": "car"},
        {"user_id": "u2", "image_paths": "images/missing.jpg",   # no usable image -> degraded
         "user_claim": "cracked screen", "claim_object": "laptop"},
    ]


def test_run_batch_produces_valid_rows_in_order(tmp_path):
    claims = _sample_claims(tmp_path)
    result = run_batch(
        claims, {}, [], FakeProvider(), build_system_prompt, str(tmp_path),
    )
    assert [r["user_id"] for r in result.rows] == ["u1", "u2"]
    for r in result.rows:
        assert list(r.keys()) == OUTPUT_COLUMNS
        assert validate_row(r, r["claim_object"]) == []
    # claim 2 has no usable image -> degraded, no model call for it
    assert result.rows[1]["valid_image"] == "false"
    assert result.stats.claims == 2
    assert result.stats.model_calls == 1   # only the claim with a real image hit the provider


def test_run_batch_uses_cache_on_second_pass(tmp_path):
    claims = _sample_claims(tmp_path)[:1]
    cache = ResponseCache(str(tmp_path / "c.sqlite"), enabled=True)
    r1 = run_batch(claims, {}, [], FakeProvider(), build_system_prompt, str(tmp_path), cache=cache)
    r2 = run_batch(claims, {}, [], FakeProvider(), build_system_prompt, str(tmp_path), cache=cache)
    cache.close()
    assert r1.stats.model_calls == 1 and r1.stats.cache_hits == 0
    assert r2.stats.model_calls == 0 and r2.stats.cache_hits == 1
    assert r1.rows[0] == r2.rows[0]


def test_run_batch_survives_provider_failure(tmp_path):
    claims = _sample_claims(tmp_path)[:1]

    class BoomProvider(VisionProvider):
        name = "boom"

        def adjudicate(self, system_prompt, context, images) -> AdjudicationResult:
            raise RuntimeError("503 unavailable")

    result = run_batch(
        claims, {}, [], BoomProvider(), build_system_prompt, str(tmp_path),
        max_retries=1,
    )
    assert result.stats.failures == 1
    row = result.rows[0]
    assert row["valid_image"] == "false"
    assert "manual_review_required" in row["risk_flags"]
    assert validate_row(row, "car") == []


def test_run_batch_applies_authenticity(tmp_path):
    claims = _sample_claims(tmp_path)[:1]
    detector = FakeAuthenticityDetector(ai_generated=True, confidence=0.99, signals=["c2pa"])
    result = run_batch(
        claims, {}, [], FakeProvider(), build_system_prompt, str(tmp_path), detector=detector,
    )
    row = result.rows[0]
    assert "non_original_image" in row["risk_flags"]
    assert row["valid_image"] == "false"
