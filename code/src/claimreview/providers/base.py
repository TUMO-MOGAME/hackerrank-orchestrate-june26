"""Provider abstraction so the same core runs against any best-in-class vision model.

A VisionProvider takes an assembled prompt + a set of inline images and returns a
validated structured decision (the 10 generated fields). Concrete adapters live in
this package (anthropic_provider, gemini_provider, openai_provider). Tests use a
FakeProvider returning canned JSON so unit tests never hit a real API.

NOTE: structure only — concrete calls are stubbed (build step 2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from claimreview.context.assembler import ClaimContext
from claimreview.io.images import LoadedImage


@dataclass
class AdjudicationResult:
    """The 10 generated fields plus token accounting for the operational report."""

    fields: dict                       # the 10 generated output columns
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)  # raw provider response (for debugging)


class VisionProvider(ABC):
    """Interface every model adapter implements."""

    name: str = "base"

    @abstractmethod
    def adjudicate(
        self,
        system_prompt: str,
        context: ClaimContext,
        images: list[LoadedImage],
    ) -> AdjudicationResult:
        """Call the model with text+images, enforce structured output, return result."""
        raise NotImplementedError
