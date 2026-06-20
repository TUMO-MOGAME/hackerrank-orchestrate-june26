"""Experiment: does a stronger model lift the `contradicted` class on the sample set?

Runs Strategy A over dataset/sample_claims.csv for each candidate model and prints the
per-class metrics (focus: contradicted recall/F1) + macro-F1 + tokens. Does NOT write the
report. Cache keys include the model, so models don't collide and reruns are free.

Usage:
    python evaluation/experiment_contradicted.py gemini-2.5-flash-lite gemini-3-flash-preview
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

    models = sys.argv[1:] or ["gemini-2.5-flash-lite"]
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("no GEMINI_API_KEY")

    from compare import evaluate_strategy

    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.providers.gemini_provider import GeminiProvider

    sample = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    history = read_user_history(str(DATASET_ROOT / "user_history.csv"))
    reqs = read_evidence_requirements(str(DATASET_ROOT / "evidence_requirements.csv"))
    detector = get_authenticity_detector(dict(os.environ))
    cache = ResponseCache(str(CODE_ROOT / ".cache" / "claimreview.sqlite"), enabled=True)

    print(f"sample rows: {len(sample)}  (contradicted gold: "
          f"{sum(1 for r in sample if r['claim_status'] == 'contradicted')})\n")

    for model in models:
        provider = GeminiProvider(api_key=key, model=model)
        res = evaluate_strategy(
            "a_zero_shot", sample, history, reqs, provider, str(DATASET_ROOT),
            detector=detector, throttle_ms=4500, cache=cache,
        )
        pc = res.report.per_class
        c = pc["contradicted"]
        print(f"=== {model} ===")
        print(f"  Macro-F1 {res.report.macro_f1:.3f} | accuracy {res.report.accuracy:.3f}")
        for cls in ("supported", "contradicted", "not_enough_information"):
            m = pc[cls]
            print(f"  {cls:24s} P={m['precision']:.2f} R={m['recall']:.2f} "
                  f"F1={m['f1']:.2f} n={m['support']}")
        print(f"  contradicted recall: {c['recall']:.2f}  "
              f"({round(c['recall'] * c['support'])}/{c['support']} caught)")
        print(f"  tokens in/out: {res.stats.input_tokens}/{res.stats.output_tokens} "
              f"calls={res.stats.model_calls} cache_hits={res.stats.cache_hits}\n")

    cache.close()


if __name__ == "__main__":
    main()
