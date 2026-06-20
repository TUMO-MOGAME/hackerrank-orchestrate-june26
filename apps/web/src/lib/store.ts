// Unified claims store. Uses Supabase (cross-device persistence) when NEXT_PUBLIC_SUPABASE_URL
// + ANON_KEY are set, otherwise the localStorage demo store. Same async API either way, so the
// UI doesn't care which backend is live.

import type { Claim } from "./claims";
import { getClaim as localGet, listClaims as localList, saveClaim as localSave } from "./claims";
import { supabaseEnabled } from "./supabase";
import { getClaimRemote, listClaimsRemote, saveClaimRemote } from "./supabase-claims";

export const persistenceMode = supabaseEnabled ? "supabase" : "local";

export async function loadClaims(): Promise<Claim[]> {
  return supabaseEnabled ? listClaimsRemote() : localList();
}

export async function loadClaim(id: string): Promise<Claim | null> {
  return supabaseEnabled ? getClaimRemote(id) : (localGet(id) ?? null);
}

export async function persistClaim(claim: Claim): Promise<void> {
  if (supabaseEnabled) await saveClaimRemote(claim);
  else localSave(claim);
}
