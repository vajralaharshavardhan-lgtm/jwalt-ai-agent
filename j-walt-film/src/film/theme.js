// Visual system. One typeface (Inter Tight, OFL), one accent (J-WALT red,
// sampled from the logo on page 1 of the source pack), architectural neutrals.

export const W = 1920;
export const H = 1080;

export const C = {
  paper: '#F2F0EB',      // warm architectural white -- the drawing sheet
  ink: '#1D1D1B',        // lines + primary type
  graphite: '#76736D',   // secondary type, labels
  rule: '#1D1D1B',       // hairlines (used with alpha)
  red: '#BE1B20',        // J-WALT red, median of the logo's ink pixels (p01)
};

// 12-column grid: 120px outer margins, 24px gutters, 118px columns.
// Vertical safe area 96px top/bottom.
export const G = {
  margin: 120,
  top: 96,
  bottom: 984,
  col: 118,
  gutter: 24,
  x: (i) => 120 + i * 142,              // left edge of column i (0..11)
  xr: (i) => 120 + i * 142 + 118,        // right edge of column i
  lines: () => {                          // margins + gutter centres
    const xs = [120];
    for (let i = 0; i < 11; i++) xs.push(120 + i * 142 + 118 + 12);
    xs.push(1800);
    return xs;
  },
};

// Type: restrained sizes, weights 300/400/500 only, uppercase with measured
// tracking -- the voice of an architecture monograph, not an advert.
// Minimum sizes are set for phone viewing: nothing below 15px at 1080p.
export const T = {
  statement: { size: 54, weight: 300, track: 0.12, color: C.ink },   // FROM AN IDEA, project names
  service:   { size: 30, weight: 300, track: 0.1, color: C.ink },
  value:     { size: 23, weight: 400, track: 0.06, color: C.ink },
  label:     { size: 15, weight: 500, track: 0.2, color: C.graphite },
  index:     { size: 15, weight: 500, track: 0.2, color: C.graphite },
  numeral:   { size: 168, weight: 300, track: -0.02, color: C.ink },
  descriptor: { size: 20, weight: 400, track: 0.36, color: C.graphite },
  tagline:   { size: 20, weight: 500, track: 0.42, color: C.ink },
};

// Line weights (px at 1080p).
export const L = {
  draw: { color: C.ink, width: 1.5, alpha: 0.82 },     // construction lines (primary)
  ghost: { color: C.ink, width: 1.5, alpha: 0.55 },    // lines over photography
  rule: { color: C.rule, width: 1, alpha: 0.28 },      // title-block rules
  grid: { color: C.ink, width: 1, alpha: 0.07 },       // column grid
  dim: { color: C.ink, width: 1, alpha: 0.5 },         // dimension strings
  edge: { color: C.ink, width: 1.5, alpha: 0.9 },      // mask leading edges
};

// Architectural line-weight hierarchy for the construction drawing:
// the room's structure and the joinery outline read first, panel joints last.
export const WEIGHT = {
  structure: { width: 1.5, alpha: 0.85 },
  desk: { width: 1.5, alpha: 0.85 },
  rings: { width: 1.15, alpha: 0.72 },
  panels: { width: 1.0, alpha: 0.62 },
};
