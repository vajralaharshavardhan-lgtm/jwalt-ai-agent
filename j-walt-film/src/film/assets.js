// Asset manifest. Every photograph is a real J-WALT project photograph cropped
// from the source pack (see analysis/catalogue.md). Renders are deliberately
// absent. A "view" is the safe region of a photo that shots may use: the
// camera cannot frame anything outside it.

const PORTFOLIO = 'assets/portfolio/';

// id: [file, page, project, view {sx, sy, w, h} (omit = whole photo)]
export const VIEWS = {
  'heid-reception':     ['heid-reception', 5, 'Heidelberg', { sx: 0, sy: 0, w: 968, h: 945 }],         // excludes CCTV dome (right edge) + floor mat (bottom left)
  'heid-boardroom':     ['heid-boardroom', 6, 'Heidelberg'],
  'heid-stained':       ['heid-stained-corridor', 8, 'Heidelberg', { sx: 0, sy: 0, w: 1122, h: 680 }],   // excludes box (y > 692), bottom right
  'heid-corridor':      ['heid-corridor-glass', 7, 'Heidelberg', { sx: 0, sy: 0, w: 751, h: 700 }],      // excludes box (y > 705), bottom left
  'heid-curved':        ['heid-curved-glass', 8, 'Heidelberg', { sx: 0, sy: 0, w: 680, h: 953 }],        // excludes chair, right edge
  'heid2-hall':         ['heid2-hall', 21, 'Heidelberg (12,647 sq ft)'],
  'corys-openplan':     ['corys-openplan-b', 10, 'Corys Piping Systems', { sx: 0, sy: 16, w: 882, h: 942 }], // excludes logo fragment, top edge
  'omoda-reception':    ['omoda-reception', 14, 'OMODA | JAECOO', { sx: 290, sy: 355, w: 950, h: 534 }], // excludes garland + flags
  'snoc-boardroom':     ['snoc-boardroom-built', 13, 'SNOC', { sx: 0, sy: 0, w: 1008, h: 800 }],        // excludes leaflet, bottom
};

async function loadImage(src) {
  const el = new Image();
  el.src = src;
  await el.decode();
  return el;
}

export async function loadAssets() {
  const files = [...new Set(Object.values(VIEWS).map((v) => v[0]))];
  const els = Object.fromEntries(await Promise.all(files.map(async (f) => [f, await loadImage(`${PORTFOLIO}${f}.jpg`)])));
  const photos = {};
  for (const [id, [file, page, project, view]] of Object.entries(VIEWS)) {
    const el = els[file];
    const v = view ?? { sx: 0, sy: 0, w: el.naturalWidth, h: el.naturalHeight };
    photos[id] = { id, file, page, project, el, ...v, density: 1 };
  }
  const lines = await (await fetch(`${PORTFOLIO}heid-reception.lines.json`)).json();
  const logoJson = await (await fetch('assets/logo/jwalt-wordmark.json')).json();
  const logo = { path: new Path2D(logoJson.d), bounds: logoJson.bounds };
  return { photos, lines, logo };
}

export async function loadFonts() {
  await Promise.all([300, 400, 500].map((w) => document.fonts.load(`${w} 40px "Inter Tight"`)));
  await document.fonts.ready;
  if (!document.fonts.check('400 40px "Inter Tight"')) throw new Error('Inter Tight failed to load');
}
