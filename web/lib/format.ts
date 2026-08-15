export const pct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;

export const num = (x: number) => x.toLocaleString("en-US");

export function usd(x: number, compact = true): string {
  if (compact) {
    if (Math.abs(x) >= 1e9) return `$${(x / 1e9).toFixed(2)}B`;
    if (Math.abs(x) >= 1e6) return `$${(x / 1e6).toFixed(2)}M`;
    if (Math.abs(x) >= 1e3) return `$${(x / 1e3).toFixed(0)}K`;
  }
  return `$${Math.round(x).toLocaleString("en-US")}`;
}
