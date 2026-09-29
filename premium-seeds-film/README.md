# Premium Seeds: brand film

A 45-second cinematic brand film for **Premium Seeds** (Bengaluru), built as a
real motion project in [Remotion](https://www.remotion.dev) (React + TypeScript).
It renders 1920×1080 (16:9), 1080×1920 (9:16) and 1080×1350 (4:5) from one
codebase, at 30 fps, with a generated score and sound design.

> **Story:** seed → breeding → research → field validation → crops → farmer →
> harvest → next generation.
> **Brand line:** *Better seed starts with the breeder.*

**Rendered previews** (compressed copies, CRF 25, ~16 MB each):
`renders/premium-seeds-16x9.mp4` and `renders/premium-seeds-9x16.mp4`.
Render full-quality masters locally with `npm run render:all`.

---

## ⚠️ Read first: what is provisional

The project was built in a sandbox whose network policy **blocked the brand
website** (`aquamarine-kheer-0fe440.netlify.app`, and `premiumseeds.in`). So:

| Area | Status | Where to fix |
|---|---|---|
| Copy & facts | ✅ Taken only from the website text quoted in the brief. Nothing invented. | `src/content/copy.ts` |
| Colours | ⚠️ **Provisional** earthy palette, *not* sampled from the site | `src/styles/brand.ts` |
| Fonts | ⚠️ **Provisional**: Fraunces (display), Inter (text), IBM Plex Mono (labels), all OFL | `src/styles/fonts.ts`, `src/styles/typography.ts` |
| Logo | ⚠️ **Not available**. The end card uses a typographic wordmark; no logo symbol was invented | drop `public/assets/logo.svg` |
| Photography | ⚠️ **None available**. Every scene has a built-in procedural visual; real photos/clips drop in via named slots | `public/assets/` |

Run `npm run extract-brand` on any machine with internet access. It downloads
the site's images and writes `brand-extract/report.md` with every colour
(ranked), CSS variable, font family and image, plus suggested slot names. Then
follow **Match the website's brand** below.

---

## Install

Requires Node 18+ (22 recommended).

```bash
cd premium-seeds-film
npm install
```

## Preview (Remotion Studio)

```bash
npm run studio
```

This opens the Studio in your browser. Compositions:

- `PremiumSeedsFilm`: the master film, 1920×1080
- `PremiumSeedsFilmVertical`: 1080×1920 (Reels / Shorts / Stories)
- `PremiumSeedsFilmFeed`: 1080×1350 (Instagram / LinkedIn feed)
- `AssetGuide`: the film with an overlay naming each scene, its timecode and
  which asset slots are filled (green) or using the fallback (amber)
- `Scenes/Scene01-…` to `Scene09-…`: each scene on its own, for fast iteration

`npm run studio` and every `render*` script first scan `public/assets/` and
(re)generate the soundtrack if needed.

## Render MP4

```bash
npm run render            # out/premium-seeds-16x9.mp4   (1920×1080, H.264, CRF 16)
npm run render:vertical   # out/premium-seeds-9x16.mp4   (1080×1920)
npm run render:all        # both
npm run render:preview    # out/premium-seeds-preview-540p.mp4 (fast, half-res)
npm run render:guide      # out/premium-seeds-asset-guide.mp4 (slot overlay)
npm run stills            # key frames → out/stills/ for review
```

4:5 feed version:

```bash
npx remotion render src/index.ts PremiumSeedsFilmFeed out/premium-seeds-4x5.mp4
```

On the first render Remotion downloads a headless Chrome. On locked-down
networks, point it at an existing Chrome/Chromium instead:

```bash
REMOTION_BROWSER_EXECUTABLE=/path/to/chrome npm run render
```

Quality and size: `remotion.config.ts` sets CRF 16 (near-lossless, needed for
the film grain). Use `--crf=22` for smaller files.

---

## Change text

All on-screen words are in **`src/content/copy.ts`**. Edit and re-render.
Set any line to `''` to hide it. Headlines wrap with balanced lines
automatically in every aspect ratio.

Keep to the brief's rule: one major sentence per scene, and only claims the
website makes.

## Replace images / video (asset slots)

Drop files into **`public/assets/`**, named after a slot id. The film picks
them up automatically, and removing a file restores the built-in visual.

| Slot file | Scene · time | What to supply | Without it |
|---|---|---|---|
| `logo.svg` / `.png` / `.webp` | 09 Final · 0:41 | Official logo, transparent, light version for dark bg | Wordmark only |
| `research-breeder.jpg` / `.mp4` | 03 Research · 0:08–0:13 | A Premium Seeds breeder with plants, or the R&D facility. Landscape, subject right | Botanical research plate |
| `field-wide.jpg` / `.mp4` | 04 Field · 0:15–0:18 | Wide shot of the company's trial field, low sun, ideally someone walking the rows | Procedural golden-hour field |
| `crop-chilli.jpg` … `crop-okra.jpg` (8 files: `crop-chilli`, `crop-cucumber`, `crop-watermelon`, `crop-bitter-gourd`, `crop-bottle-gourd`, `crop-ridge-gourd`, `crop-tomato`, `crop-okra`) | 05 Crops · 0:18–0:24 | Close-ups of each crop. **Supply all 8** (the montage switches to photos only when every crop has one, so it never mixes styles) | Morphing botanical renders |
| `topgun-product.png` | 06 Top Gun · 0:24–0:29 | Top Gun F1 product image from the website, ideally a transparent cut-out | Procedural macro chilli ripening green→red |
| `harvest-farmer.jpg` / `.mp4` | 07 Harvest · 0:29–0:31 | Real farmer inspecting a crop (with consent) | Backlit chilli canopy |
| `harvest-hands.jpg` / `.mp4` | 07 Harvest · 0:31–0:33 | Hands touching plants / harvesting | ″ |
| `harvest-basket.jpg` / `.mp4` | 07 Harvest · 0:33–0:35 | Basket or crate of harvested vegetables | ″ |
| `music.mp3` / `.wav` / `.m4a` | Whole film | Licensed music track | Generated score |

Photos are automatically treated as graded footage (slow push, drift, colour
grade toward the palette, vignette): see `src/components/CinematicImage.tsx`.
Video clips are used muted; trim them to at least the slot's duration.

To check what is filled: `npm run assets:scan`, or render `AssetGuide`.

Scenes 01, 02 and 08 (seed, germination, return to seed) are procedural
by design. They are the film's visual metaphor and need no photography.

## Replace music

- **Licensed track:** put it at `public/assets/music.mp3`. It replaces the
  generated score and gets a 20-frame fade-in and 2-second fade-out.
- **Keep or mute the sound design:** the generated SFX layer (seed tock,
  crack, growth, wind, transitions, logo impact) stays on top. Set
  `AUDIO_MIX.sfx = 0` in `src/components/Soundtrack.tsx` to mute it, or
  lower it if it clashes with your track.
- **Levels:** `AUDIO_MIX.music` / `AUDIO_MIX.sfx` in the same file.
- **Regenerate / edit the score:** `scripts/audio/generate-soundtrack.mjs`
  (the timeline of cues is at the top; `npm run audio` rebuilds in ~3 s).

## Match the website's brand

1. `npm run extract-brand` → open `brand-extract/report.md`.
2. **Colours:** in `src/styles/brand.ts`, keep the role names and replace
   the hex values: `forest` = the site's primary dark green, `leaf` = primary
   green, `husk` = its accent (gold/earth), `cream` = its light text colour.
   Every scene reads colour from this file.
3. **Fonts:** copy the site's `.woff2` files into `public/fonts/`, point
   `src/styles/fonts.ts` at them (family names `PS Display`, `PS Sans`,
   `PS Mono` can stay), and adjust weights / `fontVariationSettings` in
   `src/styles/typography.ts` (the Fraunces axis settings won't apply to other fonts).
4. **Images:** copy the useful ones into `public/assets/` renamed to slot ids.
5. `npm run stills` and review, then `npm run render:all`.

## Vertical and other formats

The film is written against an orientation-aware layout (`src/utils/layout.ts`):
every size is in units of the short edge, and each scene has a portrait
composition (subject higher, copy lower, clear of Reels/Shorts UI).
So the vertical version is simply:

```bash
npm run render:vertical
```

To add another size, register the same component in `src/Root.tsx` with new
`width`/`height`.

## Timing

`src/utils/timeline.ts` is the master timeline (30 fps, 1350 frames):

| # | Scene | Time | Visual | Text |
|---|---|---|---|---|
| 01 | OpeningSeed | 0:00–0:04 | Macro seed emerges from black; focus pull; tip splits, leaking light | Every harvest begins with a seed. |
| 02 | Germination | 0:04–0:08 | Match cut; light reveals soil cross-section; root, root hairs, shoot, cotyledons | But better seeds begin with better breeding. |
| 03 | Research | 0:08–0:13 | Seedling traced into a breeder's plate: grid, true leaves, leaf-cell micrograph, P1 × P2 → F1 | Vegetable genetics. Research. Field validation. / Designed for Indian growing conditions. |
| 04 | FieldValidation | 0:13–0:18 | Push into a backlit leaf; veins swing into crop-row furrows; golden-hour field dolly | From research to the field. / Validated across growing conditions. |
| 05 | CropPortfolio | 0:18–0:24 | Chilli → cucumber → watermelon → bitter gourd → bottle gourd → ridge gourd → tomato → okra, morphing point-for-point | 25+ vegetable crops / Built around real farming needs. |
| 06 | TopGunF1 | 0:24–0:29 | Macro chilli, orbiting light, ripens green → red | TOP GUN F1 · Chilli · F1 Hybrid · 55,000 SHU · 74 ASTA |
| 07 | FarmerHarvest | 0:29–0:35 | Backlit chilli crop at golden hour (+ real farmer/hands/basket slots) | Healthy crops. / Better possibilities for farmers. |
| 08 | ReturnToSeed | 0:35–0:40 | Tomato sliced by light → cross-section → dive into one seed → it floats alone | (none) |
| 09 | FinalReveal | 0:40–0:45 | Seed → point of light → hairline → wordmark rises, brand line descends; 2 s hold; fade | PREMIUM SEEDS · Better seed starts with the breeder. · Bengaluru · India |

Change a scene's length by editing its `duration` (and the following `from`
values); scenes use scene-local frames, so their internals follow.

## Project structure

```
premium-seeds-film/
  public/
    assets/           drop-in photos, clips, logo, music (slot-named)
    fonts/            OFL font files + licences
    audio/generated/  score + SFX stems (generated, git-ignored)
  scripts/
    scan-assets.mjs           detects filled slots → src/assets/available.generated.ts
    audio/dsp.mjs             tiny offline synth/DSP kit (no deps)
    audio/generate-soundtrack.mjs   the score + sound design timeline
    extract-brand.mjs         pulls colours/fonts/images from the website
    render-stills.mjs         batch review stills
  src/
    Root.tsx                  compositions (16:9, 9:16, 4:5, guide, per-scene)
    compositions/PremiumSeedsFilm.tsx, AssetGuide.tsx
    scenes/                   OpeningSeed … FinalReveal (one file per scene)
    components/               AnimatedText, CinematicImage, ImageReveal, CropMorph,
                              LogoReveal, Seed, Atmosphere (grain, vignette,
                              particles, bokeh, light leak), Soundtrack
    visuals/                  procedural geometry: seedling, leaf, field, crops, macro chilli
    content/copy.ts           all on-screen text
    styles/                   brand colours, fonts, type styles
    assets/                   slot definitions + detection
    utils/                    timeline, easing, layout, geometry, scene clock
```

## Assets you need to supply

In order of impact:

1. **Official logo** (SVG preferred, light-on-dark version) → `public/assets/logo.svg`
2. **Brand colours and fonts** from the website → run `npm run extract-brand`
3. **Top Gun F1 product image** (website) → `public/assets/topgun-product.png`
4. **Real farmer / field photography or footage** (with consent) →
   `harvest-farmer`, `harvest-hands`, `harvest-basket`, `field-wide`
5. **Breeder or R&D facility photo/clip** → `research-breeder`
6. **Eight crop close-ups** → `crop-*` (all eight, or none)
7. **Licensed music** (optional; the generated score is usable as-is) → `music.mp3`

Please don't substitute stock photos of people or labs presented as Premium
Seeds staff or facilities.

## Notes

- Fonts: Fraunces, Inter and IBM Plex Mono are SIL Open Font License, and the
  licences sit next to the files.
- The soundtrack is synthesised by `scripts/audio/` and is original, with no
  samples, so it is free of third-party licensing.
- Remotion is free for individuals and small companies; larger companies
  need a [Remotion company licence](https://www.remotion.dev/license).
