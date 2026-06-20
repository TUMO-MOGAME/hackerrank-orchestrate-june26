// Shared design tokens — "forensic editorial" theme. Single source of truth for the
// web (CSS variables mirror these) and mobile (imported directly). Warm paper + warm ink,
// ember brand accent, and a semantic verdict palette that maps to claim_status.

export const theme = {
  color: {
    paper: "#F6F2E9", // warm off-white background
    paperRaised: "#FBF9F2", // cards/surfaces
    ink: "#17150F", // primary text / near-black
    inkSoft: "#4A463C", // secondary text
    inkFaint: "#8A8475", // muted text / captions
    line: "#E2DCCD", // hairline borders
    lineStrong: "#D3CAB4", // stronger borders / inputs
    ember: "#C2612C", // brand accent
    emberDeep: "#9F4A1E", // accent (links, hover)
    emberSoft: "#E8A87C", // accent tint
    emberWash: "#F3E3D3", // accent background wash
    // verdict palette (maps to claim_status)
    supported: "#3F7D5B",
    contradicted: "#B23A3A",
    needsInfo: "#C2902C",
    risk: "#9A4A2A",
  },
  font: {
    display: '"Fraunces", Georgia, serif',
    body: '"Hanken Grotesk", system-ui, sans-serif',
    mono: '"JetBrains Mono", ui-monospace, monospace',
  },
  radius: { sm: 8, md: 14, lg: 22, pill: 999 },
  space: (n: number) => n * 4,
} as const;

export type Theme = typeof theme;

/** Map a claim_status to its verdict color + human label. */
export function verdictMeta(status: string): { color: string; label: string } {
  switch (status) {
    case "supported":
      return { color: theme.color.supported, label: "Supported" };
    case "contradicted":
      return { color: theme.color.contradicted, label: "Contradicted" };
    default:
      return { color: theme.color.needsInfo, label: "Needs more info" };
  }
}
