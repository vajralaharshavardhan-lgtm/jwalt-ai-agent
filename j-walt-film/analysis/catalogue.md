# Asset catalogue — J-WALT-Brand-Film-Source-Pack.pdf

**Source inspected:** `J-WALT-Brand-Film-Source-Pack.pdf`, all 21 pages. Each page is one
flattened 2000×1125 JPEG slide (no text layer), so everything below was read visually and
every photo is a crop out of a slide raster, not an original camera file.

**Not available:** `J-WALT-Brand-Film-Source-Notes.txt` was not present in this session.
The original 116-page portfolio was not inspected.

Crops: `assets/portfolio/<id>.jpg` (made by `analysis/extract_assets.py`). Contact sheet:
`analysis/contact/contact_sheet.jpg`. *Sharpness* = variance of the Laplacian at a common
800px height (higher = crisper; Heidelberg ≈ 450–1100, soft phone/HDR images ≈ 40–200).

## Page map

| Page | Content | Used for |
|---|---|---|
| 1 | J-WALT logo lockup: wordmark, `INTERIORS\|MEP\|CONTRACTING`, script "Redefining Spaces.", contact details | Wordmark vectorised → `assets/logo/jwalt-wordmark.svg`; red sampled |
| 2 | "About us" text + unattributed office photo | Wording reference only |
| 3 | "Our services" graphic + "Milestones" (310+, 500+, 700,000+) | Service terms, statistics |
| 4 | "The process" (Consult and Define / Design and Approvals / Execute & Complete) + "Authority Approvals" logos | Process terms (authority logos are third-party marks — not used) |
| 5–8 | Heidelberg — 70 days, 5,600 SQF, Dubai Production City | Primary photography |
| 9–10 | +GF+ / CORYS — 80 days, 25,000 SQF, Plot no. 598-1105 Dubai Investment Park | Photography |
| 11–13 | SNOC — 50 days, 2,500 SQF, Sharjah (11–12 renders, 13 built photos) | Photography (p13 only) |
| 14–16 | OMODA \| JAECOO — 60 days, 3,500 SQF, Dubai Marina | Photography |
| 17–18 | Wilhelmsen — 40 days, 4,500 SQF, Fujairah (17 render, 18 photos) | Held (see below) |
| 19 | Divider: "Warehouse — Completed Projects" | — |
| 20 | Heidelberg company history (text) | Not used (client history, not J-WALT work) |
| 21 | Heidelberg — 12,647 SQF, 4 months, Dubai Production City (three hall photos) | Photography |

## Every extracted image

Class: **P** = real completed-project photography · **P\*** = real but heavily processed
(phone HDR / upscaling artefacts) · **R** = 3D render (never presented as completed work).

