"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell } from "../../../components/AuthShell";
import { supabase, supabaseEnabled } from "../../../lib/supabase";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) return setError("Use at least 6 characters.");
    if (password !== confirm) return setError("Passwords don&apos;t match.");
    setBusy(true);
    try {
      if (supabaseEnabled && supabase) {
        const { error: err } = await supabase.auth.updateUser({ password });
        if (err) throw new Error(err.message);
      }
      setDone(true);
      setTimeout(() => router.push("/signin"), 1600);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update your password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Set a new password"
      subtitle="Choose a strong password you don&apos;t use elsewhere."
      footer={
        <Link className="link" href="/signin">
          Back to sign in
        </Link>
      }
    >
      {done ? (
        <div className="alert alert--ok" role="status">
          Password updated. Redirecting you to sign in…
        </div>
      ) : (
        <form className="form-stack" onSubmit={submit}>
          {error && <div className="alert alert--error">{error}</div>}
          <div className="field">
            <label htmlFor="password">New password</label>
            <input
              id="password"
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="confirm">Confirm password</label>
            <input
              id="confirm"
              className="input"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <button className="btn btn--ember btn--block btn--lg" type="submit" disabled={busy}>
            {busy ? "Updating…" : "Update password"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
