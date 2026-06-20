// ClaimLens mark — a luxury car wheel-rim emblem (generated via Gemini) + wordmark.

export function Mark({ size = 28 }: { size?: number }) {
  return (
    <span
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        borderRadius: size * 0.28,
        overflow: "hidden",
        border: "1px solid var(--line)",
        boxShadow: "var(--shadow-sm)",
        flex: "0 0 auto",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/brand/logo-wheel.png"
        alt="ClaimLens"
        width={size}
        height={size}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
    </span>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <Mark size={size} />
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontWeight: 600,
          fontSize: size * 0.74,
          letterSpacing: "-0.02em",
        }}
      >
        Claim<span style={{ color: "var(--ember)" }}>Lens</span>
      </span>
    </span>
  );
}
