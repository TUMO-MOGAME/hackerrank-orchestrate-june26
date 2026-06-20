// Web-configured ClaimReviewClient instance.
import { ClaimReviewClient } from "@claimreview/shared";

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = new ClaimReviewClient(baseUrl);
