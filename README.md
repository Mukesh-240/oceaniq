# OceanIQ — Reconstruct Incident

Single-page oil-spill attribution console. Static HTML/CSS/JS, no build step, no backend,
no runtime network calls except map tiles.

## Run it

Double-click **`serve.bat`** (or `python -m http.server 8000` in this folder) and open
<http://localhost:8000/index.html>.

Opening `index.html` straight off the filesystem works too, but browsers block `fetch()`
on `file://`, so the page shows a **DATA SOURCE UNREACHABLE** note with a *Load JSON
manually* file picker as an escape hatch. Serving over HTTP is the intended path.

## Files

| Path | What it is |
|---|---|
| `index.html` | The whole app — markup, styles, reveal controller |
| `mock-data.json` | The data contract (swap this for real pipeline output) |
| `assets/sar-scene.svg` | Synthetic SAR scene used as `satellite_image_url` |
| `PRODUCT.md` | Confirmed product truth: users, purpose, constraints, principles |
| `lib/leaflet.js` `lib/leaflet.css` | Leaflet 1.9.4 — map |
| `lib/anime.min.js` | Anime.js 3.2.2 — SVG stroke draw-in for the slick and tracks |
| `lib/motion.js` | Motion 11.11.17 — staged sequencing, stagger, meters |
| `lib/tailwind.js` | Tailwind Play CDN 3.4.16, self-hosted |
| `lib/fonts.css` `lib/fonts/` | Space Grotesk + IBM Plex Sans + IBM Plex Mono, self-hosted woff2 |
| `serve.bat` | Starts a local static server and opens the page |

Everything is self-hosted, fonts included, so the demo survives venue wifi. The only
runtime network request is the Esri World Light Gray basemap (`initMap()` in
`index.html`); point that `L.tileLayer` at a local tile folder for a fully offline demo.

## Swapping in real data

Change **one line** near the top of the app script:

```js
const DATA_SOURCE = 'mock-data.json';   // -> 'https://api.example.org/incident/42'
```

Nothing else reads the data source.

### Data contract

```jsonc
{
  "satellite_image_url": "string",
  "spill_mask":    { "type": "Polygon", "coordinates": [[[lon, lat], ...]] },
  "origin_region": {
    "polygon":     { "type": "Polygon", "coordinates": [[[lon, lat], ...]] },
    "time_window": { "start": "ISO8601", "end": "ISO8601" }
  },
  "candidate_ships": [
    {
      "id": "string",
      "name": "string",
      "track": { "type": "LineString", "coordinates": [[lon, lat], ...] },
      "score": 0-100,
      "factors": [                       // exactly 5
        { "label": "string", "score": 0, "max": 25, "explanation": "string" }
      ]
    }
  ]
}
```

Coordinates are GeoJSON order (`[lon, lat]`); the app flips them for Leaflet in `toLatLngs()`.

**The factor model is weighted and the total is the literal sum of its parts:**

| Factor | Max |
|---|---|
| Proximity to origin | 25 |
| Temporal compatibility | 25 |
| Trajectory compatibility | 20 |
| Drift consistency | 20 |
| AIS/SAR discrepancy | 10 |

`max` is optional per factor and the bar falls back to treating `score` as a percentage if
it is absent — but **the pipeline should emit it**, because "86 = 23+22+18+16+7" is the
explainability story, and a bare 0-100 score throws it away.

Ships are sorted by `score` client-side, so the pipeline need not pre-rank them. Rank
colour, the `#1` treatment, and track weight all follow from that sort.

**Optional blocks** the mock file also carries. All are additive — a payload with only the
contract above still renders:

- `incident` — `{ case_id, basin, detected_at, area_km2, confidence, chart_datum, survey_note }`
  drives the left case rail. Missing fields render as `·`.
- `scene` — `{ id, sensor, acquired, bounds, center, zoom }` for the header readout and the
  image-overlay footprint. If omitted, `sceneOf()` derives bounds from the spill mask.
- `flag`, `type` on each ship — shown in the card subtitle.

## The flow

`RECONSTRUCT INCIDENT` runs a cancellable async sequence (`run()`):

1. **Scene** — the acquisition plate fades in over the chart. A missing or broken raster is
   removed silently rather than showing a broken image.
2. **Slick** — the spill polygon's stroke draws itself (Anime.js `strokeDashoffset`), then
   the teal fill blooms.
3. **Origin** — the inferred region fades in stippled and soft-edged, with its modelled
   release window as a chart note beside it.
4. **Tracks** — each candidate track traces on in a staggered volley, a head dot riding the
   stroke, then drops a numbered position circle keyed to the list.
5. **Ranking** — the candidate column staggers in and the score meters fill.
6. **Dossier** — clicking a card (or its track on the map) expands five scored factors, each
   with its own measure and explanation directly beneath it.

The same button re-runs the whole sequence; each step checks a run token, so a re-run
mid-flight cancels the old one cleanly. `Space` runs it, `Esc` closes an open dossier.
Hovering a card highlights its track and marker, and hovering a track does the reverse.

## Design notes

The visual world is an **Admiralty nautical chart**, chosen so the interface carries the
product's central distinction for free: on a real chart, surveyed fact and advisory
inference are printed in different inks. Here **teal is measured** (the delineated slick,
high scores) and **amber is inferred** (the back-projected origin region, caution-band
scores), with slate for weak evidence. That is why the origin region is stippled and
soft-edged while the slick has a hard delineated boundary — the shapes state their own
epistemic status before you read a word.

Supporting chart apparatus: minute-ticked double borders on the map panel, a graticule at
0.1° drawn from real coordinates, a source-and-reliability block in the case rail, a boxed
CAUTION note, a scale bar, and score meters ruled into tenths so every number reads against
a graduated scale rather than a bare progress bar.

Tokens live in the `tailwind.config` block and the `:root` custom properties at the top of
`index.html`. Map-layer inks are in `INK` / `band()` in the script.

## Honest limitations

- **All data is synthetic.** Vessels, IMO numbers, tracks, scores, factor explanations, and
  the SAR scene are invented. No real incident or vessel is depicted, and the page says so
  in the case rail. Do not present it as real data.
- The IMO numbers are plausible-format but arbitrary; one could coincidentally match a real
  vessel.
- Attribution is framed throughout as an investigative lead, never a finding of liability.
