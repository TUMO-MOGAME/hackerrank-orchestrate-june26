// Client-side AI-image / manipulation detection — mirrors the Python provenance layer
// (code/src/claimreview/authenticity/provenance.py). Scans the file's bytes for an embedded
// C2PA manifest with the `trainedAlgorithmicMedia` assertion + Google SynthID references.
// PRESENT => strong proof of AI generation; ABSENT => unknown (not proof of "real").

export interface DetectResult {
  aiGenerated: boolean;
  confidence: number; // 0..1
  signals: string[];
}

export async function detectAiImage(file: File): Promise<DetectResult> {
  const buf = new Uint8Array(await file.arrayBuffer());
  // latin1 keeps every byte 1:1 so marker strings survive intact.
  const text = new TextDecoder("latin1").decode(buf);

  const signals: string[] = [];
  const hasAiAssertion = text.includes("trainedAlgorithmicMedia");
  const hasSynthId = text.includes("SynthID");
  const hasC2pa = ["urn:c2pa", "c2pa", "jumbf"].some((m) => text.includes(m));

  if (hasAiAssertion) signals.push("c2pa:trainedAlgorithmicMedia");
  if (hasSynthId) signals.push("synthid-watermark");
  if (hasC2pa && !hasAiAssertion) signals.push("c2pa-manifest");

  const aiGenerated = hasAiAssertion || (hasC2pa && hasSynthId);
  return { aiGenerated, confidence: aiGenerated ? 0.99 : 0, signals };
}
