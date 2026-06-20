import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "./Logo";

// Split-screen auth layout: an atmospheric branded panel + the form card.
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="auth-grid">
      {/* Branded panel */}
      <aside className="auth-panel">
        <div className="auth-panel__top">
          <Link href="/" aria-label="ClaimLens home">
            <Logo size={30} />
          </Link>
        </div>
        <div className="auth-panel__body">
          <p className="eyebrow" style={{ color: "var(--ember-soft)" }}>
            Evidence-grounded adjudication
          </p>
          <h2 style={{ color: "var(--paper)", maxWidth: 440, marginTop: 14 }}>
            The image is the truth. We just make it provable.
          </h2>
          <p style={{ color: "rgba(246,242,233,0.72)", marginTop: 18, maxWidth: 430 }}>
            Submit a claim&apos;s photos and conversation — ClaimLens reads the damage, checks the
            evidence standard, flags AI-generated images, and returns a grounded verdict.
          </p>
          <div className="auth-panel__chips">
            <span className="chip auth-chip">
              <span className="dot" style={{ color: "var(--ember-soft)" }} /> deepfake / C2PA check
            </span>
            <span className="chip auth-chip">
              <span className="dot" style={{ color: "#9ecbb0" }} /> image-grounded verdicts
            </span>
          </div>
        </div>
        <div className="auth-panel__foot mono">SOC-ready · audit trail · multi-modal</div>
      </aside>

      {/* Form side */}
      <main className="auth-main">
        <div className="auth-card reveal reveal-1">
          <header style={{ marginBottom: 22 }}>
            <h1 style={{ fontSize: "2.1rem", letterSpacing: "-0.02em" }}>{title}</h1>
            {subtitle && (
              <p className="muted" style={{ marginTop: 8 }}>
                {subtitle}
              </p>
            )}
          </header>
          {children}
          {footer && <div style={{ marginTop: 22, textAlign: "center" }}>{footer}</div>}
        </div>
      </main>
    </div>
  );
}
