"""Image loading: resolve semicolon-separated image_paths to local files and encode.

Images are the primary source of truth. We pass image bytes inline (base64) to the
model rather than relying on URL fetches. The image ID is the filename without
extension (e.g. `img_1`), used in supporting_image_ids.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


@dataclass(frozen=True)
class LoadedImage:
    image_id: str        # filename without extension, e.g. "img_1"
    rel_path: str        # path as it appears in image_paths
    mime_type: str       # image/jpeg, image/png, ...
    data_b64: str        # base64-encoded bytes


def split_image_paths(image_paths: str) -> list[str]:
    """Split the semicolon-separated image_paths field into trimmed, non-empty paths."""
    return [p.strip() for p in str(image_paths).split(";") if p.strip()]


def image_id_from_path(rel_path: str) -> str:
    """Return the filename without extension (the image ID)."""
    return Path(rel_path).stem


def _mime_for(rel_path: str) -> str:
    return _MIME_BY_SUFFIX.get(Path(rel_path).suffix.lower(), "application/octet-stream")


def load_images(image_paths: str, dataset_root: str) -> list[LoadedImage]:
    """Resolve each path under dataset_root, read bytes, detect MIME, base64-encode.

    Skips paths that don't exist on disk (the adjudicator decides how to treat a claim
    with no usable images). `dataset_root` is the directory that the CSV paths are
    relative to (the one containing `images/`).
    """
    root = Path(dataset_root)
    loaded: list[LoadedImage] = []
    for rel in split_image_paths(image_paths):
        full = root / rel
        if not full.is_file():
            continue
        data = full.read_bytes()
        loaded.append(
            LoadedImage(
                image_id=image_id_from_path(rel),
                rel_path=rel,
                mime_type=_mime_for(rel),
                data_b64=base64.b64encode(data).decode("ascii"),
            )
        )
    return loaded
