"""C2PA provenance detector + ensemble logic (offline, deterministic)."""

from __future__ import annotations

import base64

from claimreview.authenticity.detector import (
    AuthenticityDetector,
    FakeAuthenticityDetector,
    ImageAuthenticity,
)
from claimreview.authenticity.ensemble import EnsembleAuthenticityDetector
from claimreview.authenticity.provenance import C2PAProvenanceDetector
from claimreview.io.images import LoadedImage


def _img(image_id: str, raw: bytes) -> LoadedImage:
    return LoadedImage(
        image_id=image_id,
        rel_path=f"{image_id}.png",
        mime_type="image/png",
        data_b64=base64.b64encode(raw).decode("ascii"),
    )


def test_c2pa_ai_assertion_flags_high_confidence():
    raw = b"\x89PNG....jumbf...urn:c2pa...trainedAlgorithmicMedia...SynthID..."
    v = C2PAProvenanceDetector().assess([_img("img_1", raw)])[0]
    assert v.ai_generated is True
    assert v.confidence >= 0.9
    assert any("trainedAlgorithmicMedia" in s for s in v.signals)


def test_plain_photo_not_flagged():
    raw = b"\xff\xd8\xff\xe0\x00\x10JFIF ordinary jpeg bytes with no provenance"
    v = C2PAProvenanceDetector().assess([_img("img_1", raw)])[0]
    assert v.ai_generated is False
    assert v.confidence == 0.0
    assert v.signals == []


def test_c2pa_manifest_without_ai_assertion_is_not_definitive():
    # A C2PA manifest alone (no AI assertion, no SynthID) is provenance but not proof of AI.
    raw = b"....jumbf...urn:c2pa...some camera manifest..."
    v = C2PAProvenanceDetector().assess([_img("img_1", raw)])[0]
    assert v.ai_generated is False
    assert "c2pa-manifest" in v.signals


def test_ensemble_provenance_overrides_vlm_and_short_circuits():
    class CountingVLM(AuthenticityDetector):
        name = "vlm"

        def __init__(self):
            self.calls = 0

        def assess(self, images):
            self.calls += len(images)
            return [ImageAuthenticity(i.image_id, False, 0.1) for i in images]

    ai_raw = b"jumbf urn:c2pa trainedAlgorithmicMedia SynthID"
    real_raw = b"plain jpeg no provenance"
    vlm = CountingVLM()
    ens = EnsembleAuthenticityDetector([C2PAProvenanceDetector(), vlm])

    out = ens.assess([_img("ai", ai_raw), _img("real", real_raw)])
    by_id = {v.image_id: v for v in out}
    # provenance settles the AI image; VLM is skipped for it (only the real image reaches VLM)
    assert by_id["ai"].ai_generated is True
    assert by_id["real"].ai_generated is False
    assert vlm.calls == 1


def test_ensemble_falls_back_to_vlm_when_no_provenance():
    real_raw = b"plain jpeg no provenance"
    vlm = FakeAuthenticityDetector(ai_generated=True, confidence=0.95, signals=["diffusion noise"])
    ens = EnsembleAuthenticityDetector([C2PAProvenanceDetector(), vlm])
    v = ens.assess([_img("x", real_raw)])[0]
    assert v.ai_generated is True
    assert v.confidence == 0.95
    assert "diffusion noise" in v.signals
