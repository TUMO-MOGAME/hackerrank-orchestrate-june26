"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Logo } from "../../components/Logo";
import { NotificationBell } from "../../components/NotificationBell";
import { useAuth } from "../../lib/auth";
import { type Claim, type EvidenceImage, notify } from "../../lib/claims";
import { detectAiImage } from "../../lib/detect";
import { downscaleDataUrl } from "../../lib/imageutil";
import { loadClaim, loadClaims, persistClaim } from "../../lib/store";

const LABEL: Record<string, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  needs_more_evidence: "Action needed",
  decided: "Decided",
};

export default function MyClaimsPage() {
  const { user, role, loading, signOut } = useAuth();
  const router = useRouter();
  const [claims, setClaims] = useState<Claim[]>([]);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/signin");
    else if (role === "admin") router.replace("/admin");
    else refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user, role]);

  async function refresh() {
    const all = await loadClaims();
    setClaims(all.filter((c) => c.userEmail === user?.email));
  }

  async function addEvidence(claimId: string, list: FileList | null) {
    if (!list) return;
    const claim = await loadClaim(claimId);
    if (!claim) return;
    let n = claim.images.length;
    const added: EvidenceImage[] = [];
    for (const file of Array.from(list).slice(0, 6)) {
      const dataUrl = await new Promise<string>((res) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result));
        r.readAsDataURL(file);
      });
      const det = await detectAiImage(file);
      n += 1;
      const thumb = await downscaleDataUrl(dataUrl);
      added.push({ id: `img_${n}`, name: file.name, dataUrl: thumb, aiGenerated: det.aiGenerated, signals: det.signals });
    }
    const updated: Claim = {
      ...claim,
      images: [...claim.images, ...added],
      status: "under_review",
      log: [
        ...claim.log,
        { at: Date.now(), kind: "submit", message: `Claimant added ${added.length} more photo(s)` },
        ...added
          .filter((a) => a.aiGenerated)
          .map((a) => ({ at: Date.now(), kind: "detection" as const, message: `${a.id} flagged AI-generated` })),
      ],
    };
    await persistClaim(updated);
    notify("admin", claim.id, `Claimant added ${added.length} photo(s) to ${claim.id}`);
    refresh();
  }

  if (loading || !user || role === "admin") {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="muted mono">Loading…</span>
      </div>
    );
  }

  return (
    <>
      <header className="app-bar">
        <Link href="/">
          <Logo size={26} />
        </Link>
        <div className="row" style={{ gap: 14 }}>
          <Link className="btn btn--ember" href="/chat">
            + New claim
          </Link>
          <NotificationBell email={user.email} isAdmin={false} />
          <span className="chip">{user.email}</span>
          <button className="btn btn--ghost" onClick={() => signOut().then(() => router.push("/"))}>
            Sign out
          </button>
        </div>
      </header>

      <main className="container" style={{ paddingTop: 36, paddingBottom: 64, maxWidth: 760 }}>
        <p className="eyebrow">Your claims</p>
        <h2 style={{ fontSize: "2rem", marginTop: 8 }}>Track your submissions</h2>

        {claims.length === 0 ? (
          <div className="panel" style={{ marginTop: 24, textAlign: "center", padding: 48 }}>
            <p className="muted">
              No claims yet.{" "}
              <Link className="link" href="/chat">
                File your first claim →
              </Link>
            </p>
          </div>
        ) : (
          <div className="stack" style={{ gap: 16, marginTop: 24 }}>
            {claims.map((c) => {
              const flagged = c.images.filter((i) => i.aiGenerated).length;
              const needs = c.status === "needs_more_evidence";
              return (
                <div key={c.id} className="panel" style={needs ? { borderColor: "var(--ember)" } : undefined}>
                  <div className="spread">
                    <div className="row" style={{ gap: 10 }}>
                      <span className="mono" style={{ fontWeight: 700 }}>
                        {c.id}
                      </span>
                      <span className="chip" style={{ textTransform: "capitalize" }}>
                        {c.claimObject}
                      </span>
                    </div>
                    <span
                      className="chip"
                      style={{ color: needs ? "var(--ember-deep)" : "var(--ink-soft)" }}
                    >
                      <span className="dot" /> {LABEL[c.status]}
                    </span>
                  </div>

                  <div className="row" style={{ gap: 14, marginTop: 12, flexWrap: "wrap" }}>
                    <span className="muted mono" style={{ fontSize: "0.8rem" }}>
                      verdict: <span className={`v-${c.decision?.claim_status ?? "needs_info"}`}>{c.decision?.claim_status ?? "—"}</span>
                    </span>
                    <span className="muted mono" style={{ fontSize: "0.8rem" }}>
                      {c.images.length} photo(s){flagged > 0 && ` · ${flagged} AI-flagged`}
                    </span>
                  </div>

                  {needs && (
                    <div style={{ marginTop: 14 }}>
                      <div className="alert" style={{ borderColor: "var(--ember)", color: "var(--ink-soft)" }}>
                        <strong>Reviewer needs more:</strong> {c.reviewerNote}
                      </div>
                      <button
                        className="btn btn--ember"
                        style={{ marginTop: 12 }}
                        onClick={() => fileRefs.current[c.id]?.click()}
                        type="button"
                      >
                        + Add evidence
                      </button>
                      <input
                        ref={(el) => {
                          fileRefs.current[c.id] = el;
                        }}
                        type="file"
                        accept="image/*"
                        multiple
                        hidden
                        onChange={(e) => addEvidence(c.id, e.target.files)}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
