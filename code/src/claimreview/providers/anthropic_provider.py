"""Anthropic Claude vision adapter.

Uses the Anthropic Messages API with base64 image blocks and structured outputs
(`output_config.format` = our JSON schema) to constrain the 10 generated fields.
The system prompt is sent as a cached text block (`cache_control: ephemeral`) so the
stable persona/rules prefix is billed once across the 64+ claims, not per claim.

Reads ANTHROPIC_API_KEY from the env (the SDK default); the user intends to test the
free Anthropic tier. Defaults to `claude-opus-4-8` (override via CLAIMREVIEW_MODEL).
The SDK is imported lazily so the package works without `anthropic` installed when a
different provider is selected.
"""

from __future__ import annotations

import json

from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage
from claimreview.providers.base import AdjudicationResult, VisionProvider
from claimreview.schema.output_schema import generated_fields_json_schema

DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 1024


def build_user_content(context: ClaimContext, images: list[LoadedImage]) -> list[dict]:
    """Build the user message content: the dynamic context text, then interleaved images.

    Pure function (no SDK), so it can be unit-tested without a network call.
    """
    text = (
        f"CLAIM OBJECT: {context.claim_object}\n\n"
        f"USER CONVERSATION (claim transcript):\n{context.user_claim}\n\n"
        f"USER HISTORY (risk context only — does not override images):\n{context.history_text}\n\n"
        f"MINIMUM EVIDENCE REQUIREMENTS:\n{context.evidence_requirements_text}\n\n"
        f"SUBMITTED IMAGES (IDs): {', '.join(i.image_id for i in images) or 'none'}\n"
        "Adjudicate strictly from the images. Use the allowed vocabulary only."
    )
    content: list[dict] = [{"type": "text", "text": text}]
    for img in images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.mime_type,
                    "data": img.data_b64,
                },
            }
        )
    return content


def parse_fields(text: str) -> dict:
    """Parse the model's structured-output text into the generated-fields dict."""
    return json.loads(text)


class AnthropicProvider(VisionProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    def adjudicate(
        self,
        system_prompt: str,
        context: ClaimContext,
        images: list[LoadedImage],
    ) -> AdjudicationResult:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": generated_fields_json_schema(context.claim_object),
                }
            },
            messages=[{"role": "user", "content": build_user_content(context, images)}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "{}")
        return AdjudicationResult(
            fields=parse_fields(text),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw={"model": self.model},
        )
