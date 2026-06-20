// Streaming Gemini chat (LangChain). Streams the assistant's reply token-by-token while a
// parallel structured call extracts the claim fields. Output is newline-delimited JSON (NDJSON):
//   {"type":"token","text":"..."}   (many)
//   {"type":"fields","object":...,"incident":...,"part":...,"phase":...}   (once, at the end)
// The Gemini key is read from server env only. Falls back gracefully — the client retries the
// non-streaming /api/chat if this fails.

import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { AIMessage, HumanMessage, SystemMessage } from "@langchain/core/messages";
import { z } from "zod";

export const runtime = "nodejs";

const Fields = z.object({
  object: z.enum(["car", "laptop", "package"]).nullable(),
  incident: z.string().nullable(),
  part: z.string().nullable(),
  phase: z.enum(["collecting", "awaiting_evidence", "ready_to_submit"]),
});

const INTAKE = `You are "Lens", a warm, genuinely human-feeling assistant for ClaimLens (insurance
damage claims). You have personality: friendly, a little witty, empathetic, and natural — like a
helpful person, not a form.

CONVERSATION STYLE:
- Read the user's message and respond to what they ACTUALLY said. If they greet you ("hi", "hello"),
  greet them back warmly and ask how you can help — do NOT assume they have damage.
- If they make small talk or ask who you are, answer naturally before steering toward how you can help.
- Only begin collecting claim details once the user indicates they actually have a problem or want to
  file a claim. Never pre-suppose damage.
- Ask ONE question at a time, in a natural order. Don't interrogate or dump a checklist.
- Keep replies short (1-3 sentences), warm, and plain. Use the occasional light touch of personality.

WHEN THEY DO HAVE A CLAIM, gently gather over the conversation: (1) the object — car, laptop, or
package; (2) what happened and the damage; (3) the specific affected part. Once you have all three,
ask them to upload clear, ORIGINAL photos. If CONTEXT shows flagged>=1, kindly note an image looked
AI-generated — it'll still be filed but can't stand alone as proof, so ask for a genuine photo (never
block). Never re-ask something you already know (see CONTEXT.known).`;

interface InMsg {
  role: "user" | "bot";
  text: string;
}

export async function POST(req: Request) {
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!apiKey) return new Response(JSON.stringify({ error: "no_key" }), { status: 503 });

  const { messages = [], imagesUploaded = 0, flagged = 0, known = {} } = (await req.json()) as {
    messages?: InMsg[];
    imagesUploaded?: number;
    flagged?: number;
    known?: Record<string, unknown>;
  };

  const model = new ChatGoogleGenerativeAI({
    apiKey,
    model: process.env.CLAIMREVIEW_CHAT_MODEL || "gemini-2.5-flash-lite",
    temperature: 0.4,
    maxOutputTokens: 500,
  });

  const ctx = `CONTEXT: images_uploaded=${imagesUploaded}, flagged=${flagged}, known=${JSON.stringify(known)}`;
  const history = messages.map((m) =>
    m.role === "user" ? new HumanMessage(m.text) : new AIMessage(m.text),
  );
  const replyMsgs = [new SystemMessage(`${INTAKE}\n\n${ctx}\nReply naturally; do NOT output JSON.`), ...history];
  const extractMsgs = [
    new SystemMessage(
      `Extract the claim fields from this conversation. ${ctx}\nReturn object (car/laptop/package or null), ` +
        `incident (one sentence or null), part (or null), and phase: "collecting" until object+incident+part ` +
        `are known, then "awaiting_evidence", then "ready_to_submit" once images_uploaded>=1 and the user is done.`,
    ),
    ...history,
  ];

  const extractionPromise = model
    .withStructuredOutput(Fields, { name: "fields" })
    .invoke(extractMsgs)
    .catch(() => ({ object: null, incident: null, part: null, phase: "collecting" as const }));

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (obj: unknown) => controller.enqueue(encoder.encode(JSON.stringify(obj) + "\n"));
      try {
        const tokens = await model.stream(replyMsgs);
        for await (const chunk of tokens) {
          const text = typeof chunk.content === "string" ? chunk.content : "";
          if (text) send({ type: "token", text });
        }
      } catch (e) {
        send({ type: "error", message: e instanceof Error ? e.message : "stream_error" });
      }
      const fields = await extractionPromise;
      send({ type: "fields", ...fields });
      controller.close();
    },
  });

  return new Response(stream, {
    headers: { "content-type": "application/x-ndjson; charset=utf-8", "cache-control": "no-cache" },
  });
}
