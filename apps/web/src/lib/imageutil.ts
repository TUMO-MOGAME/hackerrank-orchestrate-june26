// Client-only image helper. Downscales a data URL to a small JPEG thumbnail so claims can be
// persisted in localStorage without blowing the ~5MB quota. Full-resolution images are still
// sent to the agent API for adjudication; only the *stored* copy is shrunk (the admin/claims
// views only need a preview).

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

export async function downscaleDataUrl(
  dataUrl: string,
  maxDim = 640,
  quality = 0.6,
): Promise<string> {
  if (typeof window === "undefined" || !dataUrl.startsWith("data:")) return dataUrl;
  try {
    const img = await loadImage(dataUrl);
    const longest = Math.max(img.width, img.height) || 1;
    const scale = Math.min(1, maxDim / longest);
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return dataUrl;
    ctx.drawImage(img, 0, 0, w, h);
    const out = canvas.toDataURL("image/jpeg", quality);
    // Keep whichever is smaller (tiny PNGs can grow when re-encoded as JPEG).
    return out.length < dataUrl.length ? out : dataUrl;
  } catch {
    return dataUrl;
  }
}
