# J-WALT brand film

A 30-second brand film for J-WALT (INTERIORS | MEP | CONTRACTING), generated entirely in
code: HTML Canvas + JavaScript for the picture, Playwright/Chromium to render frames,
FFmpeg to encode, and Python for asset analysis and QA. It uses only real J-WALT project
photography from the supplied source pack. No AI video or image generation and no editing
suite are involved.

**Current state:** Phase 1 (direction). See [PHASE1.md](PHASE1.md) for the beat map, shot
list, transition map, visual system and open questions, and `output/keyframes/` for the four
keyframe stills (awaiting approval). The full video is not rendered yet.

## Layout

```
index.html              the film page (canvas); add ?preview for a scrubber in a browser
src/engine/             deterministic core: math/easing, camera, drawing primitives
src/film/               theme (grid, type, colour), asset manifest, scenes, timeline
assets/portfolio/       photos cropped from the source pack + registered line drawings
assets/logo/            vectorised J-WALT wordmark (svg + json path data)
assets/fonts/           Inter Tight (SIL OFL 1.1, see OFL.txt)
analysis/               extraction, logo vectorisation, line registration, QA, catalogue
render/                 static server + still renderer (video renderer comes in Phase 2)
output/keyframes/       rendered keyframes
```

## Running

Requirements: Node 18+, Python 3.10+, Chromium via Playwright.

```
npm install                                   # playwright (browsers are provided separately)
pip install pymupdf pillow numpy potracer imageio-ffmpeg

# re-extract assets from the source pack (only needed if the pack changes)
python analysis/extract_assets.py /path/to/J-WALT-Brand-Film-Source-Pack.pdf
python analysis/contact_sheet.py
python analysis/vectorize_logo.py
python analysis/snap_lines.py heid-reception

# render the Phase 1 keyframes, or any timecodes
node render/stills.js
node render/stills.js 2.5 13.62               # -> render/frames/

# QA
python analysis/qa_frames.py output/keyframes/*.png

# interactive preview
npm run serve                                 # then open http://localhost:8123/?preview
```

## Rules the code enforces

- `film.seek(t)` is a pure function of time: no clock, no hidden state, no unseeded randomness.
- The camera never rotates or scales non-uniformly, and a photo always covers its plate.
  Each photo has a "safe view" that the camera can't leave.
- Photos are never enlarged beyond 1.25× their source pixels; every frame reports this.
- Type is rendered with greyscale antialiasing (no LCD colour fringing).
- Every fact on screen is quoted from the source pack; see `analysis/catalogue.md`.
