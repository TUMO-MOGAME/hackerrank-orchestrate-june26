// One-off: generate the ClaimLens luxury car wheel-rim logo via the Gemini Imagen API.
// Uses Imagen 4 Ultra for photorealistic output. Reads GEMINI_API_KEY from apps/web/.env.local.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const env = readFileSync(resolve(root, ".env.local"), "utf8");
const KEY = (env.match(/^GEMINI_API_KEY=(.*)$/m)?.[1] ?? "").trim();
if (!KEY) throw new Error("no GEMINI_API_KEY in .env.local");

const MODEL = "imagen-4.0-ultra-generate-001";
const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:predict?key=${KEY}`;

const prompt = `Professional studio product photograph of a single luxury car alloy wheel rim with a
glossy black tire, shot perfectly head-on (straight front view, fully circular). Polished metallic
multi-spoke alloy rim with a brushed bronze/champagne finish, fine machined detail, a centered hub
cap, realistic reflections and highlights. Soft diffused studio lighting, shallow depth of field with
the rim in razor-sharp focus, on a clean light neutral seamless background. Ultra realistic,
photorealistic, high detail, DSLR macro shot, commercial automotive photography. No text, no
watermark.`;

async function gen(outName) {
  const body = {
    instances: [{ prompt }],
    parameters: { sampleCount: 1, aspectRatio: "1:1" },
  };
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  const json = await res.json();
  const pred = json.predictions?.[0];
  const b64 = pred?.bytesBase64Encoded ?? pred?.image?.imageBytes;
  if (!b64) throw new Error("no image in response: " + JSON.stringify(json).slice(0, 400));
  const buf = Buffer.from(b64, "base64");
  const out = resolve(root, "public/brand", outName);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, buf);
  console.log("saved", out, buf.length, "bytes");
}

await gen("logo-wheel.png");
