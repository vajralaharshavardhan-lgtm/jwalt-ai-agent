/**
 * BRAND TOKENS: the single source of truth for colour in the film.
 *
 * ────────────────────────────────────────────────────────────────────────────
 * STATUS: PROVISIONAL. NOT YET EXTRACTED FROM THE WEBSITE.
 *
 * The brand site (https://aquamarine-kheer-0fe440.netlify.app/) was blocked by
 * the network policy of the environment this project was built in, so these
 * values could not be sampled from it. They are a restrained, earthy palette
 * chosen to suit the subject (seed, soil, leaf, chilli), not the brand's own.
 *
 * To make the film match the website:
 *   1. On a machine with internet access run `npm run extract-brand`.
 *   2. Open brand-extract/report.md: it lists every colour the site's HTML/CSS
 *      uses, ranked by frequency, plus CSS custom properties by name.
 *   3. Map the site's colours onto the ROLES below (keep the keys, change the
 *      hex values). Every scene reads colour only from this file.
 * ────────────────────────────────────────────────────────────────────────────
 */
export const palette = {
  /** Near-black with a green cast. Base of every dark frame. */
  ink: '#060D09',
  /** Deep brand green. Plates, crop montage backgrounds. */
  forest: '#0E2A1C',
  /** Mid green. Leaves, UI accents. */
  leaf: '#3F7A45',
  /** Fresh highlight green. Backlit leaf veins, shoots. */
  sprout: '#A5CC7C',
  /** Warm seed-gold. Hairlines, highlights, the logo light. */
  husk: '#C9A56B',
  /** Pale gold. Seed body, rim lights. */
  huskLight: '#EEDCB4',
  /** Primary text on dark backgrounds. */
  cream: '#F4EFE3',
  /** Soil cross-section. */
  soil: '#24170E',
  soilLight: '#5B4130',
  /** Chilli / harvest reds. */
  chilli: '#B7261B',
  chilliDeep: '#6E110C',
  /** Golden-hour sun. */
  sun: '#F6C47C',
} as const;

/** Semantic roles used by typography and overlays. */
export const roles = {
  textPrimary: palette.cream,
  textSecondary: 'rgba(244, 239, 227, 0.72)',
  textMuted: 'rgba(244, 239, 227, 0.45)',
  accent: palette.husk,
  hairline: 'rgba(201, 165, 107, 0.75)',
} as const;

/** Crop colours used by the portfolio montage (natural produce colours, not brand). */
export const produce = {
  chilliRed: ['#E0473A', '#B7261B', '#5E0D08'],
  chilliGreen: ['#8BC766', '#3C8A34', '#12391A'],
  cucumber: ['#7FAF5C', '#35652C', '#132B12'],
  watermelon: ['#86B25E', '#355F29', '#0F2410'],
  bitterGourd: ['#A8D36F', '#4F9133', '#173A12'],
  bottleGourd: ['#D6E4A6', '#93B566', '#3F5A26'],
  ridgeGourd: ['#9CC06A', '#4C7A31', '#1B3312'],
  tomato: ['#F26A4B', '#C9301F', '#5A0E08'],
  okra: ['#A9D07A', '#5A8E3A', '#1E3B15'],
} as const;
