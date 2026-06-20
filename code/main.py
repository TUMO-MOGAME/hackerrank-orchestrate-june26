"""Terminal entry point (CONTRACT — do not rename; see AGENTS.md §6).

Runs the full claim-review system over dataset/claims.csv and writes output.csv with the
exact 14-column schema. Provider, strategy and operational options come from env/config and
CLI flags.

Usage:
    python code/main.py                       # provider/strategy from .env, full claims.csv
    python code/main.py --provider fake       # offline smoke run (no API/cost)
    python code/main.py --limit 5             # first 5 claims only (dev)
    python code/main.py --strategy a_zero_shot --no-cache
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))


def _build_env(args) -> dict:
    env = dict(os.environ)
    if args.provider:
        env["CLAIMREVIEW_PROVIDER"] = args.provider
    if args.no_cache:
        env["CLAIMREVIEW_CACHE_ENABLED"] = "false"
    if args.no_auth:
        env["CLAIMREVIEW_AUTH_ENABLED"] = "false"
    return env


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")

    ap = argparse.ArgumentParser(description="Run damage-claim verification -> output.csv")
    ap.add_argument("--input", default=str(REPO_ROOT / "dataset" / "claims.csv"))
    ap.add_argument("--output", default=str(REPO_ROOT / "output.csv"))
    ap.add_argument("--provider", default=None, help="override CLAIMREVIEW_PROVIDER")
    ap.add_argument("--strategy", default="d_image_grounded", help="prompt strategy key")
    ap.add_argument("--limit", type=int, default=None, help="process only the first N claims")
    ap.add_argument("--throttle-ms", type=int, default=None, help="override delay between calls")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--no-auth", action="store_true", help="disable authenticity detection")
    args = ap.parse_args()

    env = _build_env(args)

    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.config import Settings
    from claimreview.io.csv_io import (
        read_claims,
        read_evidence_requirements,
        read_user_history,
        write_output,
    )
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.pipeline.runner import run_batch
    from claimreview.prompts import STRATEGIES
    from claimreview.providers.registry import get_provider

    settings = Settings.load(env)
    if args.strategy not in STRATEGIES:
        ap.error(f"unknown strategy {args.strategy!r}; choose from {sorted(STRATEGIES)}")
    strategy = STRATEGIES[args.strategy]

    dataset_root = str(REPO_ROOT / "dataset")
    claims = read_claims(args.input)
    if args.limit:
        claims = claims[: args.limit]
    user_history = read_user_history(str(REPO_ROOT / "dataset" / "user_history.csv"))
    requirements = read_evidence_requirements(
        str(REPO_ROOT / "dataset" / "evidence_requirements.csv")
    )

    provider = get_provider(settings, env)
    detector = get_authenticity_detector(env)
    cache = ResponseCache(str(CODE_ROOT / settings.cache_path), enabled=settings.cache_enabled)

    # The offline fake provider has no rate limit; don't waste wall-clock throttling it.
    throttle_ms = 0 if provider.name == "fake" else settings.throttle_ms
    if args.throttle_ms is not None:
        throttle_ms = args.throttle_ms

    print(
        f"Running {len(claims)} claims | provider={provider.name} strategy={strategy.NAME} "
        f"auth={'on' if detector else 'off'} cache={'on' if settings.cache_enabled else 'off'} "
        f"throttle={throttle_ms}ms"
    )

    def on_progress(done: int, total: int) -> None:
        if done == total or done % 10 == 0:
            print(f"  ...{done}/{total}")

    result = run_batch(
        claims, user_history, requirements, provider, strategy.build_system_prompt, dataset_root,
        detector=detector, throttle_ms=throttle_ms, max_retries=settings.max_retries,
        cache=cache, on_progress=on_progress,
    )
    cache.close()

    n = write_output(args.output, result.rows)
    s = result.stats
    print(
        f"\nWrote {n} rows -> {args.output}\n"
        f"  model_calls={s.model_calls} cache_hits={s.cache_hits} auth_calls={s.auth_calls} "
        f"failures={s.failures}\n"
        f"  images={s.images} input_tokens={s.input_tokens} output_tokens={s.output_tokens} "
        f"elapsed={s.elapsed_s:.1f}s"
    )


if __name__ == "__main__":
    main()
