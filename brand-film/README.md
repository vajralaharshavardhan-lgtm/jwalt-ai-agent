# J-WALT — "From Vision to Reality" (brand film)

A 35-second cinematic brand film for J-WALT, built as an editable,
fully reproducible project: every frame and every sound is generated from
the code and settings in this folder. It renders a 16:9 master plus native
9:16 and 1:1 cuts.

> **Status: draft for review.** Read "Before this goes public" first.

```
VISION ─ DESIGN ─ CRAFT ─ ENGINEERING ─ EXECUTION ─ TRANSFORMATION ─ HERO ─ BRAND
0.0      3.6      8.0     12.0          16.0        21.5             27.5   32.0 → 35.0
```

| Time | Shot | What happens |
|---|---|---|
| 0.0–3.6 | `s01_vision` | Black. One precise line, then the floor plan draws itself and lights up. **VISION**. The walls start to rise out of the drawing. |
| 3.6–8.0 | `s02_design` | One unbroken camera move from the drawing board down to eye level. The wireframe grows into white "clay" forms from the floor up. Materials sweep toward camera, then the cove, wall-washers and niche light up. **DESIGN** |
| 8.0–12.0 | `s03_craft` | Three macro studies: reeded oak in raking light, travertine niche and bronze reveal, the coffer cove lighting circuit by circuit. **CRAFT** |
| 12.0–16.0 | `s04_engineering` | Exploded axonometric of the fit-out systems as translucent technical layers: floor finishes, walls/partitions/joinery, ceilings/lighting, MEP services. **ENGINEERING** |
| 16.0–21.5 | `s05_execution` | Four match-cut studies of the space being built: studs → boards → reeded panels pressed home; open services → finished ceiling and a downlight on; screed → stone tiles set in a wave; a glass panel sliding home. **EXECUTION** |
| 21.5–27.5 | `s06_transformation` | One continuous dolly while the raw site completes around the camera. Elements arrive with small physical motions, site equipment leaves, and work lights give way to architectural light. |
| 27.5–32.0 | `s07_hero` | The finished space in low western sun. No text. |
| 32.0–35.0 | `s08_brand` | Evening falls, the architectural light remains. The opening line returns and resolves into the J-WALT mark, services and website. |

## Before this goes public

This environment's network policy blocked both the J-WALT website supplied
for this brief (`zingy-arithmetic-e9bb1d.netlify.app`) and `j-walt.com`, and
the reference video did not come through. So:

1. **The logo is a typeset placeholder, not the J-WALT logo.** Drop the real
   file at `assets/brand/logo.svg` (preferred) or `assets/brand/logo.png` and
   re-render. It is placed as supplied, never redrawn or distorted.
2. **Colours and typography are placeholders.** An architectural palette
   (warm black, warm white, champagne accent) and two OFL fonts (Jost and
   Manrope) stand in until the site's brand colours and fonts can be read.
   Change them in `film.yaml` (`palette`, `typography`).
3. **The space is illustrative CGI, not a J-WALT project.** The film never
   names, captions or claims it as one. To use real J-WALT work, point any
   shot at a real photo or video (see "Replacing a shot with real footage").
4. **Copy on screen** is limited to chapter words, the services line
   (`INTERIOR DESIGN · FIT-OUT · MEP · JOINERY`) and `j-walt.com`. These
   come from J-WALT's public pages as surfaced by web search (links under
   Sources). No clients, awards, statistics or claims appear. Search results
   also attribute the line "Making spaces lively, beautiful and functional"
   to J-WALT. It was not verified on the site, so it is not used. Add it to
   `brand` in `film.yaml` if confirmed.

## How it is made

Real-time or AI video generation would make the architecture wobble.
Brute-force path tracing was measured at ~3.5 min per 1080p frame on the
available 4-core CPU, far too slow for 840 frames × 3 formats. The film
uses a production technique from high-end VFX instead: **render once,
project many**.

```
              ┌──────────────── one parametric 3D model (Blender, jfilm/scene) ───────────────┐
              │ shell · MEP · framing · boards · finishes · furniture · site · lights (groups) │
              └───────┬───────────────────────────────┬───────────────────────────────────────┘
      converged Cycles stills per shot            per-frame visibility buffer
      (light-group passes, depth, ids,            (Workbench: object id + depth, 2× supersampled,
       normals; OIDN denoised)                     ~1 s at 4K)
              └──────────────┬────────────────────────┘
          projection compositor (jfilm/render/project.py): every pixel is traced back to
          the world point it sees and looked up in the stills that saw it (id + depth +
          normal agreement) → exact parallax, moving objects, relighting by light-group mix
                             │
          lens: layered DOF, shutter motion blur → Blender AgX (OCIO) → vector graphics
          (skia: plan, wireframe, typography) → grade, halation, CA, vignette, grain
                             │
          ffmpeg: ProRes 422 HQ master + H.264 for every format, muxed with the soundtrack
```

Consequences worth knowing:

- **Architecture cannot morph.** Every frame comes from the same geometry.
  Walls, windows and furniture are identical in every shot and every stage.
- **No render noise or flicker.** Each shot is lit by a few converged stills,
  not by independently noisy frames.
