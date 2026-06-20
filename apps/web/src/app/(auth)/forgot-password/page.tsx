"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthShell } from "../../../components/AuthShell";
import { useAuth } from "../../../lib/auth";

export default function ForgotPasswordPage() {
  const { resetPassword, demo } = useAuth();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await resetPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send the reset link.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We&apos;ll email you a secure link to set a new one."
      footer={
        <span className="muted">
          Remembered it?{" "}
          <Link className="link" href="/signin">
            Back to sign in
          </Link>
        </span>
      }
    >
      {sent ? (
        <div className="alert alert--ok" role="status">
          If an account exists for <strong>{email}</strong>, a reset link is on its way.
          {demo && " (Demo mode: no email is actually sent.)"}
        </div>
      ) : (
        <form className="form-stack" onSubmit={submit}>
          {error && <div className="alert alert--error">{error}</div>}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <button className="btn btn--ember btn--block btn--lg" type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