| # | id | Pg | Project | Description | Orientation · px | Class | Conf. | Sharp | Recommended use |
|---|---|---|---|---|---|---|---|---|---|
| 1 | heid-reception | 5 | Heidelberg | Reception: timber panel wall + HEIDELBERG sign, white curved desk, three ring pendants, exposed services | square · 993×983 | P | high | 449 | **PRIMARY** — opening: drawing → space |
| 2 | heid-boardroom | 6 | Heidelberg | Boardroom: vertical timber slat wall, screen, timber table, cove-lit bulkhead | square · 921×917 | P | high | 1084 | **PRIMARY** — craft |
| 3 | heid-teamwork-joinery | 6 | Heidelberg | Long timber cabinet run under a "TEAMWORK" wall graphic | square · 914×916 | P | high | 771 | secondary — cabinetry crop only |
| 4 | heid-corridor-glass | 7 | Heidelberg | One-point corridor: fluted glass, exposed ducts / sprinklers / trays | portrait · 751×937 | P | high | 1035 | **PRIMARY** — build / MEP (box cropped out) |
| 5 | heid-private-office | 7 | Heidelberg | Office: glass desk, lounge, timber credenza, exposed MEP | landscape · 1115×938 | P | high | 997 | secondary — build alternate |
| 6 | heid-curved-glass | 8 | Heidelberg | Curved fluted-glass meeting room | portrait · 760×953 | P | high | 500 | **PRIMARY** — build / fit-out (chair cropped out) |
| 7 | heid-stained-corridor | 8 | Heidelberg | Timber-framed stained-glass inserts, tall timber cabinets, glass room | landscape · 1122×961 | P | high | 1085 | **PRIMARY** — craft (box cropped out) |
| 8 | corys-openplan-a | 9 | Corys | Open plan with staff, exposed services | portrait · 721×902 | P | high | 826 | secondary — scale |
| 9 | corys-glass-a | 9 | Corys | Frameless glass offices | portrait · 556×824 | P | high | 1028 | secondary (small) |
| 10 | corys-glass-b | 10 | Corys | Glass partitions, open plan beyond | square · 936×944 | P | high | 326 | secondary |
| 11 | corys-openplan-b | 10 | Corys | Long perspective: glass offices + workstations | portrait · 882×958 | P | high | 926 | **PRIMARY** — project (logo fragment cropped out) |
| 12 | snoc-boardroom-render | 11 | SNOC | Boardroom render; includes a framed portrait of a real person | landscape · 1387×812 | **R** | high | 58 | **excluded** |
| 13 | snoc-reception-render | 12 | SNOC | Reception render (on-screen OS wallpaper) | square · 1134×1000 | **R** | high | 81 | **excluded** |
| 14 | snoc-boardroom-built | 13 | SNOC | Built boardroom: arched lattice panels, timber cladding, U-table with glass centre | square · 1008×927 | P\* | med-high | 516 | **PRIMARY** — project (leaflet cropped out) |
| 15 | snoc-shelving-built | 13 | SNOC | Built lounge: floating white-framed timber shelving | square · 980×941 | P\* | medium | 59 | secondary — joinery, small size only |
| 16 | omoda-reception | 14 | OMODA \| JAECOO | Wave-form reception desk, backlit sign (festive décor + flags cropped out) | landscape · 1272×889 | P | high | 164 | **PRIMARY** — project (16:9 crop) |
| 17 | omoda-workspace-a | 15 | OMODA \| JAECOO | Workstations, festive décor | square · 971×917 | P\* | medium | 96 | avoid |
| 18 | omoda-workspace-b | 15 | OMODA \| JAECOO | Workstations, ring pendant | square · 896×925 | P | medium | 204 | secondary |
| 19 | omoda-boardroom | 16 | OMODA \| JAECOO | Boardroom with paper lanterns | square · 945×992 | P\* | medium | 127 | avoid |
| 20 | omoda-workspace-c | 16 | OMODA \| JAECOO | Black gloss partition, gold ring pendant | portrait · 868×993 | P\* | medium | 102 | avoid |
| 21 | wilh-reception-render | 17 | Wilhelmsen | Reception render | landscape · 1240×833 | **R** | high | 37 | **excluded** |
| 22 | wilh-openplan-a | 18 | Wilhelmsen | Open plan, black ceiling, glossy floor | landscape · 1198×811 | P\* | med-low | 80 | hold — confirm authenticity |
| 23 | wilh-openplan-b | 18 | Wilhelmsen | Illuminated world-map wall | square · 762×811 | P\* | med-low | 156 | hold |
| 24 | heid2-hall | 21 | Heidelberg (12,647 SQF) | Empty hall: epoxy floor, cove-lit bulkheads | portrait · 703×830 | P | high | 220 | secondary — build / civil works |
| 25 | heid2-window | 21 | Heidelberg (12,647 SQF) | Full-height glazing, parked cars outside | portrait · 616×830 | P | high | 285 | avoid (cars) |
| 26 | heid2-blinds | 21 | Heidelberg (12,647 SQF) | Glazing with blinds, cars | portrait · 570×829 | P | high | 338 | avoid |
| 27 | about-office | 2 | unattributed | Glass-partitioned office | landscape · 1131×752 | P | medium | 224 | avoid (no project attribution) |

## Ranking — strongest 20 candidates

1 heid-reception · 2 heid-boardroom · 3 heid-stained-corridor · 4 heid-corridor-glass ·
5 corys-openplan-b · 6 heid-curved-glass · 7 heid-private-office · 8 snoc-boardroom-built ·
9 omoda-reception · 10 corys-openplan-a · 11 heid2-hall · 12 heid-teamwork-joinery (crop) ·
13 corys-glass-b · 14 corys-glass-a · 15 snoc-shelving-built · 16 omoda-workspace-b ·
17 heid2-window · 18 wilh-openplan-a · 19 omoda-boardroom · 20 about-office

Ranking weighs architectural composition first, then authenticity, then measured image
quality, then how well the frame survives a cinematic crop. Colour was not a criterion.

**Primary (8):** heid-reception, heid-boardroom, heid-stained-corridor, heid-corridor-glass,
heid-curved-glass, corys-openplan-b, omoda-reception, snoc-boardroom-built.

**Secondary (7):** heid2-hall, corys-openplan-a, heid-private-office, heid-teamwork-joinery,
corys-glass-b, snoc-shelving-built, omoda-workspace-b.

## Verified text (quoted from the pack)

- Positioning: `INTERIORS|MEP|CONTRACTING` · tagline: "Redefining Spaces." (p1)
- Services (p3): Design and build · MEP · Refurbishment & Renovation · Turn Key Interior Fit Out
  Solutions · Carpentry and Joinery Work · Civil Works
- Process (p4): Consult and Define · Design and Approvals · Execute & Complete · Authority Approvals
- Milestones (p3): **310+** Happy Clients · **500+** Completed Projects · **700,000+** (no label
  printed — not used, see uncertainties)
- Project facts: Heidelberg 70 Days / 5,600 SQF / Dubai Production City (p5) · Corys 80 Days /
  25,000 SQF / Plot no. 598-1105 Dubai Investment Park (p9) · SNOC 50 Days / 2,500 SQF / Sharjah
  (p11) · OMODA | JAECOO 60 Days / 3,500 SQF / Dubai Marina (p14) · Wilhelmsen 40 Days /
  4,500 SQF / Fujairah (p17) · Heidelberg 12,647 SQF / 4 Months / Dubai Production City (p21)
- SNOC (p11): "Custom-built joinery elements were incorporated across workspaces, meeting
  tables, wall panels, shelving, and storage units"
