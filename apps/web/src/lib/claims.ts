// Demo claims store (localStorage). The user chatbot writes claims here; the admin console
// reads them. Abstracted so it can later be swapped for Supabase / the Python API without
// touching the UI. Single-browser demo: submit on the user side, view on the admin side.

import type { ClaimDecision, ClaimObject } from "@claimreview/shared";

export type ClaimStatusFlow = "submitted" | "under_review" | "needs_more_evidence" | "decided";

export interface EvidenceImage {
  id: string; // img_1, img_2, ...
  name: string;
  dataUrl: string; // base64 preview/payload
  aiGenerated: boolean;
  signals: string[];
}

export interface ChatMessage {
  role: "bot" | "user";
  text: string;
  at: number;
}

export interface ProcessLogEntry {
  at: number;
  kind: "intake" | "detection" | "submit" | "decision" | "system";
  message: string;
}

export interface Claim {
  id: string;
  createdAt: number;
  status: ClaimStatusFlow;
  // who
  userEmail: string;
  // what
  claimObject: ClaimObject;
  part?: string;
  conversation: string; // pipe-joined transcript sent to the agent
  transcript: ChatMessage[]; // full chat for the audit view
  images: EvidenceImage[];
  // outcomes
  decision?: ClaimDecision;
  confidence?: number; // 0..1 heuristic confidence in the decision
  reviewerNote?: string; // set when a reviewer requests more evidence
  log: ProcessLogEntry[];
}

export interface Notification {
  id: string;
  forEmail: string; // recipient (user email, or "admin" for the queue)
  claimId: string;
  message: string;
  at: number;
  read: boolean;
}

const KEY = "claimlens.claims.v1";

function read(): Claim[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as Claim[];
  } catch {
    return [];
  }
}

function write(claims: Claim[]) {
  if (typeof window === "undefined") return;
  // localStorage is ~5MB; base64 evidence images can fill it. On quota errors, evict the
  // oldest claims and retry; as a last resort, drop image payloads so metadata still saves.
  let list = [...claims].sort((a, b) => b.createdAt - a.createdAt);
  for (let i = 0; i < 8; i++) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(list));
      return;
    } catch {
      if (list.length > 1) {
        list = list.slice(0, list.length - 1); // drop the oldest claim
      } else {
        list = list.map((c) => ({ ...c, images: c.images.map((im) => ({ ...im, dataUrl: "" })) }));
        try {
          window.localStorage.setItem(KEY, JSON.stringify(list));
        } catch {
          /* give up silently — the decision is already shown in-session */
        }
        return;
      }
    }
  }
}

export function listClaims(): Claim[] {
  return read().sort((a, b) => b.createdAt - a.createdAt);
}

export function getClaim(id: string): Claim | undefined {
  return read().find((c) => c.id === id);
}

export function saveClaim(claim: Claim) {
  const all = read();
  const i = all.findIndex((c) => c.id === claim.id);
  if (i >= 0) all[i] = claim;
  else all.push(claim);
  write(all);
}

export function newClaimId(): string {
  return "CLM-" + Math.random().toString(36).slice(2, 7).toUpperCase();
}

/** Human-readable label for a claim_status verdict (handles missing/unknown gracefully). */
const VERDICT_LABELS: Record<string, string> = {
  supported: "Supported",
  contradicted: "Contradicted",
  not_enough_information: "Needs more info",
};
export function verdictLabel(status?: string | null): string {
  if (!status) return "—";
  return VERDICT_LABELS[status] ?? status.replace(/_/g, " ");
}

/** Decision booleans arrive as real booleans (demo engine) or "true"/"false" strings (live API). */
export function isTrueish(v: unknown): boolean {
  return v === true || String(v).trim().toLowerCase() === "true";
}

/** Real evidence first, AI-flagged evidence appended — per the product rule. */
export function orderedEvidence(images: EvidenceImage[]): EvidenceImage[] {
  return [...images].sort((a, b) => Number(a.aiGenerated) - Number(b.aiGenerated));
}

export function evidenceStrength(images: EvidenceImage[]): {
  real: number;
  flagged: number;
  label: string;
} {
  const real = images.filter((i) => !i.aiGenerated).length;
  const flagged = images.filter((i) => i.aiGenerated).length;
  const label = real >= 2 ? "Strong" : real === 1 ? "Adequate" : flagged > 0 ? "At risk" : "None";
  return { real, flagged, label };
}

/** Heuristic decision-confidence for the demo: more genuine evidence + fewer flags = higher. */
export function confidenceFor(claim: Claim): number {
  const { real, flagged } = evidenceStrength(claim.images);
  let c = 0.4 + Math.min(real, 3) * 0.18 - flagged * 0.12;
  if (claim.decision?.claim_status === "not_enough_information") c -= 0.15;
  return Math.max(0.05, Math.min(0.97, Number(c.toFixed(2))));
}

// --- notifications (demo, localStorage) -------------------------------------
const NOTE_KEY = "claimlens.notifications.v1";

function readNotes(): Notification[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(NOTE_KEY) ?? "[]") as Notification[];
  } catch {
    return [];
  }
}
function writeNotes(n: Notification[]) {
  if (typeof window !== "undefined") window.localStorage.setItem(NOTE_KEY, JSON.stringify(n));
}

export function notify(forEmail: string, claimId: string, message: string) {
  const all = readNotes();
  all.push({
    id: "N" + Math.random().toString(36).slice(2, 8),
    forEmail,
    claimId,
    message,
    at: Date.now(),
    read: false,
  });
  writeNotes(all);
}

export function notificationsFor(email: string, isAdmin: boolean): Notification[] {
  return readNotes()
    .filter((n) => (isAdmin ? n.forEmail === "admin" : n.forEmail === email))
    .sort((a, b) => b.at - a.at);
}

export function markNotificationsRead(email: string, isAdmin: boolean) {
  const all = readNotes();
  for (const n of all) if (isAdmin ? n.forEmail === "admin" : n.forEmail === email) n.read = true;
  writeNotes(all);
}
