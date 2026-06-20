// Shared domain types — mirror the Python output contract (code/src/claimreview/schema).
// Keep these in lock-step with problem_statement.md allowed values.

export type ClaimObject = "car" | "laptop" | "package";

export type ClaimStatus = "supported" | "contradicted" | "not_enough_information";

export type IssueType =
  | "dent" | "scratch" | "crack" | "glass_shatter" | "broken_part" | "missing_part"
  | "torn_packaging" | "crushed_packaging" | "water_damage" | "stain" | "none" | "unknown";

export type Severity = "none" | "low" | "medium" | "high" | "unknown";

export type RiskFlag =
  | "none" | "blurry_image" | "cropped_or_obstructed" | "low_light_or_glare"
  | "wrong_angle" | "wrong_object" | "wrong_object_part" | "damage_not_visible"
  | "claim_mismatch" | "possible_manipulation" | "non_original_image"
  | "text_instruction_present" | "user_history_risk" | "manual_review_required";

// Input to the /verify-claim endpoint (single claim).
export interface ClaimInput {
  user_id: string;
  user_claim: string;
  claim_object: ClaimObject;
  image_paths?: string;        // semicolon-separated, server-resolved; OR:
  images_base64?: string[];    // inline images for the web/mobile upload flow
  image_ids?: string[];        // optional ids parallel to images_base64, so the agent's
                               // references/supporting_image_ids match what the UI shows
}

// The 10 generated fields returned by the agent.
export interface ClaimDecision {
  evidence_standard_met: boolean;
  evidence_standard_met_reason: string;
  risk_flags: string;          // semicolon-separated RiskFlag values, or "none"
  issue_type: IssueType;
  object_part: string;         // valid for the claim_object (see schema)
  claim_status: ClaimStatus;
  claim_status_justification: string;
  supporting_image_ids: string; // semicolon-separated image IDs, or "none"
  valid_image: boolean;
  severity: Severity;
}