- **Light is additive.** Each still stores the sun/sky, cove (4 circuits),
  wall-washers, niche, meeting-room and work lights separately. Lights
  turning on, sequencing or giving way to evening are exact mixes.
- **Limits.** Reflections are baked from the projector viewpoints, so camera
  moves are kept slow and deliberate, as the brief asks. Very thin
  occluders (facade fins) are the hardest case; each moving shot therefore
  uses two projectors (start and end of the move).

## Sound

Everything is synthesised in `jfilm/audio`. There are no sample libraries,
so there is nothing to license.

- `sfx.py`: precise clicks, metal/glass modal resonances, stone taps, servo
  glides, air and sub impacts. Each cue lands on a picture event declared by
  the shot (`Shot.cues()`), so re-timing a shot re-times its sound.
- `score.py`: a low D drone, a slow pad, a felt-piano motif, a precise pulse
  and glass arpeggios for the build. D minor lifts to D major at the hero
  reveal, with a final low impact and shimmer on the logo.
- `mix.py`: an intensity arc, bus EQ and compression, loudness to
  **-14 LUFS**, true-peak **-1 dBTP**. Stems are written separately
  (`output/audio/stem_music.wav`, `stem_sfx.wav`, `stem_ambience.wav`).

## Project layout

```
film.yaml                 timing, formats, copy, palette, typography, render + audio targets
render.py                 CLI (below)
jfilm/config.py           loads film.yaml, project paths
jfilm/camera.py           the single camera model used by Blender, compositor and graphics
jfilm/easing.py           motion vocabulary (architectural / typographic curves)
jfilm/scene/              dims.py (key dimensions) · room.py (model) · materials.py (procedural PBR)
                          lights.py (light groups) · linework.py (edges for the wireframe)
jfilm/shots/              one module per shot + _opening.py (shared S01/S02 move) + base.py (interface)
jfilm/render/             stills.py · blender.py · project.py · frame.py · post.py · exr.py · footage.py
jfilm/graphics/           canvas.py (skia) · plan.py (the drawing) · titles.py (chapter titles)
jfilm/audio/              dsp.py · sfx.py · score.py · mix.py
jfilm/encode.py           deliverables
assets/fonts/             Jost, Manrope (SIL OFL 1.1, licences included)
assets/brand/             put the real logo here (logo.svg / logo.png)
output/                   renders (not committed)
```

## Rendering

Requirements: Python 3.11 and `pip install -r requirements.txt` (includes
Blender as a Python module, `bpy`). Also `ffmpeg`, plus Mesa/EGL on
headless Linux for the Workbench visibility pass.

```bash
python render.py linework                      # model edges for the vector layer
python render.py stills --preview              # quick stills (half res, 12 spp)
python render.py frames -f 16x9 --preview      # half-res animatic frames
python render.py audio                         # soundtrack + stems
python render.py encode -f 16x9 --preview      # → output/masters/*_preview.mp4

python render.py stills                        # final stills (cached by content hash)
python render.py frames -f all --workers 3     # 16x9, 9x16, 1x1
python render.py encode -f all                 # ProRes master + H.264 deliverables
```

Stills are cached by a hash of their spec. Changing one shot re-renders
only that shot's stills. Bump `SCENE_VERSION` in `jfilm/render/stills.py`
after editing geometry, materials or lights.

## Revising

- **Timing.** Change a shot's `start` / `end` in `film.yaml`. Internal beats
  live as named constants at the top of each shot module.
- **Copy.** Edit `brand` in `film.yaml` for the name, services and website.
  Chapter words are the `title` of each shot.
- **Look.** Edit `palette` and `typography` in `film.yaml`; grain,
  halation and vignette live under `render`. Per-shot lens and grade
  tweaks go in `Shot.post()`.
- **Camera.** Each shot's `cam(t)` is a `CamPath` of keyframes. Vertical
  and square reframes are set in `reframe` (yaw, pitch, roll, fov) and can
  be functions of time.
- **Sound.** Cues are declared next to the picture they belong to
  (`Shot.cues()`). Mix levels live in `jfilm/audio/mix.py`.

### Replacing a shot with real footage

Add an override to `film.yaml`. The shot keeps its titles, grade and grain:

```yaml
overrides:
  s07_hero:
    footage: assets/projects/finished-lounge.jpg   # photo, or .mp4/.mov clip
    from: [0.00, 0.00, 1.00, 1.00]                 # crop window at shot start (x, y, w, h)
    to:   [0.04, 0.03, 0.92, 0.92]                 # crop window at shot end → slow push-in
```

## Sources

- Services and domain: J-WALT public pages as indexed by web search, e.g.
  [Services](https://j-walt.com/services/),
  [Premium Interior Fit Out in Dubai](https://www.j-walt.com/interior-fit-out-services-dubai/),
  [Interior Design, MEP, Fit Out](https://www.j-walt.com/interior-design-fitout-services/),
  [About](https://j-walt.com/about-us/). These pages could not be opened
  from the build environment, so they were not read directly.
- Fonts: [Jost](https://github.com/indestructible-type/Jost) and
  [Manrope](https://github.com/googlefonts/manrope), SIL Open Font License 1.1.
- Everything else (geometry, materials, lighting, music, sound) is
  original to this project.
