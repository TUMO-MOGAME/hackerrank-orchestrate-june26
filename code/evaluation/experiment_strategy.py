"""Experiment: compare prompt strategies on a fixed model (the .env model).

Scores each named strategy's claim_status against the gold sample labels and prints per-class
metrics. Cache keys include the strategy's system prompt, so already-run strategies are free.
Does NOT write the report or output.csv.

Usage:
    python evaluation/experiment_strategy.py a_zero_shot d_image_grounded
"""

from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_ROOT.parent
DATASET_ROOT = REPO_ROOT / "dataset"
sys.path.insert(0, str(CODE_ROOT / "src"))
sys.path.insert(0, str(CODE_ROOT / "evaluation"))


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    import os

    from compare import evaluate_strategy

    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.config import Settings
    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.providers.registry import get_provider

    names = sys.argv[1:] or ["a_zero_shot", "d_image_grounded"]
    env = dict(os.environ)
    settings = Settings.load(env)
    provider = get_provider(settings, env)
    detector = get_authenticity_detector(env)
    cache = ResponseCache(str(CODE_ROOT / settings.cache_path), enabled=True)

    sample = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    history = read_user_history(str(DATASET_ROOT / "user_history.csv"))
    reqs = read_evidence_requirements(str(DATASET_ROOT / "evidence_requirements.csv"))

    print(f"model={getattr(provider,'model','')}  sample={len(sample)} rows\n")
    for name in names:
        res = evaluate_strategy(
            name, sample, history, reqs, provider, str(DATASET_ROOT),
            detector=detector, throttle_ms=settings.throttle_ms, cache=cache,
        )
        pc = res.report.per_class
        print(f"=== {name} ===  Macro-F1 {res.report.macro_f1:.3f} | acc {res.report.accuracy:.3f} "
              f"| calls={res.stats.model_calls} cache_hits={res.stats.cache_hits}")
        for c in ("supported", "contradicted", "not_enough_information"):
            m = pc[c]
            print(f"    {c:24s} P={m['precision']:.2f} R={m['recall']:.2f} "
                  f"F1={m['f1']:.2f} n={m['support']}")
        sec = "  ".join(f"{k}={v:.2f}" for k, v in res.secondary.items())
        print(f"    secondary: {sec}\n")

    cache.close()


if __name__ == "__main__":
    main()
