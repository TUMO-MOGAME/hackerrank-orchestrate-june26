"""OpenAI GPT vision adapter.

Uses the OpenAI SDK with image_url(base64 data URI) content parts and JSON-schema
structured outputs to constrain the 10 generated fields. Reads OPENAI_API_KEY from env.

NOTE: structure only — real SDK calls are stubbed (build step 2).
"""

from __future__ import annotations

from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage
from claimreview.providers.base import AdjudicationResult, VisionProvider


class OpenAIProvider(VisionProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        # TODO: init OpenAI client; default to a current multimodal model id.
        self.model = model

    def adjudicate(
        self,
        system_prompt: str,
        context: ClaimContext,
        images: list[LoadedImage],
    ) -> AdjudicationResult:
        raise NotImplementedError
