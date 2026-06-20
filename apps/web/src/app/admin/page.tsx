"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "../../components/Logo";
import { NotificationBell } from "../../components/NotificationBell";
import { useAuth } from "../../lib/auth";
import { type Claim, verdictLabel } from "../../lib/claims";
import { loadClaims } from "../../lib/store";

const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  needs_more_evidence: "Needs more evidence",
  decided: "Decided",
};

export default function AdminPage() {
  const { user, role, loading, signOut } = useAuth();
  const router = useRouter();
  const [claims, setClaims] = useState<Claim[]>([]);

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/signin");
    else if (role !== "admin") router.replace("/chat");
    else loadClaims().then(setClaims);
  }, [loading, user, role, router]);

  if (loading || !user || role !== "admin") {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="muted mono">Loading…</span>
      </div>
    );
  }

  const flaggedCount = claims.filter((c) => c.images.some((i) => i.aiGenerated)).length;

  return (
    <>
      <header className="app-bar">
        <div className="row" style={{ gap: 14 }}>
          <Link href="/">
            <Logo size={26} />
          </Link>
          <span className="chip" style={{ color: "var(--ember-deep)" }}>
            <span className="dot" /> review console
          </span>
        </div>
        <div className="row" style={{ gap: 12 }}>
          <NotificationBell email={user.email} isAdmin={true} />
          <span className="chip">{user.email}</span>
          <button className="btn btn--ghost" onClick={() => signOut().then(() => router.push("/"))}>
            Sign out
          </button>
        </div>
      </header>

      <main className="container" style={{ paddingTop: 36, paddingBottom: 64 }}>
        <p className="eyebrow">Adjudication queue</p>
        <div className="spread" style={{ alignItems: "flex-end", marginTop: 8 }}>
          <h2 style={{ fontSize: "2rem" }}>Claims for review</h2>
          <div className="row" style={{ gap: 10 }}>
            <span className="chip">{claims.length} total</span>
            <span className="chip" style={{ color: flaggedCount ? "var(--risk)" : "var(--ink-faint)" }}>
              <span className="dot" /> {flaggedCount} with AI-flagged evidence
            </span>
          </div>
        </div>

        {claims.length === 0 ? (
          <div className="panel" style={{ marginTop: 24, textAlign: "center", padding: 56 }}>
            <p className="muted">
              No claims yet. File one from the{" "}
              <Link className="link" href="/chat">
                user chat
              </Link>{" "}
              — it&apos;ll appear here for review.
            </p>
          </div>
        ) : (
          <div className="table" style={{ marginTop: 24 }}>
            <div className="trow trow--head">
              <span>Claim</span>
              <span>Object</span>
              <span>Status</span>
              <span>Verdict</span>
              <span>Evidence</span>
              <span>Filed by</span>
            </div>
            {claims.map((c) => {
              const flagged = c.images.filter((i) => i.aiGenerated).length;
              return (
                <Link key={c.id} href={`/admin/${c.id}`} className="trow">
                  <span className="mono">{c.id}</span>
                  <span style={{ textTransform: "capitalize" }}>{c.claimObject}</span>
                  <span>
                    <span className="chip">{STATUS_LABEL[c.status]}</span>
                  </span>
                  <span className={`v-${c.decision?.claim_status ?? "needs_info"}`}>
                    {verdictLabel(c.decision?.claim_status)}
                  </span>
                  <span className="mono" style={{ fontSize: "0.82rem" }}>
                    {c.images.length} img
                    {flagged > 0 && (
                      <span style={{ color: "var(--contradicted)" }}> · {flagged} AI</span>
                    )}
                  </span>
                  <span className="muted" style={{ fontSize: "0.82rem" }}>
                    {c.userEmail}
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
