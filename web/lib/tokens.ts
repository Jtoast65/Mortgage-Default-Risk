// Chart tokens mirror the CSS design system so Recharts matches the terminal look.
export const C = {
  bg: "#0B0E14",
  surface: "#151A23",
  surface2: "#1E252F",
  text: "#E6EAF0",
  muted: "#8B97A8",
  accent: "#4F8EF7",
  red: "#E5484D",
  hairline: "#252C38",
};

export const axisProps = {
  stroke: C.hairline,
  tick: { fill: C.muted, fontSize: 11 },
  tickLine: false,
} as const;
