"""Provider interface, registry, schema-builder, and Anthropic pure-helper tests.

All offline — no real API calls. The Anthropic adapter's network path is not exercised
(no key, no cost); only its pure request-building / parsing helpers are tested.
"""

from __future__ import annotations

import pytest

from claimreview.config import Settings
from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage
from claimreview.providers.anthropic_provider import build_user_content, parse_fields
from claimreview.providers.fake_provider import FakeProvider
from claimreview.providers.registry import get_provider
from claimreview.schema.output_schema import (
    OBJECT_PARTS,
    generated_fields_json_schema,
    validate_row,
)


def _ctx(claim_object: str = "car") -> ClaimContext:
    return ClaimContext(
        user_id="user_001",
        claim_object=claim_object,
        user_claim="rear bumper dent",
        history_text="No prior history on file.",
        evidence_requirements_text="- (general) be visible",
        image_paths="images/test/case_001/img_1.jpg",
    )


def _img(image_id: str = "img_1") -> LoadedImage:
    return LoadedImage(
        image_id=image_id, rel_path=f"{image_id}.jpg", mime_type="image/jpeg", data_b64="QQ=="
    )


@pytest.mark.parametrize("obj", ["car", "laptop", "package"])
def test_fake_provider_returns_schema_valid_fields(obj):
    result = FakeProvider().adjudicate("system", _ctx(obj), [_img()])
    assert validate_row(result.fields, obj) == []


def test_fake_provider_fields_overridable():
    fields = FakeProvider().adjudicate("s", _ctx(), []).fields
    assert fields["claim_status"] == "not_enough_information"


def test_registry_returns_fake_without_key():
    provider = get_provider(Settings(provider="fake"), env={})
    assert provider.name == "fake"


def test_registry_anthropic_requires_key():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_provider(Settings(provider="anthropic"), env={})


def test_json_schema_object_part_enum_matches_object():
    schema = generated_fields_json_schema("laptop")
    assert set(schema["properties"]["object_part"]["enum"]) == OBJECT_PARTS["laptop"]
    assert schema["additionalProperties"] is False
    assert len(schema["required"]) == 10


def test_build_user_content_has_text_then_images():
    content = build_user_content(_ctx(), [_img("img_1"), _img("img_2")])
    assert content[0]["type"] == "text"
    assert "rear bumper dent" in content[0]["text"]
    assert [c["type"] for c in content[1:]] == ["image", "image"]
    assert content[1]["source"]["media_type"] == "image/jpeg"


def test_parse_fields_reads_json():
    assert parse_fields('{"claim_status": "supported"}')["claim_status"] == "supported"
