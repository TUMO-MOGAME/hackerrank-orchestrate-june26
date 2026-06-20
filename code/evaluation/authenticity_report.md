# Authenticity Detector — Fair Benchmark

- Detector model: `ensemble:c2pa+memoized:gemini`
- Decision threshold: confidence ≥ **0.70** AND ai_generated=true
- Balanced set: **12** images (6 AI-generated fakes, 6 real photos)
- Detector API calls (after content-hash dedupe): **6**

## Headline metrics

| Metric | Value |
|---|---|
| Precision (flagged that were truly AI) | 1.00 |
| Recall (AI fakes we caught) | 1.00 |
| F1 | 1.00 |
| Accuracy | 1.00 |
| **False-positive rate on REAL photos** | **0.00** |

## Confusion matrix

| | predicted REAL | predicted AI |
|---|---|---|
| actual REAL | 6 (TN) | 0 (FP) |
| actual AI | 0 (FN) | 6 (TP) |

_FP is the cost that matters most for the graded set: real claim images wrongly flagged as `non_original_image` would hurt the `risk_flags` score. Keep FP rate low._

## Per-image detail

| image | actual | predicted | conf | signals |
|---|---|---|---|---|
| `images/_generated_fakes/car/fake_01.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/_generated_fakes/car/fake_02.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/sample/case_001/img_1.jpg` | REAL | REAL | 0.10 |  |
| `images/sample/case_002/img_1.jpg` | REAL | REAL | 0.10 |  |
| `images/_generated_fakes/laptop/fake_01.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/_generated_fakes/laptop/fake_02.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/sample/case_009/img_1.jpg` | REAL | REAL | 0.10 |  |
| `images/sample/case_010/img_1.jpg` | REAL | REAL | 0.10 | low resolution and compression artifacts; unusual text rende |
| `images/_generated_fakes/package/fake_01.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/_generated_fakes/package/fake_02.png` | AI | AI | 0.99 | c2pa:trainedAlgorithmicMedia; synthid-watermark-ref |
| `images/sample/case_015/img_1.jpg` | REAL | REAL | 0.05 | slight blurriness in some text areas |
| `images/sample/case_016/img_1.jpg` | REAL | REAL | 0.05 |  |
