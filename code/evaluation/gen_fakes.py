"""Generate synthetic (AI-generated) damage images to benchmark the authenticity detector.

These images are FAKE on purpose. They are written under
`dataset/images/_generated_fakes/<object>/`, a directory that `claims.csv` and
`sample_claims.csv` never reference — so they can never enter the graded `output.csv`.
They exist solely so `authenticity_eval.py` can measure, fairly and blind, how well the
detector catches AI-generated "evidence".

Idempotent: an image that already exists on disk is not regenerated (saves quota).

Usage:
    python code/evaluation/gen_fakes.py --count 3
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]          # code/
REPO_ROOT = CODE_ROOT.parent
FAKES_ROOT = REPO_ROOT / "dataset" / "images" / "_generated_fakes"
DEFAULT_IMAGE_MODEL = "gemini-2.5-flash-image"

# Photoreal prompts per object — phrased to look like ordinary amateur claim photos so the
# benchmark is honest (we are NOT generating obviously-cartoonish fakes).
PROMPTS = {
    "car": [
        "photorealistic amateur smartphone photo of a car with a large dented and scratched "
        "front bumper, parked outdoors in daylight, slightly imperfect snapshot",
        "realistic phone photo of a car door with a deep scratch and a dent, sunny day",
        "realistic photo of a car with a cracked windshield, close up, overcast light",
    ],
    "laptop": [
        "photorealistic photo of an open laptop with a shattered, cracked screen, on a wooden "
        "desk indoors, ordinary room lighting",
        "realistic phone photo of a laptop with a dented bent corner and a damaged hinge",
        "realistic close-up photo of a laptop lid with deep scratches, on a table",
    ],
    "package": [
        "photorealistic photo of a crushed, dented cardboard delivery box on a doorstep",
        "realistic phone photo of a torn, ripped shipping package with exposed contents indoors",
        "realistic photo of a water-damaged, stained cardboard box, close up",
    ],
}


def _generate_one(client, model: str, prompt: str) -> bytes | None:
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in response.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            return inline.data
    return None


def generate(
    count_per_object: int = 3,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    api_key: str | None = None,
    env: dict | None = None,
) -> list[Path]:
    """Generate up to `count_per_object` fakes per object. Returns the paths on disk."""
    from google import genai

    e = os.environ if env is None else env
    key = api_key or e.get("GEMINI_API_KEY") or e.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY / GOOGLE_API_KEY not set")
    client = genai.Client(api_key=key)

    written: list[Path] = []
    for obj, prompts in PROMPTS.items():
        out_dir = FAKES_ROOT / obj
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(count_per_object):
            dest = out_dir / f"fake_{i + 1:02d}.png"
            if dest.exists():
                written.append(dest)
                continue
            data = _generate_one(client, model, prompts[i % len(prompts)])
            if data:
                dest.write_bytes(data)
                written.append(dest)
                print(f"  generated {dest.relative_to(REPO_ROOT)} ({len(data)} bytes)")
            else:
                print(f"  WARNING: no image returned for {obj} prompt #{i + 1}")
    return written


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(CODE_ROOT / ".env")
    ap = argparse.ArgumentParser(description="Generate AI fake damage images for the benchmark.")
    ap.add_argument("--count", type=int, default=3, help="fakes per object (car/laptop/package)")
    ap.add_argument("--model", default=DEFAULT_IMAGE_MODEL)
    args = ap.parse_args()
    paths = generate(args.count, model=args.model)
    print(f"Done. {len(paths)} fake images under {FAKES_ROOT.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
