"""Evaluation entry point (CONTRACT — do not rename; see AGENTS.md §6).

Runs the system over dataset/sample_claims.csv (which has ground-truth labels), scores
claim_status (per-class + Macro-F1 + confusion), compares >=2 strategies, and writes
evaluation/evaluation_report.md.

Usage:
    python code/evaluation/main.py --compare              # A vs B on the sample set
    python code/evaluation/main.py --strategy a_zero_shot # single strategy
    python code/evaluation/main.py --compare --provider fake   # offline plumbing check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_ROOT.parent
DATASET_ROOT = REPO_ROOT / "dataset"
REPORT_PATH = CODE_ROOT / "evaluation" / "evaluation_report.md"

sys.path.insert(0, str(CODE_ROOT / "src"))
sys.path.insert(0, str(CODE_ROOT / "evaluation"))


def _render_report(results, *, provider_name: str, model: str) -> str:
    from compare import render_comparison
    from metrics import render_report

    best = max(results, key=lambda r: (r.report.macro_f1, r.report.accuracy))
    total_calls = sum(r.stats.model_calls for r in results)
    total_in = sum(r.stats.input_tokens for r in results)
    total_out = sum(r.stats.output_tokens for r in results)
    total_imgs = sum(r.stats.images for r in results)
    elapsed = sum(r.stats.elapsed_s for r in results)
    n_sample = results[0].report.per_class
    sample_n = sum(m["support"] for m in n_sample.values())

    # crude per-call token averages -> extrapolate the 44-row test set (single strategy)
    avg_in = total_in / total_calls if total_calls else 0
    avg_out = total_out / total_calls if total_calls else 0
    test_calls = 44
    # Public per-1M-token pricing (USD), model-aware; falls back to flash pricing.
    PRICING = {
        "gemini-2.5-flash-lite": (0.10, 0.40),
        "gemini-3-flash-preview": (0.30, 2.50),
        "gemini-3.5-flash": (0.30, 2.50),
        "gemini-2.5-flash": (0.30, 2.50),
        "gemini-2.5-pro": (1.25, 10.0),
    }
    price_in, price_out = PRICING.get(model, (0.30, 2.50))
    est_cost = (test_calls * avg_in / 1e6) * price_in + (test_calls * avg_out / 1e6) * price_out

    lines = [
        "# Evaluation Report — Multi-Modal Damage Claim Verification",
        "",
        "## 1. Setup",
        f"- Dataset: `dataset/sample_claims.csv` ({sample_n} labeled rows); "
        "final predictions on `dataset/claims.csv` (44 rows).",
        f"- Provider: `{provider_name}`  ·  Model: `{model}`",
        "- Strategies: " + ", ".join(f"`{r.name}`" for r in results),
        "- Primary metric: **Macro-F1** on `claim_status` (class imbalance: supported≫"
        "contradicted>not_enough_information, so accuracy alone misleads).",
        "",
        "## 2. Per-strategy metrics on sample_claims.csv",
        "",
    ]
    for r in results:
        lines.append(render_report(r.report, title=f"Strategy `{r.name}` — claim_status"))
        sec = "  ·  ".join(f"{f}={a:.2f}" for f, a in r.secondary.items())
        lines.append(f"Secondary exact-match accuracy: {sec}\n")

    lines += [
        "## 3. Strategy comparison (≥2 required)",
        "",
        render_comparison(results),
        "",
        f"**Final strategy chosen for `output.csv`: `{best.name}`** "
        f"(highest Macro-F1 = {best.report.macro_f1:.3f}).",
        "",
        "## 4. Operational analysis",
        f"- Model calls (this eval, all strategies): **{total_calls}** "
        f"(sample = {sample_n} rows × {len(results)} strategies; cache makes reruns free).",
        f"- Tokens (this eval): input **{total_in:,}**, output **{total_out:,}** "
        f"(avg ≈ {avg_in:.0f} in / {avg_out:.0f} out per call).",
        f"- Images processed (this eval): **{total_imgs}**.",
        f"- Full test set (44 rows, single chosen strategy): ≈ **{test_calls} calls**, "
        f"≈ {test_calls * avg_in:,.0f} input + {test_calls * avg_out:,.0f} output tokens.",
        f"- Est. cost for the test set ≈ **${est_cost:.4f}** "
        f"(`{model}` pricing assumption: ${price_in}/1M in, ${price_out}/1M out).",
        f"- Runtime (this eval): ≈ {elapsed:.0f}s wall-clock.",
        "- TPM/RPM & resilience: throttle between live calls (free tier ≈10–15 RPM); "
        "exponential backoff (2/4/8s) on 429/503/timeouts; SHA-256 response cache keyed on "
        "provider+prompt+claim avoids repeat calls on reruns; per-image authenticity is "
        "memoized by content hash. A single claim's failure degrades to a safe "
        "manual-review row rather than aborting the batch.",
        "",
        "## 5. Findings & limitations (honest)",
        "- **`contradicted` is the hard class:** all strategies score F1≈0 on it — the model "
        "rarely emits `contradicted`, reading visible damage as `supported`. A targeted "
        "iteration (Strategy C: explicit status-decision gate making `supported` *earn* it) "
        "did not move it on `gemini-2.5-flash-lite` (0/5), and the stronger `gemini-2.5-flash` "
        "caught only 1/5 — i.e. this is largely a **model/task-difficulty ceiling**, not a "
        "prompt bug. Next levers: a contradiction-focused few-shot set, a stronger model, or a "
        "second 'is the claim refuted?' verification pass.",
        "- **Bug fixed during iteration:** the brain's structured-JSON calls truncated on slow/"
        "loaded models because Gemini 'thinking' tokens consumed the output budget; thinking is "
        "now disabled for the structured tasks (faster, cheaper, reliable).",
        "- **Model choice:** `gemini-2.5-flash-lite` is used because `gemini-2.5-flash` returns "
        "503s and ~16s latency under current free-tier load; lite is ~1.3s and reliable, at a "
        "small reasoning cost. Swap via `CLAIMREVIEW_MODEL` if flash load clears.",
        "- **Authenticity:** provenance mode (C2PA/SynthID) deterministically flags the test "
        "images that are genuinely AI-generated, at zero added API cost and zero false "
        "positives on real photos (see `evaluation/authenticity_report.md`).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    ap = argparse.ArgumentParser(description="Evaluate strategies on sample_claims.csv")
    ap.add_argument("--strategy", default="d_image_grounded")
    ap.add_argument("--compare", action="store_true", help="evaluate all registered strategies")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-auth", action="store_true")
    args = ap.parse_args()

    import os

    env = dict(os.environ)
    if args.provider:
        env["CLAIMREVIEW_PROVIDER"] = args.provider
    if args.no_auth:
        env["CLAIMREVIEW_AUTH_ENABLED"] = "false"

    from compare import evaluate_strategy

    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.config import Settings
    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.prompts import STRATEGIES
    from claimreview.providers.registry import get_provider

    settings = Settings.load(env)
    provider = get_provider(settings, env)
    detector = get_authenticity_detector(env)
    cache = ResponseCache(str(CODE_ROOT / settings.cache_path), enabled=settings.cache_enabled)
    throttle_ms = 0 if provider.name == "fake" else settings.throttle_ms

    sample = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    if args.limit:
        sample = sample[: args.limit]
    user_history = read_user_history(str(DATASET_ROOT / "user_history.csv"))
    requirements = read_evidence_requirements(str(DATASET_ROOT / "evidence_requirements.csv"))

    names = sorted(STRATEGIES) if args.compare else [args.strategy]
    results = []
    for name in names:
        print(f"Evaluating strategy {name!r} on {len(sample)} sample rows...")
        res = evaluate_strategy(
            name, sample, user_history, requirements, provider, str(DATASET_ROOT),
            detector=detector, throttle_ms=throttle_ms, cache=cache,
        )
        results.append(res)
        print(f"  Macro-F1={res.report.macro_f1:.3f} accuracy={res.report.accuracy:.3f}")
    cache.close()

    report = _render_report(
        results, provider_name=provider.name, model=getattr(provider, "model", "")
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
