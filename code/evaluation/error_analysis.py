"""Error analysis: which sample rows does the production config get wrong, and why?

Runs the production config (strategy A + the .env model) over the labeled sample via the
cached batch runner, lines predictions up against the gold labels, and prints every
misclassified row with its object, the model's own justification, and an error category.
Feeds the "Findings" section of evaluation_report.md. Reuses the cache, so it is free to
re-run after the metrics have been generated once.

Usage:
    python evaluation/error_analysis.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_ROOT.parent
DATASET_ROOT = REPO_ROOT / "dataset"
sys.path.insert(0, str(CODE_ROOT / "src"))


def categorize(gold: str, pred: str) -> str:
    if gold == pred:
        return "correct"
    if pred == "contradicted" and gold in ("supported", "not_enough_information"):
        return "over-contradiction (false positive)"
    if gold == "contradicted" and pred != "contradicted":
        return "missed contradiction"
    if pred == "not_enough_information":
        return "over-cautious (called NEI)"
    if gold == "not_enough_information" and pred == "supported":
        return "over-confident (NEI->supported)"
    return f"{gold}->{pred}"


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    import os

    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.config import Settings
    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.pipeline.runner import run_batch
    from claimreview.prompts import STRATEGIES
    from claimreview.providers.registry import get_provider

    env = dict(os.environ)
    settings = Settings.load(env)
    provider = get_provider(settings, env)
    detector = get_authenticity_detector(env)
    cache = ResponseCache(str(CODE_ROOT / settings.cache_path), enabled=True)

    sample = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    history = read_user_history(str(DATASET_ROOT / "user_history.csv"))
    reqs = read_evidence_requirements(str(DATASET_ROOT / "evidence_requirements.csv"))

    strat = sys.argv[1] if len(sys.argv) > 1 else "d_image_grounded"
    res = run_batch(
        sample, history, reqs, provider, STRATEGIES[strat].build_system_prompt,
        str(DATASET_ROOT), detector=detector, throttle_ms=settings.throttle_ms, cache=cache,
    )
    cache.close()

    cats = Counter()
    misses = []
    for gold_row, pred in zip(sample, res.rows, strict=False):
        g, p = gold_row["claim_status"], pred["claim_status"]
        cat = categorize(g, p)
        cats[cat] += 1
        if g != p:
            misses.append((gold_row, pred, cat))

    n = len(sample)
    print(f"model={getattr(provider,'model','')}  sample={n}  "
          f"correct={cats['correct']}/{n} ({cats['correct']/n:.0%})  "
          f"model_calls={res.stats.model_calls} cache_hits={res.stats.cache_hits}\n")
    print("Error categories:")
    for cat, c in cats.most_common():
        if cat != "correct":
            print(f"  {c:2d}  {cat}")
    print(f"\n{len(misses)} misclassified rows:\n")
    for gr, pr, cat in misses:
        print(f"[{cat}]  {gr['user_id']} {gr['claim_object']}: gold={gr['claim_status']} "
              f"pred={pr['claim_status']}")
        print(f"    issue={pr['issue_type']} part={pr['object_part']} "
              f"valid_image={pr['valid_image']}")
        print(f"    model says: {pr['claim_status_justification'][:150]}\n")


if __name__ == "__main__":
    main()
