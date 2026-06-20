// Thin client for the deployable FastAPI agent endpoint. Used by web AND mobile.

import type { ClaimDecision, ClaimInput } from "./types";

export class ClaimReviewClient {
  constructor(private readonly baseUrl: string) {}

  /** POST /verify-claim — returns the 10 generated decision fields. */
  async verifyClaim(input: ClaimInput): Promise<ClaimDecision> {
    const body: Record<string, unknown> = {
      user_id: input.user_id,
      user_claim: input.user_claim,
      claim_object: input.claim_object,
    };
    if (input.images_base64?.length) {
      body.images = input.images_base64.map((data_b64, i) => ({
        id: input.image_ids?.[i] ?? `img_${i + 1}`,
        mime_type: "image/jpeg",
        data_b64: stripDataUrl(data_b64),
      }));
    } else if (input.image_paths) {
      body.image_paths = input.image_paths;
    }

    const res = await fetch(`${this.baseUrl}/verify-claim`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      throw new Error(`verify-claim failed (${res.status}): ${detail}`);
    }
    return (await res.json()) as ClaimDecision;
  }

  /** GET /health */
  async health(): Promise<{ status: string; provider?: string; model?: string }> {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) throw new Error(`health failed (${res.status})`);
    return res.json();
  }
}

/** Accept either a raw base64 string or a full data URL; return raw base64. */
function stripDataUrl(s: string): string {
  const comma = s.indexOf(",");
  return s.startsWith("data:") && comma !== -1 ? s.slice(comma + 1) : s;
}
