#!/usr/bin/env node
/**
 * Pulls the brand's real colours, fonts and images from the website so the
 * film can be matched to it. Run on any machine with internet access:
 *
 *   npm run extract-brand
 *   npm run extract-brand -- --url=https://aquamarine-kheer-0fe440.netlify.app/
 *
 * Writes brand-extract/:
 *   report.md    colours ranked by use, CSS custom properties, font families,
 *                every image with where it was found, suggested slot names
 *   report.json  the same, machine-readable
 *   images/      every image the site references (HTML, CSS and JS bundles,
 *                so single-page apps built with Vite/React are covered too)
 *
 * It does not change the film: you decide which colour maps to which role in
 * src/styles/brand.ts and which image goes in which slot (public/assets/).
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argUrl = process.argv.find((a) => a.startsWith('--url='));
const SITE = (argUrl ? argUrl.slice(6) : 'https://aquamarine-kheer-0fe440.netlify.app/').replace(/\/?$/, '/');
const out = path.join(root, 'brand-extract');
fs.mkdirSync(path.join(out, 'images'), {recursive: true});

const get = async (url, asText = true) => {
  const res = await fetch(url, {headers: {'user-agent': 'Mozilla/5.0 (brand-extract for Premium Seeds film)'}});
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return asText ? res.text() : Buffer.from(await res.arrayBuffer());
};
const abs = (u, base) => {
  try {
    return new URL(u.replace(/&amp;/g, '&'), base).href;
  } catch {
    return null;
  }
};

const IMG_RE = /(?:src|href|srcset|content|data-src)=["']([^"']+?\.(?:png|jpe?g|webp|avif|svg|gif)(?:\?[^"']*)?)["']/gi;
const URL_RE = /url\(\s*["']?([^"')]+?\.(?:png|jpe?g|webp|avif|svg|gif)(?:\?[^"')]*)?)["']?\s*\)/gi;
const JS_IMG_RE = /["'`]([^"'`\s]+?\.(?:png|jpe?g|webp|avif|svg|gif))["'`]/gi;
const COLOR_RE = /#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3})\b|rgba?\([^)]+\)|hsla?\([^)]+\)|oklch\([^)]+\)/gi;
const VAR_RE = /(--[\w-]+)\s*:\s*([^;}{]+)/g;
const FONT_RE = /font-family\s*:\s*([^;}{]+)/gi;
const GFONT_RE = /fonts\.googleapis\.com\/css2?\?[^"')\s]+/gi;

const main = async () => {
  console.log(`[brand] fetching ${SITE}`);
  const html = await get(SITE);
  fs.writeFileSync(path.join(out, 'index.html'), html);

  const cssUrls = [...html.matchAll(/<link[^>]+href=["']([^"']+\.css[^"']*)["']/gi)].map((m) => abs(m[1], SITE)).filter(Boolean);
  const jsUrls = [...html.matchAll(/<script[^>]+src=["']([^"']+\.m?js[^"']*)["']/gi)].map((m) => abs(m[1], SITE)).filter(Boolean);
  const inlineCss = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).join('\n');
  const inlineStyles = [...html.matchAll(/style=["']([^"']+)["']/gi)].map((m) => m[1]).join(';\n');

  const sources = [{name: 'index.html', url: SITE, text: html + '\n' + inlineCss + '\n' + inlineStyles}];
  for (const u of [...cssUrls, ...jsUrls]) {
    try {
      sources.push({name: path.basename(new URL(u).pathname), url: u, text: await get(u)});
      console.log(`[brand]   + ${u}`);
    } catch (e) {
      console.warn(`[brand]   ! ${e.message}`);
    }
  }

  const colors = new Map();
  const vars = new Map();
  const fonts = new Map();
  const googleFonts = new Set();
  const images = new Map();
  for (const s of sources) {
    const isJs = /\.m?js$/.test(new URL(s.url).pathname);
    for (const m of s.text.matchAll(COLOR_RE)) {
      const c = m[0].toLowerCase().replace(/\s+/g, '');
      colors.set(c, (colors.get(c) ?? 0) + 1);
    }
    for (const m of s.text.matchAll(VAR_RE)) {
      if (/#|rgb|hsl|oklch/.test(m[2])) vars.set(m[1], m[2].trim());
    }
    for (const m of s.text.matchAll(FONT_RE)) {
      const f = m[1].trim().replace(/["']/g, '');
      fonts.set(f, (fonts.get(f) ?? 0) + 1);
    }
    for (const m of s.text.matchAll(GFONT_RE)) googleFonts.add(m[0]);
    const add = (u) => {
      for (const part of u.split(',')) {
        const clean = part.trim().split(/\s+/)[0];
        const a = abs(clean, s.url);
        if (a && !images.has(a)) images.set(a, s.name);
      }
    };
    for (const m of s.text.matchAll(IMG_RE)) add(m[1]);
    for (const m of s.text.matchAll(URL_RE)) add(m[1]);
    if (isJs) for (const m of s.text.matchAll(JS_IMG_RE)) if (!m[1].startsWith('data:')) add(m[1]);
  }
  for (const m of html.matchAll(/<img[^>]*>/gi)) {
    const src = /src=["']([^"']+)["']/i.exec(m[0])?.[1];
    const alt = /alt=["']([^"']*)["']/i.exec(m[0])?.[1];
    if (src) {
      const a = abs(src, SITE);
      if (a) images.set(a, `index.html <img alt="${alt ?? ''}">`);
    }
  }

  const downloaded = [];
  for (const [u, where] of images) {
    try {
      const buf = await get(u, false);
      const name = decodeURIComponent(path.basename(new URL(u).pathname)).replace(/[^\w.-]/g, '_');
      fs.writeFileSync(path.join(out, 'images', name), buf);
      downloaded.push({url: u, file: `images/${name}`, bytes: buf.length, foundIn: where});
      console.log(`[brand]   image ${name} (${Math.round(buf.length / 1024)} KB)`);
    } catch (e) {
      console.warn(`[brand]   ! image ${e.message}`);
    }
  }

  const ranked = [...colors.entries()].sort((a, b) => b[1] - a[1]);
  const report = {
    site: SITE,
    fetchedAt: new Date().toISOString(),
    colors: ranked.map(([c, n]) => ({color: c, uses: n})),
    cssVariables: Object.fromEntries(vars),
    fontFamilies: [...fonts.entries()].sort((a, b) => b[1] - a[1]).map(([f, n]) => ({family: f, uses: n})),
    googleFonts: [...googleFonts],
    images: downloaded,
  };
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 2));

  const guess = (f) =>
    /logo/i.test(f) ? 'logo' :
    /top.?gun|chil+i/i.test(f) ? 'topgun-product / crop-chilli' :
    /research|lab|breed/i.test(f) ? 'research-breeder' :
    /field|farm|trial/i.test(f) ? 'field-wide / harvest-farmer' :
    /tomato/i.test(f) ? 'crop-tomato' : /okra|bhindi/i.test(f) ? 'crop-okra' :
    /cucumber/i.test(f) ? 'crop-cucumber' : /water.?melon/i.test(f) ? 'crop-watermelon' :
    /bitter/i.test(f) ? 'crop-bitter-gourd' : /bottle/i.test(f) ? 'crop-bottle-gourd' :
    /ridge/i.test(f) ? 'crop-ridge-gourd' : '';
  const md = [
    `# Brand extract: ${SITE}`,
    `Fetched ${report.fetchedAt}`,
    '',
    '## CSS custom properties (colours)',
    ...(vars.size ? [...vars.entries()].map(([k, v]) => `- \`${k}\`: \`${v}\``) : ['_none found_']),
    '',
    '## Colours by frequency (top 40)',
    ...ranked.slice(0, 40).map(([c, n]) => `- \`${c}\` × ${n}`),
    '',
    '## Font families',
    ...report.fontFamilies.map((f) => `- ${f.family} (× ${f.uses})`),
    ...(googleFonts.size ? ['', 'Google Fonts links:', ...[...googleFonts].map((g) => `- https://${g}`)] : []),
    '',
    '## Images',
    '| file | size | found in | suggested slot |',
    '|---|---|---|---|',
    ...downloaded.map((d) => `| ${d.file} | ${Math.round(d.bytes / 1024)} KB | ${d.foundIn} | ${guess(d.file)} |`),
    '',
    'Next: map colours onto the roles in src/styles/brand.ts, copy chosen images',
    'into public/assets/ renamed to their slot id (see src/assets/slots.json).',
  ].join('\n');
  fs.writeFileSync(path.join(out, 'report.md'), md);
  console.log(`[brand] done → ${path.relative(root, out)}/report.md (${downloaded.length} images, ${ranked.length} colours)`);
};

main().catch((e) => {
  console.error(`[brand] failed: ${e.message}`);
  process.exit(1);
});
