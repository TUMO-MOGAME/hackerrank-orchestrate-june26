"""Experiment: does an independent verification pass improve claim_status on the sample?

Runs the production pass-1 (strategy A) over sample_claims.csv, then a second independent
verification pass on the decisive rows, and scores every reconciliation policy against the
gold labels. Prints a comparison so the best policy (if any) can be chosen empirically.
Does NOT write the report or output.csv.

Usage:
    python evaluation/experiment_verify.py            # default model from .env
    python evaluation/experiment_verify.py gemini-3-flash-preview
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

    from metrics import score_claim_status

    from claimreview.adjudicator.adjudicator import adjudicate_with_images
    from claimreview.authenticity.factory import get_authenticity_detector
    from claimreview.context.assembler import assemble_context
    from claimreview.io.csv_io import (
        read_evidence_requirements,
        read_sample_claims,
        read_user_history,
    )
    from claimreview.io.images import load_images
    from claimreview.pipeline.cache import ResponseCache
    from claimreview.pipeline.throttle import sleep_ms
    from claimreview.pipeline.verification import POLICIES, apply_verification, should_verify
    from claimreview.prompts import STRATEGIES
    from claimreview.prompts import verification as verify_prompt
    from claimreview.providers.gemini_provider import GeminiProvider
    from claimreview.schema.output_schema import repair_generated_fields

    model = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAIMREVIEW_MODEL", "")
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("no GEMINI_API_KEY")

    sample = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    history = read_user_history(str(DATASET_ROOT / "user_history.csv"))
    reqs = read_evidence_requirements(str(DATASET_ROOT / "evidence_requirements.csv"))
    detector = get_authenticity_detector(dict(os.environ))
    provider = GeminiProvider(api_key=key, model=model)
    cache = ResponseCache(str(CODE_ROOT / ".cache" / "claimreview.sqlite"), enabled=True)
    stratA = STRATEGIES["a_zero_shot"].build_system_prompt

    gold = [r["claim_status"] for r in sample]
    status1: list[str] = []
    status2: list[str] = []  # second-pass status (== status1 when row not verified)
    n_verified = 0

    print(f"model={model}  sample={len(sample)} rows\n")
    for r in sample:
        images = load_images(r.get("image_paths", ""), str(DATASET_ROOT))
        row1 = adjudicate_with_images(
            r, history, reqs, provider, stratA(r["claim_object"]), images, detector=detector,
        )
        sleep_ms(4500)  # stay under the free-tier RPM ceiling between live calls
        s1 = row1["claim_status"]
        s2 = s1
        if should_verify(row1) and images:
            ctx = assemble_context(r, history, reqs)
            sysp = verify_prompt.build_system_prompt(r["claim_object"])
            res = provider.adjudicate(sysp, ctx, images)
            ids = {i.image_id for i in images}
            fixed = repair_generated_fields(res.fields, r["claim_object"], ids)
            s2 = fixed["claim_status"]
            n_verified += 1
            sleep_ms(4500)
        status1.append(s1)
        status2.append(s2)

    def _report(name: str, preds: list[str]) -> None:
        rep = score_claim_status(gold, preds)
        pc = rep.per_class
        changed = sum(1 for a, b in zip(status1, preds, strict=False) if a != b)
        print(f"=== {name} ===  Macro-F1 {rep.macro_f1:.3f} | acc {rep.accuracy:.3f} "
              f"| changed-from-pass1 {changed}")
        for c in ("supported", "contradicted", "not_enough_information"):
            m = pc[c]
            print(f"    {c:24s} P={m['precision']:.2f} R={m['recall']:.2f} "
                  f"F1={m['f1']:.2f} n={m['support']}")

    print(f"verified rows (decisive + usable images): {n_verified}\n")
    _report("baseline (pass-1 only)", status1)
    for policy in POLICIES:
        finals = []
        for s1, s2 in zip(status1, status2, strict=False):
            row = {"claim_status": s1, "valid_image": "true", "risk_flags": "none",
                   "supporting_image_ids": "x", "evidence_standard_met": "true",
                   "claim_status_justification": ""}
            finals.append(apply_verification(row, s2, policy)["claim_status"])
        _report(f"policy={policy}", finals)

    cache.close()


if __name__ == "__main__":
    main()
