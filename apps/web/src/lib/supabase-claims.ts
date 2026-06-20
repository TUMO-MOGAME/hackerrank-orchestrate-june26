// Supabase persistence adapter for claims — the production upgrade path from the localStorage
// demo store (lib/claims.ts). Wire it on by: (1) setting NEXT_PUBLIC_SUPABASE_URL + ANON_KEY,
// (2) running the SQL below, (3) swapping the imports in chat/admin/claims pages from
// `./claims` to `./supabase-claims` (the function shapes are async-compatible mirrors).
//
// SQL (run in Supabase SQL editor):
//   create table claims (
//     id text primary key,
//     created_at bigint not null,
//     status text not null,
//     user_email text not null,
//     claim_object text not null,
//     part text,
//     conversation text,
//     transcript jsonb,
//     images jsonb,         -- [{id,name,dataUrl,aiGenerated,signals}]
//     decision jsonb,
//     confidence real,
//     reviewer_note text,
//     log jsonb
//   );
//   alter table claims enable row level security;
//   -- demo policies (tighten for production: users see only their own rows, admins see all):
//   create policy "read" on claims for select using (true);
//   create policy "write" on claims for insert with check (true);
//   create policy "update" on claims for update using (true);

import type { Claim } from "./claims";
import { supabase, supabaseEnabled } from "./supabase";

function toRow(c: Claim) {
  return {
    id: c.id,
    created_at: c.createdAt,
    status: c.status,
    user_email: c.userEmail,
    claim_object: c.claimObject,
    part: c.part ?? null,
    conversation: c.conversation,
    transcript: c.transcript,
    images: c.images,
    decision: c.decision ?? null,
    confidence: c.confidence ?? null,
    reviewer_note: c.reviewerNote ?? null,
    log: c.log,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fromRow(r: any): Claim {
  return {
    id: r.id,
    createdAt: r.created_at,
    status: r.status,
    userEmail: r.user_email,
    claimObject: r.claim_object,
    part: r.part ?? undefined,
    conversation: r.conversation,
    transcript: r.transcript ?? [],
    images: r.images ?? [],
    decision: r.decision ?? undefined,
    confidence: r.confidence ?? undefined,
    reviewerNote: r.reviewer_note ?? undefined,
    log: r.log ?? [],
  };
}

export async function listClaimsRemote(): Promise<Claim[]> {
  if (!supabaseEnabled || !supabase) return [];
  const { data, error } = await supabase.from("claims").select("*").order("created_at", { ascending: false });
  if (error) throw new Error(error.message);
  return (data ?? []).map(fromRow);
}

export async function getClaimRemote(id: string): Promise<Claim | null> {
  if (!supabaseEnabled || !supabase) return null;
  const { data, error } = await supabase.from("claims").select("*").eq("id", id).single();
  if (error) return null;
  return fromRow(data);
}

export async function saveClaimRemote(claim: Claim): Promise<void> {
  if (!supabaseEnabled || !supabase) return;
  const { error } = await supabase.from("claims").upsert(toRow(claim));
  if (error) throw new Error(error.message);
}
