"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell } from "../../../components/AuthShell";
import { GoogleButton } from "../../../components/GoogleButton";
import { useAuth } from "../../../lib/auth";

export default function SignInPage() {
  const { signIn, signInWithGoogle, demo } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  async function quickDemo(kind: "user" | "admin") {
    setError(null);
    setBusy(true);
    try {
      // 'reviewer' in the email grants the admin role (see roleFor in lib/auth).
      const demoEmail = kind === "admin" ? "reviewer@claimlens.app" : "demo.user@claimlens.app";
      await signIn(demoEmail, "demo-pass");
      router.push(kind === "admin" ? "/admin" : "/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start demo.");
      setBusy(false);
    }
  }

  async function google() {
    setError(null);
    try {
      await signInWithGoogle();
      if (demo) router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed.");
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to review claims and run authenticity checks."
      footer={
        <span className="muted">
          New here?{" "}
          <Link className="link" href="/signup">
            Create an account
          </Link>
        </span>
      }
    >
      {demo && (
        <div className="stack" style={{ gap: 8, marginBottom: 16 }}>
          <p className="muted" style={{ fontSize: "0.78rem", textAlign: "center", margin: 0 }}>
            ⚡ Fast demo — one click, no typing
          </p>
          <div className="row" style={{ gap: 8 }}>
            <button
              className="btn btn--ember"
              style={{ flex: 1 }}
              type="button"
              onClick={() => quickDemo("user")}
              disabled={busy}
            >
              👤 Enter as user
            </button>
            <button
              className="btn btn--ghost"
              style={{ flex: 1 }}
              type="button"
              onClick={() => quickDemo("admin")}
              disabled={busy}
            >
              🛡️ Enter as reviewer
            </button>
          </div>
          <div className="or-rule">or sign in normally</div>
        </div>
      )}

      <GoogleButton onClick={google} label="Sign in with Google" disabled={busy} />
      <div className="or-rule">or with email</div>

      <form className="form-stack" onSubmit={submit}>
        {error && <div className="alert alert--error">{error}</div>}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            className="input"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <div className="spread">
            <label htmlFor="password">Password</label>
            <Link className="link" href="/forgot-password" style={{ fontSize: "0.8rem" }}>
              Forgot?
            </Link>
          </div>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="btn btn--ember btn--block btn--lg" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {demo && (
        <p className="demo-flag">demo mode · any email + password works (no Supabase keys set)</p>
      )}
    </AuthShell>
  );
}
