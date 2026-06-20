// Server-side Gemini chat (LangChain). Drives the claim-intake conversation AND extracts the
// structured claim fields in one call. The Gemini key is read from the server env only — it is
// never exposed to the browser. The full transcript is passed each turn = the bot's memory.

import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { AIMessage, HumanMessage, SystemMessage } from "@langchain/core/messages";
import { NextResponse } from "next/server";
import { z } from "zod";

export const runtime = "nodejs";

const Schema = z.object({
  reply: z.string().describe("the assistant's next message to the user (1-3 sentences)"),
  object: z.enum(["car", "laptop", "package"]).nullable().describe("the claimed object, or null"),
  incident: z.string().nullable().describe("one-sentence summary of what happened, or null"),
  part: z.string().nullable().describe("the specific affected part, or null"),
  phase: z
    .enum(["collecting", "awaiting_evidence", "ready_to_submit"])
    .describe("collecting = still gathering object/incident/part; awaiting_evidence = ask for photos; ready_to_submit = enough collected"),
});

const SYSTEM = `You are "Lens", a warm, genuinely human-feeling assistant for ClaimLens, an
insurance damage-claim platform. You have personality: friendly, a little witty, empathetic, and
natural — like a real person, not a form.

CONVERSATION STYLE:
- Respond to what the user ACTUALLY said. If they just greet you ("hi", "hello"), greet them back
  warmly and ask how you can help — do NOT assume they have damage.
- If they make small talk or ask who you are, answer naturally before steering toward how you can help.
- Only start collecting claim details once the user shows they actually have a problem or want to
  file a claim. Never pre-suppose damage. While they're just chatting, keep phase="collecting" and
  leave object/incident/part null.
- Ask ONE question at a time, in a natural order. Don't interrogate or read out a checklist.
- Keep replies short (1-3 sentences), warm and plain, with a light touch of personality.

WHEN THEY DO HAVE A CLAIM, gather over the conversation (one friendly question at a time):
1. The object type — must be car, laptop, or package.
2. What happened and what the damage is.
3. The specific affected part (e.g. rear bumper, screen, box corner).

Once you have all three, set phase="awaiting_evidence" and ask them to upload clear, ORIGINAL
photos of the damage. When CONTEXT shows images_uploaded >= 1 and the user signals they're done,
set phase="ready_to_submit" and tell them you'll file it for review.

If CONTEXT shows flagged >= 1, an uploaded photo was detected as AI-generated/edited. Gently tell
the user it will still be filed but can't stand alone as proof, and encourage at least one genuine
photo. Never block submission over it.

Rules: carry forward already-known fields (don't re-ask). Always return the structured fields
reflecting everything known so far.`;

interface InMsg {
  role: "user" | "bot";
  text: string;
}

export async function POST(req: Request) {
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) return NextResponse.json({ error: "no_key" }, { status: 503 });

  let payload: {
    messages?: InMsg[];
    imagesUploaded?: number;
    flagged?: number;
    known?: Record<string, unknown>;
  };
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }
  const { messages = [], imagesUploaded = 0, flagged = 0, known = {} } = payload;

  const model = new ChatGoogleGenerativeAI({
    apiKey,
    model: process.env.CLAIMREVIEW_CHAT_MODEL || "gemini-2.5-flash-lite",
    temperature: 0.4,
    maxOutputTokens: 800,
  });
  const structured = model.withStructuredOutput(Schema, { name: "claim_intake" });

  const system = new SystemMessage(
    `${SYSTEM}\n\nCURRENT CONTEXT: images_uploaded=${imagesUploaded}, flagged=${flagged}, ` +
      `known=${JSON.stringify(known)}`,
  );
  const history = messages.map((m) =>
    m.role === "user" ? new HumanMessage(m.text) : new AIMessage(m.text),
  );

  try {
    const out = await structured.invoke([system, ...history]);
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "llm_error" }, { status: 500 });
  }
}
