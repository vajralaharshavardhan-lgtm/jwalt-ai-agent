# J-WALT brand film: production record

**Master:** `output/j-walt-brand-film.mp4`. H.264 High, 1920×1080, 60 fps (1,800 frames,
30.000 s), yuv420p, BT.709 limited range, CRF 12 / preset slow, AAC 320 kb/s 48 kHz stereo,
`+faststart`, 16.6 MB.

This supersedes the Phase 1 plan (`PHASE1.md`) wherever the two differ. The differences
come from the client rulings below and from three rounds of review.

## Client rulings applied

| Ruling | How it is applied |
|---|---|
| No "700,000+" without a verified label | Not used. Only 310+ HAPPY CLIENTS and 500+ COMPLETED PROJECTS appear (p3). |
| No Retail / Residential / F&B | No sectors appear. |
| "MEP" as the label | "MEP" is used verbatim. |
| Exact Corys wording from the source | **CORYS**, the wordmark on p9–10, which is also the name in the page text. "Piping Systems" and "+GF+" are not used. |
| MEP never over a photograph | **All three** service titles form a standalone schedule on paper (12–16 s), attached to no photo. |
| Weaker Wilhelmsen images out of hero moments | Wilhelmsen images are not used at all. |
| Keep the rebuilt vector logo | Kept (IoU 0.984 against p1). |
| No invented or inferred facts | Every fact is quoted in the table below. "CARPENTRY & JOINERY" is placed only over SNOC, whose source text describes its custom-built joinery (p11). |

## Final edit (120 BPM; beat = 0.5 s, bar = 2 s)

| Time (s) | Section | Picture | Type | Sound |
|---|---|---|---|---|
| 0.0–4.0 | Idea | Red datum mark; a line is drawn; the Heidelberg reception draws itself in construction lines registered to the real photo | FROM AN IDEA | tick, graphite drag, pad on 2.0, pencil ticks, air rising into 4.0 |
| 4.0–7.5 | Space | Photo unfolds from the wall's corner line under the drawing; drawing ghosts out; 3.5% push | HEIDELBERG · DUBAI PRODUCTION CITY · 5,600 SQ FT · 70 DAYS | felt impact at 4.0, half-time pulse, pluck motif |
| 7.5–12.2 | Craft | SNOC boardroom slides over the reception in the same window (parallax push); shelving plate built up from its base line; plate closes to its edge | CARPENTRY & JOINERY · PROJECT SNOC · SHARJAH · 2,500 SQ FT · 50 DAYS | air on the cover; warmer chord |
| 12.2–15.8 | Services | The closing edge travels and becomes the schedule's spine; rules draw on the beat, with scale ticks | SERVICES · 01 MEP · 02 CIVIL WORKS · 03 TURN KEY INTERIOR FIT OUT SOLUTIONS | quarter-note pulse, rule ticks, off-beat hats |
| 15.8–18.1 | Corys | Spine becomes the seam; plate opens both ways from it; closes vertically into the horizon rule | CORYS · DUBAI INVESTMENT PARK · 25,000 SQ FT · 80 DAYS | — |
| 18.0–20.0 | OMODA \| JAECOO | Plate opens from the same horizon line; drift along the desk; closes down into its base line | OMODA \| JAECOO · DUBAI MARINA · 3,500 SQ FT · 60 DAYS | — |
| 20.0–22.1 | Gallery | Base line widens into a ground line; three Heidelberg plates built up on it, then taken down | — | three wood knocks |
| 22.1–25.5 | Scale | Grid returns; each numeral on a rule with its label at the rule's end | 310+ HAPPY CLIENTS → 500+ COMPLETED PROJECTS | break: pulse drops out |
| 25.5–30.0 | Brand | Rule travels to centre; wordmark rises out of it; descriptor, tagline; still from 28.35 | J-WALT · INTERIORS \| MEP \| CONTRACTING · REDEFINING SPACES | rising air, mallet chord at 26.5, silence by 29.8 |

## Facts on screen and their sources

