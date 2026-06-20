"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { ClaimDecision, ClaimObject, IssueType } from "@claimreview/shared";
import { Logo } from "../../components/Logo";
import { NotificationBell } from "../../components/NotificationBell";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import {
  type ChatMessage,
  type Claim,
  type EvidenceImage,
  type ProcessLogEntry,
  confidenceFor,
  evidenceStrength,
  newClaimId,
  notify,
  orderedEvidence,
} from "../../lib/claims";
import { detectAiImage } from "../../lib/detect";
import { downscaleDataUrl } from "../../lib/imageutil";
import { persistClaim, persistenceMode } from "../../lib/store";

type Phase = "collecting" | "awaiting_evidence" | "ready_to_submit";
interface Known {
  object: ClaimObject | null;
  incident: string | null;
  part: string | null;
}

export default function ChatPage() {
  const { user, role, loading, signOut } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !user) router.replace("/signin");
  }, [loading, user, router]);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [known, setKnown] = useState<Known>({ object: null, incident: null, part: null });
  const [phase, setPhase] = useState<Phase>("collecting");
  const [images, setImages] = useState<EvidenceImage[]>([]);
  const [log, setLog] = useState<ProcessLogEntry[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [llmDown, setLlmDown] = useState(false);
  const [claimId, setClaimId] = useState<string | null>(null);
  const [decision, setDecision] = useState<ClaimDecision | null>(null);
  const [decidedBy, setDecidedBy] = useState<"live" | "demo" | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const greeted = useRef(false);

  const pushBot = (t: string) => setMessages((m) => [...m, { role: "bot", text: t, at: Date.now() }]);
  const pushUser = (t: string) => setMessages((m) => [...m, { role: "user", text: t, at: Date.now() }]);
  const note = (kind: ProcessLogEntry["kind"], message: string) =>
    setLog((l) => [...l, { at: Date.now(), kind, message }]);

  useEffect(() => {
    // Guard against React StrictMode double-invoking the mount effect in dev,
    // which would otherwise post the greeting twice.
    if (greeted.current) return;
    greeted.current = true;
    pushBot(
      "Hey there — I'm Lens 👋 I help people file damage claims, but no rush. How are you doing today, and what brings you in?",
    );
    note("intake", "Intake session started");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function callLLM(history: ChatMessage[], imgs: EvidenceImage[]) {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        messages: history.map((m) => ({ role: m.role, text: m.text })),
        imagesUploaded: imgs.length,
        flagged: imgs.filter((i) => i.aiGenerated).length,
        known,
      }),
    });
    if (!res.ok) throw new Error(String(res.status));
    return (await res.json()) as Known & { reply: string; phase: Phase };
  }

  function applyFields(f: { object: ClaimObject | null; incident: string | null; part: string | null; phase: Phase }) {
    setKnown({ object: f.object, incident: f.incident, part: f.part });
    // Trust local signals over the model's phase guess: once we have the full claim,
    // open the evidence uploader; once a photo exists, we're ready to submit. The
    // parallel extraction call sometimes lags behind the conversation, so we never
    // let it pull the flow backwards.
    const haveAll = Boolean(f.object && f.incident && f.part);
    let next: Phase = f.phase;
    if (haveAll && next === "collecting") next = "awaiting_evidence";
    if (images.length > 0 && next === "collecting") next = "awaiting_evidence";
    setPhase((prev) => {
      const rank: Record<Phase, number> = { collecting: 0, awaiting_evidence: 1, ready_to_submit: 2 };
      return rank[next] >= rank[prev] ? next : prev;
    });
    if (f.object) note("intake", `Field update · object=${f.object} part=${f.part ?? "?"}`);
  }

  async function send() {
    const v = text.trim();
    if (!v || busy) return;
    setText("");
    const history = [...messages, { role: "user" as const, text: v, at: Date.now() }];
    setMessages(history);
    setBusy(true);

    const botAt = Date.now() + Math.random();
    let botText = "";
    let started = false;
    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          messages: history.map((m) => ({ role: m.role, text: m.text })),
          imagesUploaded: images.length,
          flagged: images.filter((i) => i.aiGenerated).length,
          known,
        }),
      });
      if (!res.ok || !res.body) throw new Error(String(res.status));
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, nl).trim();
          buf = buf.slice(nl + 1);
          if (!line) continue;
          const evt = JSON.parse(line);
          if (evt.type === "token") {
            botText += evt.text;
            if (!started) {
              started = true;
              setStreaming(true);
              setMessages((m) => [...m, { role: "bot", text: botText, at: botAt }]);
            } else {
              setMessages((m) => m.map((x) => (x.at === botAt ? { ...x, text: botText } : x)));
            }
          } else if (evt.type === "fields") {
            applyFields(evt);
          } else if (evt.type === "error") {
            throw new Error(evt.message);
          }
        }
      }
      if (!botText) throw new Error("empty");
    } catch {
      // fallback to the non-streaming route, then to offline mode
      try {
        const out = await callLLM(history, images);
        applyFields(out);
        if (started) setMessages((m) => m.map((x) => (x.at === botAt ? { ...x, text: out.reply } : x)));
        else pushBot(out.reply);
      } catch {
        setLlmDown(true);
        pushBot(
          "I'm having trouble reaching my assistant service right now — but you can still add your photos below and submit; a reviewer will take it from there.",
        );
        setPhase("awaiting_evidence");
      }
    } finally {
      setBusy(false);
      setStreaming(false);
      // Keep the cursor in the box so the user can keep typing without re-clicking.
      inputRef.current?.focus();
    }
  }

  async function onFiles(list: FileList | null) {
    if (!list) return;
    let n = images.length;
    for (const file of Array.from(list).slice(0, 6)) {
      const dataUrl = await new Promise<string>((res) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result));
        r.readAsDataURL(file);
      });
      const det = await detectAiImage(file);
      n += 1;
      const id = `img_${n}`;
      const img: EvidenceImage = { id, name: file.name, dataUrl, aiGenerated: det.aiGenerated, signals: det.signals };
      setImages((prev) => [...prev, img]);
      pushUser(`📎 Uploaded ${file.name}`);
      if (det.aiGenerated) {
        note("detection", `${id} flagged AI-generated (${det.signals.join(", ")})`);
        pushBot(
          `⚠️ ${id} looks AI-generated or edited (detected ${det.signals.join(", ")}). I'll still file it — clearly marked — but please add a genuine photo so it isn't held for manual review.`,
        );
      } else {
        note("detection", `${id} passed authenticity check (genuine)`);
        pushBot(`✓ ${id} looks like a genuine photo — added to your evidence.`);
      }
    }
  }

  async function submit() {
    if (submitting || claimId) return;
    setSubmitting(true);
    note("submit", "Claim submitted by user");
    pushBot("📋 Filing your claim — inspecting the photos and running authenticity + damage checks. This takes a few seconds…");
    const id = newClaimId();
    const ordered = orderedEvidence(images);
    const object = (known.object ?? "car") as ClaimObject;
    const conversation =
      `Customer: ${known.incident ?? messages.find((m) => m.role === "user")?.text ?? ""}` +
      ` | Agent: Which part is affected? | Customer: ${known.part ?? "unspecified"}` +
      (images.some((i) => i.aiGenerated) ? ` | System: one or more images flagged as AI-generated.` : "");

    // Downscale for the API too: a phone photo can be multi-MB, which dominates upload +
    // tokenization latency. 1280px keeps ample detail for damage; authenticity already ran
    // client-side on the originals (see onFiles), so re-encoding here doesn't lose that signal.
    const apiImages = await Promise.all(ordered.map((i) => downscaleDataUrl(i.dataUrl, 1280, 0.85)));

    let dec: ClaimDecision;
    try {
      dec = await api.verifyClaim({
        user_id: user?.email ?? "web-user",
        user_claim: conversation,
        claim_object: object,
        images_base64: apiImages,
        image_ids: ordered.map((i) => i.id), // keep agent IDs aligned with what the UI shows
      });
      note("decision", "Adjudicated by live agent API");
      setDecidedBy("live");
    } catch {
      dec = demoDecide(object, known.part ?? "", ordered);
      note("decision", "Adjudicated by built-in demo engine (agent API offline)");
      setDecidedBy("demo");
    }
    if (images.some((i) => i.aiGenerated)) {
      const flags = new Set(dec.risk_flags.split(";").map((x) => x.trim()).filter(Boolean));
      flags.delete("none");
      flags.add("non_original_image");
      flags.add("possible_manipulation");
      dec = { ...dec, risk_flags: [...flags].join(";"), valid_image: false };
    }

    // Store small thumbnails (full-res was already sent to the agent above) so the claim fits
    // in localStorage; the admin/claims views only need a preview.
    const storedImages = await Promise.all(
      ordered.map(async (i) => ({ ...i, dataUrl: await downscaleDataUrl(i.dataUrl) })),
    );

    const claim: Claim = {
      id,
      createdAt: Date.now(),
      status: "submitted",
      userEmail: user?.email ?? "web-user",
      claimObject: object,
      part: known.part ?? undefined,
      conversation,
      transcript: [...messages],
      images: storedImages,
      decision: dec,
      log: [...log, { at: Date.now(), kind: "system", message: `Claim ${id} created` }],
    };
    claim.confidence = confidenceFor(claim);
    await persistClaim(claim);
    notify("admin", id, `New claim ${id} (${object}) filed for review`);
    setClaimId(id);
    setDecision(dec);
    setPhase("ready_to_submit");
    setSubmitting(false);
    const flagged = images.filter((i) => i.aiGenerated).length;
    pushBot(
      `✅ Claim ${id} filed for review.` +
        (flagged > 0
          ? ` ${flagged} image(s) were flagged as AI-generated and attached after your genuine evidence — the reviewer is notified.`
          : " Your evidence looks genuine — the reviewer has everything they need."),
    );
  }

  if (loading || !user) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <span className="muted mono">Loading…</span>
      </div>
    );
  }

  const strength = evidenceStrength(images);
  // Safety net: if the assistant has asked for photos in its latest message, show the
  // uploader even if the structured-extraction phase hasn't caught up yet.
  const lastBot = [...messages].reverse().find((m) => m.role === "bot")?.text.toLowerCase() ?? "";
  const botAskedForPhotos = /photo|upload|picture|image/.test(lastBot);
  const showEvidence =
    (phase === "awaiting_evidence" || phase === "ready_to_submit" || llmDown || botAskedForPhotos || images.length > 0) &&
    !claimId;
  const canSubmit = images.length > 0 && !claimId;

  return (
    <>
      <header className="app-bar">
        <Link href="/">
          <Logo size={26} />
        </Link>
        <div className="row" style={{ gap: 12 }}>
          <Link className="btn btn--ghost" href="/claims">
            My claims
          </Link>
          <NotificationBell email={user.email} isAdmin={false} />
          <span className="chip">{user.email}</span>
          <button className="btn btn--ghost" onClick={() => signOut().then(() => router.push("/"))}>
            Sign out
          </button>
        </div>
      </header>

      <main className="chat-wrap container">
        <div className="chat">
          <div className="chat__head">
            <span className="chat__avatar">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/logo-wheel.png"
                alt="Lens"
                style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
              />
            </span>
            <div>
              <div style={{ fontWeight: 700 }}>Lens · Claims assistant</div>
              <div className="muted mono" style={{ fontSize: "0.72rem" }}>
                {claimId ? "claim filed" : submitting ? "analyzing evidence…" : busy ? "typing…" : "powered by Gemini"}
              </div>
            </div>
          </div>

          <div className="chat__scroll" ref={scroller}>
            {messages.map((m, i) => (
              <div key={i} className={`bubble bubble--${m.role}`}>
                {m.text.split("\n").map((line, j) => (
                  <p key={j} style={{ margin: line ? 0 : "4px 0" }}>
                    {line}
                    {streaming && m.role === "bot" && i === messages.length - 1 && j === m.text.split("\n").length - 1 && (
                      <span className="caret" />
                    )}
                  </p>
                ))}
              </div>
            ))}
            {(busy || submitting) && !streaming && (
              <div className="bubble bubble--bot" aria-label="typing">
                <span className="typing">
                  <i /><i /><i />
                </span>
              </div>
            )}
          </div>

          <div className="chat__composer stack" style={{ gap: 12 }}>
            {showEvidence && (
              <div className="stack" style={{ gap: 10 }}>
                {images.length > 0 && (
                  <div className="thumbs" style={{ justifyContent: "flex-start" }}>
                    {images.map((im) => (
                      <div key={im.id} className="ev">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={im.dataUrl} alt={im.name} className="thumb" />
                        <span className={`ev__tag ${im.aiGenerated ? "ev__tag--ai" : "ev__tag--ok"}`}>
                          {im.aiGenerated ? "AI?" : "✓"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="row" style={{ gap: 8, justifyContent: "space-between", flexWrap: "wrap" }}>
                  <button className="btn btn--ghost" onClick={() => fileRef.current?.click()} type="button">
                    + Add photos
                  </button>
                  <span className="chip" style={{ color: strength.flagged ? "var(--risk)" : "var(--supported)" }}>
                    <span className="dot" /> evidence: {strength.label}
                  </span>
                  {canSubmit && (
                    <button className="btn btn--ember" onClick={submit} type="button" disabled={submitting}>
                      {submitting ? "Analyzing evidence…" : "Submit claim →"}
                    </button>
                  )}
                </div>
                <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => onFiles(e.target.files)} />
              </div>
            )}

            {claimId ? (
              <div className="row" style={{ gap: 8 }}>
                <button className="btn btn--ghost" onClick={() => window.location.reload()} type="button">
                  File another
                </button>
                {role === "admin" ? (
                  <Link className="btn btn--ember" href="/admin">
                    View in review console →
                  </Link>
                ) : (
                  <Link className="btn btn--ember" href="/claims">
                    Track my claims →
                  </Link>
                )}
              </div>
            ) : (
              <form
                className="row"
                style={{ gap: 8 }}
                onSubmit={(e) => {
                  e.preventDefault();
                  send();
                }}
              >
                <input
                  ref={inputRef}
                  className="input"
                  placeholder="Type your message…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  autoFocus
                />
                <button className="btn btn--ember" type="submit" disabled={busy || !text.trim()}>
                  Send
                </button>
              </form>
            )}
          </div>
        </div>

        <aside className="chat-rail">
          {decision && <Verdict decision={decision} decidedBy={decidedBy} />}
          <div className="panel">
            <p className="eyebrow">Your claim</p>
            <Rail label="Object" value={known.object ?? "—"} />
            <Rail label="Part" value={known.part ?? "—"} />
            <Rail label="Photos" value={`${images.length} (${strength.real} genuine / ${strength.flagged} flagged)`} />
            <Rail label="Strength" value={strength.label} />
            <div className="hairline" style={{ margin: "14px 0" }} />
            <p className="eyebrow">Why authenticity matters</p>
            <p className="muted" style={{ fontSize: "0.85rem", marginTop: 8 }}>
              Every photo is checked for AI-generation and tampering (C2PA / SynthID). Flagged images
              are still submitted — clearly marked — but genuine photos carry the decision.
            </p>
            <div className="hairline" style={{ margin: "14px 0" }} />
            <div className="spread">
              <span className="muted" style={{ fontSize: "0.78rem" }}>
                Storage
              </span>
              <span className="chip mono" style={{ fontSize: "0.68rem" }}>
                {persistenceMode === "supabase" ? "supabase · cross-device" : "local demo store"}
              </span>
            </div>
          </div>
        </aside>
      </main>
    </>
  );
}

function Verdict({ decision, decidedBy }: { decision: ClaimDecision; decidedBy: "live" | "demo" | null }) {
  const status = decision.claim_status;
  const color =
    status === "supported"
      ? "var(--supported)"
      : status === "contradicted"
        ? "var(--contradicted)"
        : "var(--risk)";
  const label =
    status === "supported" ? "Supported" : status === "contradicted" ? "Contradicted" : "Needs more info";
  const flags = decision.risk_flags.split(";").map((f) => f.trim()).filter((f) => f && f !== "none");
  return (
    <div className="panel" style={{ marginBottom: 16, borderColor: color }}>
      <div className="spread">
        <p className="eyebrow" style={{ margin: 0 }}>
          Agent decision
        </p>
        <span className="chip mono" style={{ fontSize: "0.62rem" }}>
          {decidedBy === "live" ? "live Gemini agent" : "demo engine"}
        </span>
      </div>
      <div className="row" style={{ gap: 8, alignItems: "center", margin: "10px 0 4px" }}>
        <span className="dot" style={{ background: color, width: 11, height: 11 }} />
        <span style={{ fontWeight: 700, fontSize: "1.1rem", color }}>{label}</span>
      </div>
      <Rail label="Issue" value={decision.issue_type} />
      <Rail label="Part" value={decision.object_part} />
      <Rail label="Severity" value={decision.severity} />
      <Rail label="Evidence" value={decision.evidence_standard_met === true || String(decision.evidence_standard_met) === "true" ? "sufficient" : "insufficient"} />
      <Rail label="Supports" value={decision.supporting_image_ids || "none"} />
      {flags.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span className="muted" style={{ fontSize: "0.72rem" }}>
            Risk flags
          </span>
          <div className="thumbs" style={{ gap: 6, marginTop: 6, justifyContent: "flex-start", flexWrap: "wrap" }}>
            {flags.map((f) => (
              <span key={f} className="chip" style={{ fontSize: "0.64rem", color: "var(--risk)" }}>
                {f.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="hairline" style={{ margin: "12px 0" }} />
      <p className="muted" style={{ fontSize: "0.8rem", lineHeight: 1.5 }}>
        {decision.claim_status_justification}
      </p>
    </div>
  );
}

function Rail({ label, value }: { label: string; value: string }) {
  return (
    <div className="spread" style={{ padding: "7px 0" }}>
      <span className="muted" style={{ fontSize: "0.82rem" }}>
        {label}
      </span>
      <span className="mono" style={{ fontSize: "0.82rem", textAlign: "right" }}>
        {value}
      </span>
    </div>
  );
}

function demoDecide(object: ClaimObject, part: string, images: EvidenceImage[]): ClaimDecision {
  const real = images.filter((i) => !i.aiGenerated);
  const anyAi = images.some((i) => i.aiGenerated);
  const issues: IssueType[] = ["dent", "scratch", "crack", "broken_part", "water_damage", "torn_packaging"];
  const issue: IssueType = issues.find((k) => part.toLowerCase().includes(k)) ?? "unknown";
  const flags: string[] = [];
  if (anyAi) flags.push("non_original_image", "possible_manipulation");
  if (real.length === 0) flags.push("manual_review_required");
  const status = real.length > 0 ? "supported" : "not_enough_information";
  return {
    evidence_standard_met: real.length > 0,
    evidence_standard_met_reason:
      real.length > 0 ? "At least one genuine photo shows the claimed part." : "No genuine photo verified; manual review.",
    risk_flags: flags.length ? flags.join(";") : "none",
    issue_type: issue,
    object_part: part || "unknown",
    claim_status: status,
    claim_status_justification:
      real.length > 0 ? `Genuine photo(s) show the ${part || object} consistent with the report.` : "Evidence insufficient or unverified.",
    supporting_image_ids: real.map((i) => i.id).join(";") || "none",
    valid_image: real.length > 0,
    severity: real.length > 0 ? "medium" : "unknown",
  };
}
