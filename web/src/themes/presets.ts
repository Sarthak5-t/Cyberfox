import type { DashboardTheme, ThemeTypography, ThemeLayout } from "./types";

/**
 * Built-in dashboard themes.
 *
 * Each theme defines its own palette, typography, and layout so switching
 * themes produces visible changes beyond just color — fonts, density, and
 * corner-radius all shift to match the theme's personality.
 *
 * Theme names must stay in sync with the backend's
 * `_BUILTIN_DASHBOARD_THEMES` list in `cyberfox_cli/web_server.py`.
 */

// ---------------------------------------------------------------------------
// Shared typography / layout presets
// ---------------------------------------------------------------------------

/** Default system stack — neutral, safe fallback for every platform. */
const SYSTEM_SANS =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
const SYSTEM_MONO =
  'ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace';

const DEFAULT_TYPOGRAPHY: ThemeTypography = {
  fontSans: `"Share Tech Mono", "JetBrains Mono", ${SYSTEM_MONO}`,
  fontMono: `"Share Tech Mono", "JetBrains Mono", ${SYSTEM_MONO}`,
  fontUrl:
    "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=JetBrains+Mono:wght@400;700&display=swap",
  baseSize: "14px",
  lineHeight: "1.5",
  letterSpacing: "0.02em",
};

const DEFAULT_LAYOUT: ThemeLayout = {
  radius: "0",
  density: "compact",
};

// ---------------------------------------------------------------------------
// Shared Horizon typography / layout
// ---------------------------------------------------------------------------

const HORIZON_TYPOGRAPHY: ThemeTypography = {
  fontSans: `"Inter", ${SYSTEM_SANS}`,
  fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`,
  fontUrl:
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap",
  baseSize: "15px",
  lineHeight: "1.6",
  letterSpacing: "-0.01em",
};

const HORIZON_LAYOUT: ThemeLayout = {
  radius: "0.75rem",
  density: "comfortable",
};

// ---------------------------------------------------------------------------
// Themes
// ---------------------------------------------------------------------------

export const horizonTheme: DashboardTheme = {
  name: "horizon",
  label: "Horizon",
  description: "Warm light theme — clean and approachable",
  palette: {
    background: { hex: "#f8f6f3", alpha: 1 },
    midground: { hex: "#1e293b", alpha: 1 },
    foreground: { hex: "#2563eb", alpha: 0 },
    warmGlow: "rgba(37, 99, 235, 0.08)",
    noiseOpacity: 0,
  },
  typography: HORIZON_TYPOGRAPHY,
  layout: HORIZON_LAYOUT,
  terminalBackground: "#f8f6f3",
  terminalForeground: "#1e293b",
  seriesColors: {
    inputTokenAccent: "#2563eb",
    outputTokenAccent: "#7c3aed",
  },
  colorOverrides: {
    destructive: "#dc2626",
    destructiveForeground: "#ffffff",
    success: "#16a34a",
    warning: "#d97706",
  },
  swatchColors: ["#f8f6f3", "#1e293b", "#2563eb"],
};

export const horizonDarkTheme: DashboardTheme = {
  name: "horizon-dark",
  label: "Horizon Dark",
  description: "Warm dark theme — soft on the eyes",
  palette: {
    background: { hex: "#18181b", alpha: 1 },
    midground: { hex: "#e4e4e7", alpha: 1 },
    foreground: { hex: "#60a5fa", alpha: 0 },
    warmGlow: "rgba(96, 165, 250, 0.15)",
    noiseOpacity: 0,
  },
  typography: HORIZON_TYPOGRAPHY,
  layout: HORIZON_LAYOUT,
  terminalBackground: "#18181b",
  terminalForeground: "#e4e4e7",
  seriesColors: {
    inputTokenAccent: "#60a5fa",
    outputTokenAccent: "#a78bfa",
  },
  colorOverrides: {
    destructive: "#ef4444",
    destructiveForeground: "#ffffff",
    success: "#22c55e",
    warning: "#f59e0b",
  },
  swatchColors: ["#18181b", "#e4e4e7", "#60a5fa"],
};

export const defaultTheme: DashboardTheme = horizonDarkTheme;

export const midnightTheme: DashboardTheme = {
  name: "midnight",
  label: "Midnight",
  description: "Deep blue-violet with cool accents",
  palette: {
    background: { hex: "#0a0a1f", alpha: 1 },
    midground: { hex: "#d4c8ff", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(167, 139, 250, 0.32)",
    noiseOpacity: 0.8,
  },
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    fontSans: `"Inter", ${SYSTEM_SANS}`,
    fontMono: `"JetBrains Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap",
    letterSpacing: "-0.005em",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    radius: "0.75rem",
  },
};

