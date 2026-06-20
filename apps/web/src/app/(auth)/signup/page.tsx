"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell } from "../../../components/AuthShell";
import { GoogleButton } from "../../../components/GoogleButton";
import { useAuth } from "../../../lib/auth";

export default function SignUpPage() {
  const { signUp, signInWithGoogle, demo } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signUp(name, email, password);
      if (demo) router.push("/dashboard");
      else setNotice("Check your inbox to confirm your email, then sign in.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create your account.");
    } finally {
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
      title="Create your account"
      subtitle="Start adjudicating claims in minutes."
      footer={
        <span className="muted">
          Already have an account?{" "}
          <Link className="link" href="/signin">
            Sign in
          </Link>
        </span>
      }
    >
      <GoogleButton onClick={google} label="Sign up with Google" disabled={busy} />
      <div className="or-rule">or with email</div>

      <form className="form-stack" onSubmit={submit}>
        {error && <div className="alert alert--error">{error}</div>}
        {notice && <div className="alert alert--ok">{notice}</div>}
        <div className="field">
          <label htmlFor="name">Full name</label>
          <input
            id="name"
            className="input"
            placeholder="Avery Stone"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
          />
        </div>
        <div className="field">
          <label htmlFor="email">Work email</label>
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
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            placeholder="At least 6 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        <button className="btn btn--ember btn--block btn--lg" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="muted" style={{ fontSize: "0.78rem", textAlign: "center" }}>
          By continuing you agree to our Terms & Privacy Policy.
        </p>
      </form>

      {demo && <p className="demo-flag">demo mode · account is stored locally in your browser</p>}
    </AuthShell>
  );
}
