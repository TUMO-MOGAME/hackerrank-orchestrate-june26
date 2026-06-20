"""Image authenticity / AI-generation detection.

A pluggable layer that asks, per image, "is this a real photo, or AI-generated /
manipulated?" Its verdicts feed the GRADED output: the `non_original_image` /
`possible_manipulation` risk flags, `valid_image`, and (conservatively) `claim_status`.

Design mirrors `providers/`: one `AuthenticityDetector` interface with swappable
backends (Gemini today; an offline model can be added behind the same interface for
ensembling). Detection is per-IMAGE and memoizable by content hash, so the same image
shared across claims is assessed once.
"""
