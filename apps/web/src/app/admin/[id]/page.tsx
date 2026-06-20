"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "../../../components/Logo";
import { useAuth } from "../../../lib/auth";
import { type Claim, type ClaimStatusFlow, confidenceFor, isTrueish, notify, verdictLabel } from "../../../lib/claims";
import { loadClaim, persistClaim } from "../../../lib/store";

const NEXT: Record<ClaimStatusFlow, ClaimStatusFlow | null> = {
  submitted: "under_review",
  under_review: "decided",
  needs_more_evidence: "under_review",
  decided: null,
};
const STATUS_LABEL: Record<ClaimStatusFlow, string> = {
  submitted: "Submitted",
  under_review: "Under review",
  needs_more_evidence: "Needs more evidence",
  decided: "Decided",
};

export default function ClaimDetail() {
  const { user, role, loading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const id = String(params.id);
  const [claim, setClaim] = useState<Claim | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) return router.replace("/signin");
    if (role !== "admin") return router.replace("/chat");
    loadClaim(id).then((c) => setClaim(c));
  }, [loading, user, role, id, router]);

  async function advance() {
    if (!claim) return;
    const next = NEXT[claim.status];
    if (!next) return;
    const updated: Claim = {
      ...claim,
      status: next,
      log: [
        ...claim.log,
        { at: Date.now(), kind: "system", message: `Status → ${STATUS_LABEL[next]} by ${user?.email}` },
      ],
    };
    await persistClaim(updated);
    setClaim(updated);
    if (next === "decided") {
      notify(
        claim.userEmail,
        claim.id,
        `Your claim ${claim.id} was decided: ${claim.decision?.claim_status ?? "see details"}.`,
      );
    }
  }

  async function requestMore() {
    if (!claim) return;
    const note =
      window.prompt(
        "Message to the claimant (what extra evidence is needed)?",
        "Please upload at least one additional genuine photo clearly showing the damaged part.",
      ) ?? "";
    if (!note.trim()) return;
    const updated: Claim = {
      ...claim,
      status: "needs_more_evidence",
      reviewerNote: note,
      log: [
        ...claim.log,
        { at: Date.now(), kind: "system", message: `Requested more evidence: "${note}"` },
      ],
    };
    await persistClaim(updated);
    setClaim(updated);
    notify(claim.userEmail, claim.id, `Reviewer requested more evidence on ${claim.id}: ${note}`);
  }

  if (loading || !user || role !== "admin") {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="muted mono">Loading…</span>
      </div>
    );
  }
  if (!claim) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <div className="stack" style={{ gap: 12, alignItems: "center" }}>
          <span className="muted">Claim not found.</span>
          <Link className="link" href="/admin">
            ← Back to queue
          </Link>
        </div>
      </div>
    );
  }

  const d = claim.decision;
  const verdictClass = `v-${d?.claim_status ?? "needs_info"}`;
  const flags = (d?.risk_flags ?? "").split(";").map((s) => s.trim()).filter((s) => s && s !== "none");
  const realImgs = claim.images.filter((i) => !i.aiGenerated);
  const aiImgs = claim.images.filter((i) => i.aiGenerated);

  return (
    <>
      <header className="app-bar">
        <Link href="/admin" className="row" style={{ gap: 12 }}>
          <Logo size={24} />
          <span className="link">← Queue</span>
        </Link>
        <div className="row" style={{ gap: 10 }}>
          <span className="chip">{STATUS_LABEL[claim.status]}</span>
          {claim.status !== "decided" && claim.status !== "needs_more_evidence" && (
            <button className="btn btn--ghost" onClick={requestMore}>
              Request more evidence
            </button>
          )}
          {NEXT[claim.status] && (
            <button className="btn btn--ember" onClick={advance}>
              Mark {STATUS_LABEL[NEXT[claim.status] as ClaimStatusFlow]} →
            </button>
          )}
        </div>
      </header>

      <main className="container detail" style={{ paddingTop: 32, paddingBottom: 72 }}>
        {/* main column */}
        <div className="stack" style={{ gap: 22 }}>
          <div>
            <p className="eyebrow">{claim.id} · filed by {claim.userEmail}</p>
            <div className="spread" style={{ marginTop: 8 }}>
              <h2 style={{ fontSize: "2rem", textTransform: "capitalize" }}>
                {claim.claimObject} · {claim.part || "—"}
              </h2>
            </div>
          </div>

          {/* verdict */}
          <div className="panel">
            <div className="spread">
              <span className={`verdict__label ${verdictClass}`} style={{ fontSize: "1.7rem" }}>
                {verdictLabel(d?.claim_status)}
              </span>
              <div className="row" style={{ gap: 8 }}>
                <span className="chip mono">conf {Math.round((claim.confidence ?? confidenceFor(claim)) * 100)}%</span>
                <span
                  className="chip"
                  style={{ color: aiImgs.length ? "var(--contradicted)" : "var(--supported)" }}
                >
                  <span className="dot" /> {aiImgs.length ? "authenticity: flagged" : "authenticity: clear"}
                </span>
              </div>
            </div>
            <p style={{ color: "var(--ink-soft)", marginTop: 8 }}>{d?.claim_status_justification}</p>
            {claim.reviewerNote && (
              <div className="alert" style={{ marginTop: 14, borderColor: "var(--line-strong)", color: "var(--ink-soft)" }}>
                <strong>Evidence requested:</strong> {claim.reviewerNote}
              </div>
            )}
            <div className="hairline" style={{ margin: "16px 0" }} />
            <div className="decision-grid">
              <Stat label="Issue" value={d?.issue_type ?? "—"} />
              <Stat label="Part" value={d?.object_part ?? "—"} />
              <Stat label="Severity" value={d?.severity ?? "—"} />
              <Stat label="Evidence standard" value={isTrueish(d?.evidence_standard_met) ? "met" : "not met"} />
              <Stat label="Valid image" value={isTrueish(d?.valid_image) ? "yes" : "no"} />
              <Stat label="Supporting" value={d?.supporting_image_ids || "none"} />
            </div>
            {flags.length > 0 && (
              <div className="row" style={{ gap: 8, flexWrap: "wrap", marginTop: 16 }}>
                {flags.map((f) => (
                  <span key={f} className="chip" style={{ color: "var(--risk)" }}>
                    <span className="dot" /> {f}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* evidence — real first, AI-flagged after */}
          <div className="panel">
            <p className="eyebrow">Evidence · genuine first, flagged after</p>
            <div className="thumbs" style={{ justifyContent: "flex-start", marginTop: 12 }}>
              {realImgs.map((im) => (
                <Evidence key={im.id} im={im} />
              ))}
              {aiImgs.length > 0 && <div className="ev-divider">AI-flagged</div>}
              {aiImgs.map((im) => (
                <Evidence key={im.id} im={im} />
              ))}
            </div>
          </div>

          {/* transcript */}
          <div className="panel">
            <p className="eyebrow">Intake transcript</p>
            <div className="stack" style={{ gap: 8, marginTop: 12 }}>
              {claim.transcript.map((m, i) => (
                <div key={i} className={`bubble bubble--${m.role}`} style={{ maxWidth: "90%" }}>
                  {m.text}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* side: process log */}
        <aside>
          <div className="panel" style={{ position: "sticky", top: 90 }}>
            <p className="eyebrow">Process log · audit trail</p>
            <ol className="timeline">
              {claim.log.map((e, i) => (
                <li key={i} className={`tl tl--${e.kind}`}>
                  <span className="tl__dot" />
                  <div>
                    <div style={{ fontSize: "0.88rem" }}>{e.message}</div>
                    <div className="muted mono" style={{ fontSize: "0.68rem" }}>
                      {e.kind}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="muted" style={{ fontSize: "0.72rem" }}>
        {label}
      </div>
      <div className="mono" style={{ marginTop: 3 }}>
        {value}
      </div>
    </div>
  );
}

function Evidence({ im }: { im: { id: string; name: string; dataUrl: string; aiGenerated: boolean; signals: string[] } }) {
  return (
    <div className="ev" title={im.signals.join(", ")}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={im.dataUrl} alt={im.name} className="thumb" style={{ width: 104, height: 104 }} />
      <span className={`ev__tag ${im.aiGenerated ? "ev__tag--ai" : "ev__tag--ok"}`}>
        {im.aiGenerated ? "AI-flagged" : "genuine"}
      </span>
      <div className="mono muted" style={{ fontSize: "0.66rem", marginTop: 4, textAlign: "center" }}>
        {im.id}
      </div>
    </div>
  );
}