export const emberTheme: DashboardTheme = {
  name: "ember",
  label: "Ember",
  description: "Warm crimson and bronze — forge vibes",
  palette: {
    background: { hex: "#1a0a06", alpha: 1 },
    midground: { hex: "#ffd8b0", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(249, 115, 22, 0.38)",
    noiseOpacity: 1,
  },
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    fontSans: `"Spectral", Georgia, "Times New Roman", serif`,
    fontMono: `"IBM Plex Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=Spectral:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;700&display=swap",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    radius: "0.25rem",
  },
  colorOverrides: {
    destructive: "#c92d0f",
    warning: "#f97316",
  },
};

export const monoTheme: DashboardTheme = {
  name: "mono",
  label: "Mono",
  description: "Clean grayscale — minimal and focused",
  palette: {
    background: { hex: "#0e0e0e", alpha: 1 },
    midground: { hex: "#eaeaea", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(255, 255, 255, 0.1)",
    noiseOpacity: 0.6,
  },
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    fontSans: `"IBM Plex Sans", ${SYSTEM_SANS}`,
    fontMono: `"IBM Plex Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    radius: "0",
  },
};

export const cyberpunkTheme: DashboardTheme = {
  name: "cyberpunk",
  label: "Cyberpunk",
  description: "Neon green on black — matrix terminal",
  palette: {
    background: { hex: "#040608", alpha: 1 },
    midground: { hex: "#9bffcf", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(0, 255, 136, 0.22)",
    noiseOpacity: 1.2,
  },
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    fontSans: `"Share Tech Mono", "JetBrains Mono", ${SYSTEM_MONO}`,
    fontMono: `"Share Tech Mono", "JetBrains Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=JetBrains+Mono:wght@400;700&display=swap",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    radius: "0",
  },
  colorOverrides: {
    success: "#00ff88",
    warning: "#ffd700",
    destructive: "#ff0055",
  },
};

export const roseTheme: DashboardTheme = {
  name: "rose",
  label: "Rosé",
  description: "Soft pink and warm ivory — easy on the eyes",
  palette: {
    background: { hex: "#1a0f15", alpha: 1 },
    midground: { hex: "#ffd4e1", alpha: 1 },
    foreground: { hex: "#ffffff", alpha: 0 },
    warmGlow: "rgba(249, 168, 212, 0.3)",
    noiseOpacity: 0.9,
  },
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    fontSans: `"Fraunces", Georgia, serif`,
    fontMono: `"DM Mono", ${SYSTEM_MONO}`,
    fontUrl:
      "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=DM+Mono:wght@400;500&display=swap",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    radius: "1rem",
  },
};

/** Light mode — vivid Cyberfox-blue accents on a cream canvas. */
export const cyberfoxBlueTheme: DashboardTheme = {
  name: "cyberfox-blue",
  label: "Cyberfox Blue",
  description: "Light mode — vivid Cyberfox-blue accents on cream canvas",
  palette: {
    background: { hex: "#E8F2FD", alpha: 1 },
    midground: { hex: "#0053FD", alpha: 1 },
    foreground: { hex: "#170d02", alpha: 0 },
    warmGlow: "rgba(0, 83, 253, 0.12)",
    noiseOpacity: 0,
  },
  typography: DEFAULT_TYPOGRAPHY,
  layout: DEFAULT_LAYOUT,
  terminalBackground: "#f5f8fc",
  terminalForeground: "#170d02",
  seriesColors: {
    inputTokenAccent: "#001934",
    outputTokenAccent: "#0053fd",
  },
  swatchColors: ["#170d02", "#0053FD", "#E8F2FD"],
};

/**
 * Same look as ``defaultTheme`` but with a larger root font size, looser
 * line-height, and ``spacious`` density so every rem-based size in the
 * dashboard scales up. For users who find the default 15px UI too dense.
 */
export const defaultLargeTheme: DashboardTheme = {
  name: "default-large",
  label: "Cyberpunk (Large)",
  description: "Cyberpunk with bigger fonts and roomier spacing",
  palette: defaultTheme.palette,
  typography: {
    ...DEFAULT_TYPOGRAPHY,
    baseSize: "17px",
    lineHeight: "1.6",
  },
  layout: {
    ...DEFAULT_LAYOUT,
    density: "comfortable",
  },
};

export const BUILTIN_THEMES: Record<string, DashboardTheme> = {
  default: defaultTheme,
  "default-large": defaultLargeTheme,
  horizon: horizonTheme,
  "horizon-dark": horizonDarkTheme,
  "cyberfox-blue": cyberfoxBlueTheme,
  midnight: midnightTheme,
  ember: emberTheme,
  mono: monoTheme,
  cyberpunk: cyberpunkTheme,
  rose: roseTheme,
};