| On screen | Source |
|---|---|
| HEIDELBERG · DUBAI PRODUCTION CITY · 5,600 SQ FT · 70 DAYS | p5 ("SQF: 5600", "Project Duration: 70 Days") |
| SNOC · SHARJAH · 2,500 SQ FT · 50 DAYS | p11 |
| CORYS · DUBAI INVESTMENT PARK · 25,000 SQ FT · 80 DAYS | p9 (location shortened from "Plot no. 598-1105 Dubai Investment Park") |
| OMODA \| JAECOO · DUBAI MARINA · 3,500 SQ FT · 60 DAYS | p14 |
| 310+ HAPPY CLIENTS · 500+ COMPLETED PROJECTS | p3 |
| MEP · CIVIL WORKS · TURN KEY INTERIOR FIT OUT SOLUTIONS · CARPENTRY & JOINERY | p3 ("Carpentry and Joinery Work"; the "&" short form is the brief's) |
| INTERIORS \| MEP \| CONTRACTING · REDEFINING SPACES | p1 |

## Review iterations (what was wrong and what changed)

1. **First assembly (frames):**
   - The Heidelberg → craft move left an 830 px paper gap between two sliding plates, which read as a slideshow. It became a cover-with-parallax inside one window.
   - The services exit left a stray tick at the spine. The exits were re-timed.
   - The statistics read like a slide. Each is now one composed line: numeral, rule, label.
   - Service type went from 48 to 56 px.
2. **Render v1:**
   - QA flagged a stutter at 14.0 s. Diagnosis: canvas text snaps to whole pixels, so slowly settling type moved only on alternate frames. All moving type now draws from pre-rasterised greyscale sprites at sub-pixel positions, and settled type snaps to the pixel grid. Measured per-frame motion now decays smoothly.
   - Two ~0.5 s "lone line" dead spots (12.3 s, 15.7 s) were overlapped with their neighbouring moves.
   - The cover slide was lengthened from 0.8 to 1.0 s (peak change per frame 10.1 → 8.8).
   - The sound cues were re-timed to match.
3. **Render v2:**
   - A tick sat 12 px from the spine and looked like an error. Removed.
   - The returning grid was still half-drawn behind the first numeral. It now completes first.
4. **Mix:** the reveal impact and logo chord peaked about 10 dB above the body, which is the "cinematic boom" the brief rules out. They were pulled down 4–6 dB, the pulse shortened, and the intro pad raised.

## Final QA (`analysis/qa_video.py`, `analysis/qa_frames.py`)

- **Video:** 1,800 frames, 60 fps, BT.709 tv range. No black frames, single-frame flashes, frame jumps or stutter. Largest frame-to-frame change is 8.8/255 (8.05 s, the cover slide).
- **Audio:** −16.8 LUFS integrated, −1.18 dBTP true peak, no clipped samples. Audio length 30.016 s against 30.000 s of picture (standard AAC priming).
- **Photographs:** maximum enlargement 1.215× (OMODA), logged for every frame in `output/j-walt-brand-film.frames.json`. No photo is rotated or non-uniformly scaled.
- **Keyframes:** type inside 5% action-safe, no colour fringing, logo edge transition 0.86 px.

## Known limitations

- **The sound was verified only by measurement.** I checked loudness, peaks, a spectrogram and cue timing against the picture, but this environment cannot play audio, so nobody has listened to it yet. The score is original and synthesised in code (pad, felt pulse, pluck motif, mallet chord, air and ticks). It is restrained and on the beat, but it will not match a professionally produced track. The picture is cut on a 120 BPM grid, so a licensed 120 BPM track can replace it (`node render/video.js --audio track.wav`).
- **Photos are capped at about 1,100 px** because they come from slide rasters. That's why the film is laid out as editorial plates rather than full-bleed frames. Original photos would allow a full-frame version.
- **Brand red is sampled** (`#BE1B20`) and the logo is a reconstruction. Replace both with official assets when available.

## Reproduce

```
python audio/score.py                          # -> output/score.wav
FFMPEG=/path/to/ffmpeg node render/video.js    # -> output/j-walt-brand-film.mp4 (~100 s on 4 cores)
FFMPEG=/path/to/ffmpeg python analysis/qa_video.py output/j-walt-brand-film.mp4 sheet.jpg
```
