# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary:** an Indian Coast Guard / marine pollution-response watch officer working a detected slick. They arrive with one incident and one question — who did this — and need enough visible reasoning to justify escalating to an investigation.

**Secondary (evaluation audience):** SIH hackathon judges watching a five-minute live demo on a projector in a bright room. They are not the design target, but the console must be legible and self-explanatory to a domain-literate stranger with no training.

## Product Purpose

Given a satellite-detected oil slick, reconstruct **where and when** the oil was released, and rank which nearby vessels could be responsible — with the reasoning exposed rather than a black-box score. Success is an officer who can say why a vessel is ranked first, and defend it.

## Positioning

Attribution, not detection. Most tooling stops at "there is a slick here." OceanIQ back-projects slick drift to a release region and time window, correlates AIS tracks against that space-time box, and decomposes every score into named, individually explained factors. The mechanism a neighbouring product could not truthfully copy is the pairing: a reconstructed origin, and a per-factor audit trail behind every number.

## Operating Context

- Analyst reviews a SAR acquisition (Sentinel-1 class) over Indian waters; one incident at a time.
- Output is investigative support and corroboration material, never a legal finding.
- Indian maritime context: Gulf of Kutch / Arabian Sea tanker corridor; Indian Coast Guard is nodal agency under NOSDCP.
- Demo environment: laptop driving a projector, bright room, unreliable venue wifi. No mobile support required.

## Capabilities and Constraints

- Static single-page app: one HTML file plus `mock-data.json`. No build step, no backend, no accounts, no database.
- Must run with no network except map tiles. Every library and font is self-hosted.
- The data source is swappable by changing one constant; nothing else reads it.
- **Contract:** `satellite_image_url`, `spill_mask` (GeoJSON Polygon), `origin_region` `{polygon, time_window{start,end}}`, `candidate_ships[]` of `{id, name, track (LineString), score, factors[5]}`.
- **Factor model (confirmed this session):** weighted subscores — Proximity to origin 25, Temporal compatibility 25, Trajectory compatibility 20, Drift consistency 20, AIS/SAR discrepancy 10. Total score is the literal sum. This adds an optional `max` per factor to the contract and must be mirrored by the teammate's pipeline.
- Candidate count varies and must not be hardcoded. Factor count is exactly five.
- A missing or broken satellite image must degrade to a placeholder, never a broken-image icon or a crash.

## Brand Commitments

User-pinned and binding — these exist to match an accompanying pitch document, so the two read as one product:

- **Colour:** navy `#0A1F33`, teal `#1FB8A6` (confirmed data, high scores), amber `#E8983A` (uncertainty, origin region, caution scores), gray `#5C6B78` (low scores, secondary text), paper `#F6F4EE` (background).
- **Type:** Space Grotesk (headings, score numerals), IBM Plex Sans (body and explanations), IBM Plex Mono (timestamps, coordinates, factor labels — anything that reads as evidence).
- **Light basemap is required.** A dark basemap washes out the teal and amber overlays in a bright demo room.

## Evidence on Hand

- `mock-data.json` — **entirely fabricated.** One spill mask, one origin region, five candidate vessels.
- `assets/sar-scene.svg` — a synthetic SAR scene generated with SVG noise filters. Not a real acquisition.
- Vessel names, IMO numbers, flags, tracks, scores, and all factor explanations are invented.
- No real incident, no pipeline output, no verified vessel records exist yet.

**Future work must never present any of this as real data,** and must not fabricate incidents, agencies, endorsements, or accuracy claims on top of it.

## Product Principles

1. **Never show a score without its explanation adjacent.** Explainability is the product, not a feature of it.
2. **Encode certainty.** Observed fact and modelled inference must be visually distinguishable on sight — the slick is measured, the origin region is inferred.
3. **The ranking must be readable from the map alone,** before anyone reads a number.
4. **Attribution is a lead, not a verdict.** The interface must never imply proof of guilt.
5. **Survive a dead network.** Anything that breaks without wifi does not ship.

## Accessibility & Inclusion

Bright-room projector legibility is a hard requirement, not a nicety. Score meaning must never rest on colour alone — rank position, numeral, and a verdict word carry it independently for colour-vision-deficient viewers and for washed-out projectors.
