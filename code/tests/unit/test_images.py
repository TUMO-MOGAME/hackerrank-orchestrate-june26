"""Image loading tests against the real dataset images."""

from __future__ import annotations

import base64

import pytest

from claimreview.io.images import (
    image_id_from_path,
    load_images,
    split_image_paths,
)


def test_split_image_paths():
    s = "images/test/case_001/img_1.jpg;images/test/case_001/img_2.jpg"
    assert split_image_paths(s) == [
        "images/test/case_001/img_1.jpg",
        "images/test/case_001/img_2.jpg",
    ]
    assert split_image_paths("") == []


def test_image_id_is_filename_without_extension():
    assert image_id_from_path("images/test/case_001/img_1.jpg") == "img_1"


def test_load_images_encodes_real_files(dataset_dir, has_dataset):
    if not has_dataset:
        pytest.skip("dataset not present")
    paths = "images/test/case_001/img_1.jpg;images/test/case_001/img_2.jpg"
    images = load_images(paths, str(dataset_dir))
    assert [i.image_id for i in images] == ["img_1", "img_2"]
    assert all(i.mime_type == "image/jpeg" for i in images)
    # base64 decodes back to non-empty bytes
    assert all(len(base64.b64decode(i.data_b64)) > 0 for i in images)


def test_load_images_skips_missing(dataset_dir, has_dataset):
    if not has_dataset:
        pytest.skip("dataset not present")
    images = load_images("images/test/case_001/does_not_exist.jpg", str(dataset_dir))
    assert images == []
