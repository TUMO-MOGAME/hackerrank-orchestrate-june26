"""Evaluation metrics — scoring math is deterministic and offline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation"))

from metrics import field_accuracy, render_report, score_claim_status  # noqa: E402


def test_score_claim_status_confusion_and_macro_f1():
    y_true = ["supported", "supported", "contradicted", "not_enough_information"]
    y_pred = ["supported", "contradicted", "contradicted", "not_enough_information"]
    r = score_claim_status(y_true, y_pred)

    assert r.confusion == [[1, 1, 0], [0, 1, 0], [0, 0, 1]]
    assert r.accuracy == 0.75
    assert r.per_class["supported"]["precision"] == 1.0
    assert r.per_class["supported"]["recall"] == 0.5
    assert abs(r.per_class["contradicted"]["precision"] - 0.5) < 1e-9
    assert r.per_class["not_enough_information"]["f1"] == 1.0
    assert abs(r.macro_f1 - (2 / 3 + 2 / 3 + 1.0) / 3) < 1e-6


def test_perfect_prediction():
    y = ["supported", "contradicted", "not_enough_information"]
    r = score_claim_status(y, list(y))
    assert r.accuracy == 1.0
    assert r.macro_f1 == 1.0


def test_field_accuracy():
    assert field_accuracy(["dent", "scratch", "crack"], ["dent", "scratch", "none"]) == 2 / 3
    assert field_accuracy([], []) == 0.0


def test_render_report_is_markdown():
    r = score_claim_status(["supported"], ["supported"])
    md = render_report(r, title="claim_status")
    assert "Macro-F1" in md
    assert "Confusion matrix" in md
