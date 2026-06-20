// Mobile-configured ClaimReviewClient instance.
import Constants from "expo-constants";
import { ClaimReviewClient } from "@claimreview/shared";

const baseUrl =
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "http://localhost:8000";

export const api = new ClaimReviewClient(baseUrl);
