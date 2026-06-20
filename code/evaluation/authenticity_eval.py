"""Fair, blind benchmark of the authenticity detector: AI fakes vs real photos.

Builds a balanced, per-object set — every generated fake (label=AI) matched by an equal
number of real claim photos sampled from `dataset/images/sample/` (label=REAL) — runs the
detector blind (it never sees labels), and reports precision / recall / F1 / accuracy, a
confusion matrix, and the false-positive rate on REAL images (the number that protects the
graded `risk_flags` score: a trigger-happy detector would wrongly flag genuine photos).

Run gen_fakes.py first (or pass --gen to do it here).

Usage:
    python code/evaluation/authenticity_eval.py --gen --count 3
    python code/evaluation/authenticity_eval.py --threshold 0.7
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]          # code/
REPO_ROOT = CODE_ROOT.parent
DATASET_ROOT = REPO_ROOT / "dataset"
FAKES_ROOT = DATASET_ROOT / "images" / "_generated_fakes"
REPORT_PATH = CODE_ROOT / "evaluation" / "authenticity_report.md"

sys.path.insert(0, str(CODE_ROOT / "src"))

from claimreview.authenticity.detector import DEFAULT_THRESHOLD  # noqa: E402
from claimreview.io.csv_io import read_sample_claims  # noqa: E402
from claimreview.io.images import load_images, split_image_paths  # noqa: E402


def _load_one(rel_path: str):
    """Load a single image file (relative to dataset/) into a LoadedImage, or None."""
    imgs = load_images(rel_path, str(DATASET_ROOT))
    return imgs[0] if imgs else None


def collect_fakes() -> dict[str, list]:
    """Generated fakes grouped by object: {object: [LoadedImage, ...]}."""
    by_obj: dict[str, list] = defaultdict(list)
    for obj_dir in sorted(p for p in FAKES_ROOT.glob("*") if p.is_dir()):
        for img_file in sorted(obj_dir.glob("*.png")):
            rel = img_file.relative_to(DATASET_ROOT).as_posix()
            img = _load_one(rel)
            if img:
                by_obj[obj_dir.name].append(img)
    return by_obj


def collect_reals() -> dict[str, list]:
    """Real first-images from sample_claims.csv grouped by object (deterministic order)."""
    by_obj: dict[str, list] = defaultdict(list)
    rows = read_sample_claims(str(DATASET_ROOT / "sample_claims.csv"))
    for row in rows:
        paths = split_image_paths(row["image_paths"])
        if not paths:
            continue
        img = _load_one(paths[0])
        if img:
            by_obj[row["claim_object"]].append(img)
    return by_obj


def build_balanced_set(fakes: dict[str, list], reals: dict[str, list]):
    """Per object, pair each fake with one real. Returns (images, labels, objects).

    labels: 1 = AI-generated (fake), 0 = real photo.
    """
    images, labels, objects = [], [], []
    for obj in sorted(set(fakes) | set(reals)):
        f, r = fakes.get(obj, []), reals.get(obj, [])
        n = min(len(f), len(r))   # balanced within each object
        for img in f[:n]:
            images.append(img)
            labels.append(1)
            objects.append(obj)
        for img in r[:n]:
            images.append(img)
            labels.append(0)
            objects.append(obj)
    return images, labels, objects


def evaluate(detector, images, labels, threshold: float):
    """Run the detector and compute binary metrics + per-image rows."""
    verdicts = detector.assess(images)
    preds, rows = [], []
    for img, label, v in zip(images, labels, verdicts, strict=True):
        pred = 1 if (v.ai_generated and v.confidence >= threshold) else 0
        preds.append(pred)
        rows.append({
            "id": img.image_id, "rel": img.rel_path, "label": label, "pred": pred,
            "ai": v.ai_generated, "conf": v.confidence, "signals": v.signals,
        })

    pairs = list(zip(labels, preds, strict=True))
    tp = sum(1 for y, p in pairs if y == 1 and p == 1)
    fn = sum(1 for y, p in pairs if y == 1 and p == 0)
    tn = sum(1 for y, p in pairs if y == 0 and p == 0)
    fp = sum(1 for y, p in pairs if y == 0 and p == 1)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(labels) if labels else 0.0
    fp_rate = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        "precision": precision, "recall": recall, "f1": f1,
        "accuracy": accuracy, "fp_rate": fp_rate, "rows": rows,
    }


def render_report(m: dict, *, threshold: float, model: str, inner_calls: int) -> str:
    n = len(m["rows"])
    n_fake = sum(1 for r in m["rows"] if r["label"] == 1)
    lines = [
        "# Authenticity Detector — Fair Benchmark",
        "",
        f"- Detector model: `{model}`",
        f"- Decision threshold: confidence ≥ **{threshold:.2f}** AND ai_generated=true",
        f"- Balanced set: **{n}** images ({n_fake} AI-generated fakes, {n - n_fake} real photos)",
        f"- Detector API calls (after content-hash dedupe): **{inner_calls}**",
        "",
        "## Headline metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Precision (flagged that were truly AI) | {m['precision']:.2f} |",
        f"| Recall (AI fakes we caught) | {m['recall']:.2f} |",
        f"| F1 | {m['f1']:.2f} |",
        f"| Accuracy | {m['accuracy']:.2f} |",
        f"| **False-positive rate on REAL photos** | **{m['fp_rate']:.2f}** |",
        "",
        "## Confusion matrix",
        "",
        "| | predicted REAL | predicted AI |",
        "|---|---|---|",
        f"| actual REAL | {m['tn']} (TN) | {m['fp']} (FP) |",
        f"| actual AI | {m['fn']} (FN) | {m['tp']} (TP) |",
        "",
        "_FP is the cost that matters most for the graded set: real claim images wrongly "
        "flagged as `non_original_image` would hurt the `risk_flags` score. Keep FP rate low._",
        "",
        "## Per-image detail",
        "",
        "| image | actual | predicted | conf | signals |",
        "|---|---|---|---|---|",
    ]
    for r in m["rows"]:
        actual = "AI" if r["label"] == 1 else "REAL"
        pred = "AI" if r["pred"] == 1 else "REAL"
        mark = "" if r["label"] == r["pred"] else " ❌"
        sig = "; ".join(r["signals"])[:60]
        lines.append(f"| `{r['rel']}` | {actual} | {pred}{mark} | {r['conf']:.2f} | {sig} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    ap = argparse.ArgumentParser(description="Fair benchmark: AI fakes vs real photos.")
    ap.add_argument("--gen", action="store_true", help="generate fakes first (calls image API)")
    ap.add_argument("--count", type=int, default=3, help="fakes per object when --gen")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = ap.parse_args()

    if args.gen:
        from gen_fakes import generate

        print("Generating fakes...")
        generate(args.count)

    fakes, reals = collect_fakes(), collect_reals()
    if not any(fakes.values()):
        print(f"No fakes found under {FAKES_ROOT}. Run with --gen first.")
        raise SystemExit(1)

    images, labels, _ = build_balanced_set(fakes, reals)
    from claimreview.authenticity.factory import get_authenticity_detector

    detector = get_authenticity_detector()
    if detector is None:
        print("Authenticity detector unavailable (key missing or disabled).")
        raise SystemExit(1)

    m = evaluate(detector, images, labels, args.threshold)
    inner_calls = int(getattr(detector, "calls", 0))   # API calls made (0 for pure provenance)
    report = render_report(
        m, threshold=args.threshold, model=detector.name, inner_calls=inner_calls
    )
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"\nBalanced set: {len(images)} images "
          f"({sum(labels)} fake / {len(labels) - sum(labels)} real)")
    print(f"precision={m['precision']:.2f} recall={m['recall']:.2f} f1={m['f1']:.2f} "
          f"accuracy={m['accuracy']:.2f} fp_rate_on_reals={m['fp_rate']:.2f}")
    print(f"Report written to {REPORT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
