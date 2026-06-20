import Link from "next/link";
import { Logo } from "../components/Logo";

const FEATURES = [
  {
    k: "01",
    t: "Image-grounded verdicts",
    d: "Every decision is tied to what's visible in the photos — never the customer's words alone. Supported, contradicted, or needs-more-info, with a cited justification.",
  },
  {
    k: "02",
    t: "Deepfake & manipulation check",
    d: "C2PA / SynthID provenance plus a vision pass flag AI-generated or doctored evidence before it ever reaches an adjudicator.",
  },
  {
    k: "03",
    t: "Evidence-standard scoring",
    d: "Checks each claim's photos against the minimum-evidence rules per object and part, and routes thin evidence to manual review.",
  },
  {
    k: "04",
    t: "Risk-aware, audit-ready",
    d: "Surfaces history risk, image-quality issues, and mismatches as structured flags — with a transcript you can defend.",
  },
];

const STEPS = [
  { t: "Submit", d: "Upload the claim photos and paste the conversation. Pick the object: car, laptop, or package." },
  { t: "Adjudicate", d: "The agent reads the damage, verifies authenticity, and scores the evidence standard." },
  { t: "Decide", d: "Get a grounded verdict with issue type, part, severity, and risk flags — ready to action." },
];

export default function Home() {
  return (
    <>
      <header className="nav container">
        <Logo size={28} />
        <nav className="nav__links">
          <a href="#how">How it works</a>
          <a href="#features">Capabilities</a>
          <Link href="/signin">Sign in</Link>
          <Link href="/signup" className="btn btn--ember">
            Get started
          </Link>
        </nav>
      </header>

      <main className="container">
        {/* HERO */}
        <section className="hero">
          <div className="hero__copy">
            <p className="eyebrow reveal reveal-1">Multi-modal evidence review</p>
            <h1 className="reveal reveal-2">
              Adjudicate damage claims on <em className="hero__em">evidence</em>, not assertions.
            </h1>
            <p className="lead reveal reveal-3" style={{ marginTop: 22, maxWidth: 540 }}>
              ClaimLens reads a claim&apos;s photos, conversation, and history — returns a grounded
              verdict, and flags AI-generated images before they cost you a payout.
            </p>
            <div className="hero__cta reveal reveal-4">
              <Link href="/signup" className="btn btn--ember btn--lg">
                Start adjudicating →
              </Link>
              <Link href="/dashboard" className="btn btn--ghost btn--lg">
                Open the console
              </Link>
            </div>
            <div className="hero__meta reveal reveal-4">
              <span className="mono">car · laptop · package</span>
              <span className="hero__sep" />
              <span className="mono">image-grounded · auditable</span>
            </div>
          </div>

          {/* Verdict preview card */}
          <aside className="hero__card card reveal reveal-3">
            <div className="spread" style={{ marginBottom: 14 }}>
              <span className="chip">
                <span className="dot v-supported" /> case_001 · car
              </span>
              <span className="mono muted" style={{ fontSize: "0.72rem" }}>
                img_1
              </span>
            </div>
            <div className="verdict">
              <span className="verdict__label v-supported">Supported</span>
              <p className="verdict__just">
                The rear bumper is clearly visible with a dent consistent with the customer&apos;s
                account; history adds no risk.
              </p>
            </div>
            <div className="hairline" style={{ margin: "16px 0" }} />
            <div className="hero__grid">
              <Field label="Issue" value="dent" />
              <Field label="Part" value="rear_bumper" />
              <Field label="Severity" value="medium" />
              <Field label="Authenticity" value="genuine" ok />
            </div>
          </aside>
        </section>

        {/* HOW */}
        <section id="how" className="section">
          <p className="eyebrow">How it works</p>
          <h2 style={{ marginTop: 10, maxWidth: 620 }}>Three steps from a messy claim to a defensible decision.</h2>
          <div className="steps">
            {STEPS.map((s, i) => (
              <div key={s.t} className="step">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="step__img" src={`/brand/step-${i + 1}.png`} alt="" />
                <span className="step__n mono">0{i + 1}</span>
                <h3 style={{ marginTop: 10 }}>{s.t}</h3>
                <p className="muted" style={{ marginTop: 8 }}>
                  {s.d}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* FEATURES */}
        <section id="features" className="section">
          <p className="eyebrow">Capabilities</p>
          <h2 style={{ marginTop: 10, maxWidth: 620 }}>Built for accuracy you can put in front of an auditor.</h2>
          <div className="features">
            {FEATURES.map((f) => (
              <article key={f.k} className="feature">
                <span className="feature__k mono">{f.k}</span>
                <h3>{f.t}</h3>
                <p className="muted">{f.d}</p>
              </article>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="cta card">
          <h2 style={{ maxWidth: 560 }}>Put every claim under the same honest lens.</h2>
          <p className="lead" style={{ marginTop: 14, marginBottom: 26 }}>
            Create an account and adjudicate your first claim in under a minute.
          </p>
          <Link href="/signup" className="btn btn--ember btn--lg">
            Get started free →
          </Link>
        </section>
      </main>

      <footer className="footer container">
        <Logo size={22} />
        <span className="muted mono" style={{ fontSize: "0.74rem" }}>
          © {new Date().getFullYear()} ClaimLens · Multi-modal evidence review
        </span>
      </footer>
    </>
  );
}

function Field({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: "0.72rem", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div className="mono" style={{ marginTop: 3, color: ok ? "var(--supported)" : "var(--ink)" }}>
        {value}
      </div>
    </div>
  );
}
