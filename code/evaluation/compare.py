"""Compare >=2 prompt strategies on sample_claims.csv.

Runs each strategy over the labeled sample set through the SAME pipeline used for the real
output (run_batch), scores claim_status, and tabulates the results so the final choice for
output.csv is justified. Satisfies the README's "at least two strategies compared".
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics import ClassificationReport, field_accuracy, score_claim_status

from claimreview.pipeline.runner import BatchStats, run_batch
from claimreview.prompts import STRATEGIES
from claimreview.schema.output_schema import GENERATED_COLUMNS

# Secondary fields scored as exact-match accuracy (diagnostic, not the primary metric).
SECONDARY_FIELDS = ["issue_type", "object_part", "severity", "evidence_standard_met", "valid_image"]


@dataclass
class StrategyResult:
    name: str
    report: ClassificationReport
    secondary: dict           # field -> accuracy
    stats: BatchStats


def evaluate_strategy(
    strategy_name: str,
    sample_rows: list[dict],
    user_history: dict,
    requirements: list[dict],
    provider,
    dataset_root: str,
    *,
    detector=None,
    throttle_ms: int = 0,
    cache=None,
) -> StrategyResult:
    """Run one strategy over the sample set and score it against the gold labels."""
    strategy = STRATEGIES[strategy_name]
    result = run_batch(
        sample_rows, user_history, requirements, provider, strategy.build_system_prompt,
        dataset_root, detector=detector, throttle_ms=throttle_ms, cache=cache,
    )
    preds = result.rows
    report = score_claim_status(
        [r["claim_status"] for r in sample_rows],
        [r["claim_status"] for r in preds],
    )
    secondary = {
        f: field_accuracy([r[f] for r in sample_rows], [r[f] for r in preds])
        for f in SECONDARY_FIELDS if f in GENERATED_COLUMNS
    }
    return StrategyResult(strategy_name, report, secondary, result.stats)


def render_comparison(results: list[StrategyResult]) -> str:
    """Markdown table: strategy x (Macro-F1, accuracy, per-class F1)."""
    lines = [
        "| Strategy | Macro-F1 | Accuracy | F1 supported | F1 contradicted | F1 NEI |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        pc = r.report.per_class
        lines.append(
            f"| {r.name} | {r.report.macro_f1:.3f} | {r.report.accuracy:.3f} "
            f"| {pc['supported']['f1']:.2f} | {pc['contradicted']['f1']:.2f} "
            f"| {pc['not_enough_information']['f1']:.2f} |"
        )
    return "\n".join(lines)
