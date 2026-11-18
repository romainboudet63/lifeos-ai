/**
 * Palette LifeOS — thème "croissance personnelle".
 * Choix délibéré : vert mousse (croissance, calme) comme accent primaire,
 * ambre chaud comme accent secondaire (énergie, motivation) — on évite
 * le duo crème/terracotta et le duo noir/vert-acide, devenus des défauts
 * IA reconnaissables plutôt que des choix.
 */

export const lightColors = {
  background: "#F6F4EE",   // parchemin chaud, plus doux qu'un blanc pur
  surface: "#FFFFFF",
  surfaceMuted: "#EDEAE1",
  border: "#DEDACD",

  textPrimary: "#1F2A24",  // encre verte profonde
  textSecondary: "#5C6B63",
  textInverse: "#F6F4EE",

  accent: "#3F7A5C",        // mousse — actions primaires, progression
  accentMuted: "#DCE8DF",
  warning: "#C98A3D",       // ambre — motivation, alertes douces
  danger: "#B4523F",

  scoreRingTrack: "#E4E0D3",
};

export const darkColors = {
  background: "#121712",
  surface: "#1A211C",
  surfaceMuted: "#212922",
  border: "#2B342D",

  textPrimary: "#EDEFE8",
  textSecondary: "#9AA79E",
  textInverse: "#121712",

  accent: "#6FB98C",
  accentMuted: "#24352B",
  warning: "#D9A15C",
  danger: "#D97B67",

  scoreRingTrack: "#242C25",
};

export type ThemeColors = typeof lightColors;
