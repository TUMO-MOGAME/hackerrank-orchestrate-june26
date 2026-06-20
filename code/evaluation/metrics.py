"""Classification metrics for claim_status (the primary scored field).

Accuracy alone is misleading under class imbalance (most sample claims are 'supported').
We report per-class precision/recall/F1, Macro-F1 (equal weight to minority classes), and
a confusion matrix. Hand-rolled (no sklearn dependency) so the numbers are transparent and
the evaluation runs with only the stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass

CLAIM_STATUS_CLASSES = ["supported", "contradicted", "not_enough_information"]


@dataclass
class ClassificationReport:
    per_class: dict          # class -> {precision, recall, f1, support}
    macro_f1: float
    accuracy: float
    confusion: list[list[int]]   # rows=actual, cols=predicted (CLAIM_STATUS_CLASSES order)
    classes: list[str]


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def score_claim_status(
    y_true: list[str], y_pred: list[str], classes: list[str] | None = None
) -> ClassificationReport:
    """Compute the per-class + macro report and confusion matrix for claim_status."""
    classes = classes or CLAIM_STATUS_CLASSES
    idx = {c: i for i, c in enumerate(classes)}
    n = len(classes)
    confusion = [[0] * n for _ in range(n)]

    scored = 0
    for t, p in zip(y_true, y_pred, strict=True):
        if t not in idx:
            continue                      # skip rows with an out-of-vocab gold label
        scored += 1
        # An out-of-class prediction can't match any class -> recorded as a miss (no column).
        if p in idx:
            confusion[idx[t]][idx[p]] += 1

    per_class = {}
    f1s = []
    correct = 0
    for c, i in idx.items():
        tp = confusion[i][i]
        fp = sum(confusion[r][i] for r in range(n)) - tp
        fn = sum(confusion[i]) - tp
        precision, recall, f1 = _prf(tp, fp, fn)
        per_class[c] = {
            "precision": precision, "recall": recall, "f1": f1, "support": sum(confusion[i]),
        }
        f1s.append(f1)
        correct += tp

    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    accuracy = correct / scored if scored else 0.0
    return ClassificationReport(per_class, macro_f1, accuracy, confusion, classes)


def field_accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """Exact-match accuracy for a secondary field (issue_type, object_part, severity, …)."""
    pairs = list(zip(y_true, y_pred, strict=True))
    if not pairs:
        return 0.0
    return sum(1 for t, p in pairs if t == p) / len(pairs)


def render_report(report: ClassificationReport, *, title: str = "claim_status") -> str:
    """Format a ClassificationReport as markdown (per-class table + confusion matrix)."""
    lines = [
        f"**{title}** — Macro-F1 **{report.macro_f1:.3f}**, accuracy **{report.accuracy:.3f}**",
        "",
        "| class | precision | recall | F1 | support |",
        "|---|---|---|---|---|",
    ]
    for c in report.classes:
        m = report.per_class[c]
        lines.append(
            f"| {c} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} | {m['support']} |"
        )
    lines += ["", "Confusion matrix (rows = actual, cols = predicted):", ""]
    header = "| actual \\ pred | " + " | ".join(report.classes) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(report.classes) + 1))
    for i, c in enumerate(report.classes):
        lines.append(f"| {c} | " + " | ".join(str(x) for x in report.confusion[i]) + " |")
    lines.append("")
    return "\n".join(lines)
