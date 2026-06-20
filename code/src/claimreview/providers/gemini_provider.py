"""Google Gemini vision adapter (the default "brain").

Uses the google-genai SDK with inline base64 image parts and a constrained JSON
response. Reads GEMINI_API_KEY / GOOGLE_API_KEY from env (resolved by the registry).

Design notes:
  * Default model `gemini-2.5-flash` — strong multimodal/spatial reasoning with a
    generous free tier (~10-15 RPM); a good accuracy/throughput balance for the batch.
    Override via CLAIMREVIEW_MODEL.
  * The response schema types the two booleans as BOOLEAN and EVERY enum-like field as a
    plain STRING (no `enum`). Gemini's structured output can 400 on rich enums, and we
    already enforce the closed vocab downstream in `schema.repair_generated_fields`, so
    the prompt carries the allowed values and repair guarantees validity.
  * `temperature=0` for determinism (AGENTS.md: deterministic where possible).
  * The SDK is imported lazily so the package works without `google-genai` installed when
    a different provider is selected.
"""

from __future__ import annotations

import base64
import json

from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage
from claimreview.providers.base import AdjudicationResult, VisionProvider
from claimreview.schema.output_schema import GENERATED_COLUMNS

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 1024


def build_user_text(context: ClaimContext, images: list[LoadedImage]) -> str:
    """The dynamic per-claim text that precedes the inline images (pure, testable)."""
    return (
        f"CLAIM OBJECT: {context.claim_object}\n\n"
        f"USER CONVERSATION (claim transcript):\n{context.user_claim}\n\n"
        f"USER HISTORY (risk context only — does not override images):\n{context.history_text}\n\n"
        f"MINIMUM EVIDENCE REQUIREMENTS:\n{context.evidence_requirements_text}\n\n"
        f"SUBMITTED IMAGES (IDs): {', '.join(i.image_id for i in images) or 'none'}\n"
        "Adjudicate strictly from the images. Use the allowed vocabulary only."
    )


def parse_fields(text: str) -> dict:
    """Parse the model's JSON response into the generated-fields dict."""
    return json.loads(text or "{}")


def _response_schema():
    """A Gemini response schema: booleans typed, enum-like fields as plain strings."""
    from google.genai import types

    def _str() -> types.Schema:
        return types.Schema(type=types.Type.STRING)

    def _bool() -> types.Schema:
        return types.Schema(type=types.Type.BOOLEAN)

    properties = {col: (_bool() if col in ("evidence_standard_met", "valid_image") else _str())
                  for col in GENERATED_COLUMNS}
    return types.Schema(
        type=types.Type.OBJECT,
        properties=properties,
        required=list(GENERATED_COLUMNS),
        property_ordering=list(GENERATED_COLUMNS),
    )


class GeminiProvider(VisionProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    def adjudicate(
        self,
        system_prompt: str,
        context: ClaimContext,
        images: list[LoadedImage],
    ) -> AdjudicationResult:
        from google.genai import types

        parts = [types.Part.from_text(text=build_user_text(context, images))]
        for img in images:
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(img.data_b64), mime_type=img.mime_type
                )
            )

        response = self._client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                # Disable "thinking": its hidden tokens consume the output budget and truncate
                # the JSON (Unterminated string) on slower/loaded models like gemini-2.5-flash.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=_response_schema(),
            ),
        )

        usage = getattr(response, "usage_metadata", None)
        return AdjudicationResult(
            fields=parse_fields(response.text),
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            raw={"model": self.model},
        )
