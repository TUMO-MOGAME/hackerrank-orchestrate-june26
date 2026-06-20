// Supabase client — created only when env vars are present. When absent, the app falls
// back to a local "demo mode" (see lib/auth.tsx) so the UI is fully runnable without keys.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabaseEnabled = Boolean(url && anon);

export const supabase: SupabaseClient | null = supabaseEnabled
  ? createClient(url as string, anon as string)
  : null;
