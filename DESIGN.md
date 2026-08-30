# Design

Recorded from the built world in `index.html`, not from intention. Where this file and the
code disagree, the code is right and this file is stale.

## World

**An Admiralty nautical chart**, not an intelligence dashboard. The category default —
dark console, cyan accents, glass panels — is the explicit anti-reference.

The chart world was chosen because it carries the product's central distinction for free.
On a real chart, surveyed fact and advisory inference are printed in different inks. Here
the same rule does the work: **teal is measured, amber is inferred**. That is why the slick
has a hard delineated boundary and the origin region is stippled, dashed and soft-edged —
the shapes state their own epistemic status before anyone reads a word.

## Colour

| Token | Value | Role |
|---|---|---|
| `--paper` | `#F6F4EE` | Ground. Every panel. |
| `--vellum` | `#EDE9DE` | Recessed ground: meter tracks, thumbnail mat, hover. |
| `--ink` | `#0A1F33` | All linework and primary text. Buttons. |
| `--teal` | `#1FB8A6` | **Areas only** — the slick fill. Never text. |
| `--amber` | `#E8983A` | **Areas only** — origin stipple and glow. Never text. |
| `--teal-ink` | `#0E7A6E` | Every teal *mark*: numerals, meters, badges, tracks. 4.74:1 |
| `--amber-ink` | `#9A5B12` | Every amber *mark*, and caution headings. 4.87:1 |
| `--slate` | `#5C6B78` | Secondary text, weak-band marks. 4.99:1 |
| `--rule` | `#C9C3B4` | Panel divisions, splitters, meter borders. |
| `--rule-soft` | `#DCD7C9` | Hairlines inside a panel. |

**The area/mark split is load-bearing.** Brand teal and amber are vivid enough for large
filled regions on a map but fail text contrast badly (2.13–2.27:1 on paper). Their darker
siblings carry every small mark. Keeping both also separates the moderate-band tracks from
the origin region they cross, which otherwise share a hue at projector distance.

Score bands: `>=70` teal · `40–69` amber · `<40` slate. Band meaning is carried
independently by rank number, numeral and verdict word, so nothing depends on colour alone.

## Type

Three faces, self-hosted as woff2 in `lib/fonts/`. No CDN.

- **Space Grotesk** — wordmark, panel headings, vessel names, score numerals.
- **IBM Plex Sans** — body, explanations, UI chrome (section headings, disclosure, caution).
- **IBM Plex Mono** — data and evidence only: timestamps, coordinates, IDs, factor labels,
  scores against their maxima, map notes. **Mono means measurement**; when it spreads to
  chrome it stops meaning anything.

Steps in use: 10.5 / 11.5 (mono micro) · 13–13.5 (body) · 15 (panel heading, vessel name) ·
19 (wordmark) · 24 (score numeral). Tabular numerals globally.

## Chart apparatus

Every device below is functional, not ornament:

- **Minute-ticked double border** on the map panel (`.chart-frame`), drawn as repeating
  gradients on the four edges with an inner rule at `inset:11px`.
- **Graticule** at 0.1°, drawn from real coordinates in `drawGraticule()` into its own
  `grid` pane. Survives teardown; it belongs to the chart, not the reveal.
- **Source & reliability block** — the scene thumbnail matted in a ruled plate, sensor
  caption, survey zone, and the layer legend (Surveyed / Inferred / Reported).
- **Boxed CAUTION note** in amber, carrying the "leads, not liability" framing.
- **Ruled measures** — every score bar is graduated into tenths, so a number reads against
  a scale rather than a bare progress fill.
- **Numbered position fixes** — small ruled circles at each track's end, keyed to the list.
- Scale bar, north arrow, and fully restyled Leaflet zoom/attribution.

## Map layer language

| Layer | Treatment | Says |
|---|---|---|
| Scene plate | Warm raster at 0.72 opacity | This is the acquisition footprint |
| Spill mask | Solid `#12897C` 1.6px stroke, teal fill 0.2 | Measured, delineated |
| Origin region | Dashed `2 4`, SVG `<pattern>` stipple, blurred glow beneath | Inferred, approximate |
| Tracks | Weight `1.2 + score/100 * 2.6`, opacity `0.5 + score/100 * 0.5` | Reported; rank readable from the map alone |

Track weight and opacity derive from **score**, never rank index — a 1-point gap and a
60-point gap must not look the same.

## Components

- `.cand` — a candidate row. Rank earns apparatus, not a coloured slab: the lead row takes
  a faint teal ground wash, an open row takes a full 1px ink border. **No offset shadows,
  no accent border-left** — a paper chart has no lifted edges.
- `.fold` — the factor breakdown, a `grid-template-rows: 0fr → 1fr` disclosure. Collapses
  to 0px. Never use Tailwind's `.block` on it; that utility beats `display:grid` and the
  fold silently stops closing.
- `.measure` — the graduated bar. Track `--vellum` with a 1px `--rule` border, tenths drawn
  by a `repeating-linear-gradient` overlay.
- `.splitter` — draggable panel divider. Pointer drag, double-click to reset, arrow keys
  (Shift for coarse), Home to reset. Width persists to `localStorage` under `oceaniq.rails`.
  Rails clamp to 190–520 (left) and 250–640 (right); the expand toggle collapses both to 0.

## Motion

One authored moment: the staged reveal in `run()`. Scene fade → the spill stroke draws
itself via `strokeDashoffset` → stippled origin with its release note → tracks trace on a
190ms stagger with head dots riding each stroke → ranked column staggers in and meters fill.

Anime.js owns SVG stroke work; Motion owns sequencing, stagger and meters. Everything is
guarded by a run token so a re-run cancels the previous one cleanly. Easing is exponential
ease-out (`[.16,1,.3,1]`) from an already-visible default. `prefers-reduced-motion` collapses
all of it.

**Never animate `width`/`height`** — the rails snap. Layout animation thrashes and the
detector is right about it.

## Browser surfaces

Themed, not left to the browser: `::selection`, `caret-color`, `:focus-visible` (2px teal,
2px offset), scrollbar thumb and track, tabular numerals, and full restyles of Leaflet's
zoom control, scale bar and attribution.

## Known open

- The minute-tick border is a fixed 13px screen pitch and carries no position; it does not
  derive from the map bounds and the border figures are unlabelled. The graticule inside is
  real; the border is currently trim.
- No soundings, isobaths, depth tint or graduated compass rose — the world's own devices
  that would carry it further than border trim does.
