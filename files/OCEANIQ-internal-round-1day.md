# OCEANIQ — 1-Day Internal Round POC
## (Scoped down from the 36-hour national-final architecture)

**Reality check:** the full OpenDrift + GFW + evidence-scoring pipeline is a 36-hour, 6-person national build. For a 1-day internal round, you build a **working frontend on top of precomputed real outputs** — not a live end-to-end pipeline. Judges here are faculty, not NTRO domain experts: they're scoring idea + credible demo + presentation, not scientific bulletproofing.

**Core rule: nothing heavy runs live during the demo.** SAR segmentation, OpenDrift backtracking, and AIS filtering all run *before* the demo, on your laptop, offline. The demo consumes their JSON output. This removes almost all live-failure risk.

---

## Architecture for the day

```
[Precomputed offline — do this first]
Known labeled SAR spill image
   → segmentation mask (pretrained model or dataset's ground-truth mask)
   → slick geometry (area/centroid/orientation)
   → OpenDrift backward run (using OpenDrift's own example NetCDF forcing data)
   → origin_region.geojson + time_window.json
   → small offline vessel list (2-5 named example vessels) with positions
   → candidate_scores.json (weighted score breakdown per vessel)

[Live at demo — this is what you actually build today]
Next.js frontend
   → loads the JSON/GeoJSON above
   → map: slick + origin region + vessel tracks
   → ranked candidate panel with "why" breakdown
   → one button: "Reconstruct Incident" → animates through the stages using the precomputed data
```

---

## Hour-by-hour (assume ~12-14 working hours)

| Hours | Task |
|---|---|
| 0–1 | Pick ONE labeled SAR spill image from a public dataset (Kaggle Oil Spill / MKLab). This is your whole "case." |
| 1–3 | Get a detection mask. Try a pretrained SAR oil-spill segmentation model if one loads cleanly in under an hour; if not, **use the dataset's own ground-truth mask** and label it honestly as "detection output" — don't burn hours fighting a model that won't converge today. |
| 3–4 | Compute slick geometry from the mask (area, centroid, orientation) — simple Python with `shapely`/`rasterio`. Fast, genuinely real. |
| 4–6 | Run OpenDrift **once, offline**, using its own bundled example/test forcing data (don't fight real NetCDF downloads today), seeded backward from your slick centroid. Export the resulting origin probability cloud as `origin_region.geojson` + a time window. |
| 6–8 | Build a small offline vessel list — 3-5 named vessels with a few lat/lon/time points each, explicitly labeled as a **controlled/example scenario** (real historical AIS for this exact scene is a stretch goal, not a requirement today). Manually mark 1 as "inside origin zone + time-compatible" and the others as not. |
| 8–9 | Write the scoring script: `score = w1*spatial + w2*temporal + w3*trajectory + w4*drift + w5*AIS_discrepancy`, run once on your vessel list, output `candidates.json` with the breakdown per vessel. |
| 9–12 | Build the Next.js dashboard: map (Leaflet, free) showing slick polygon + origin region + vessel tracks, ranked candidate cards, click-through "why" panel showing the score breakdown. |
| 12–13 | Wire the "Reconstruct Incident" button — a scripted client-side animation stepping through: slick detected → geometry computed → drift backtracked → origin region shown → AIS candidates loaded → ranking revealed. All using data you already have — no live compute, so it can't fail. |
| 13–14 | Rehearse the pitch. Practice saying plainly: "detection, drift modeling, and AIS reconstruction were run offline on a controlled test case using OpenDrift and public datasets — this demo shows the reconstruction and attribution logic working end-to-end." |

---

## What to say about scope (be upfront, it lands better than hiding it)

*"This is a controlled validation scenario built on a real SAR spill observation, run through an established drift-modeling tool (OpenDrift), with a representative vessel scenario to demonstrate the attribution logic. Full live satellite/AIS ingestion is the next milestone if selected for the national round."*

Faculty judges respect that sentence. It's honest, it's specific, and it shows you know the difference between a demo and a production system — which is a stronger signal than pretending it's real-time.

---

## What NOT to touch today
- Live Sentinel-1 or AIS ingestion
- Look-alike classifier (mention it as designed, don't build it today)
- Forward counterfactual simulation
- Gemini, Supabase persistence, auth, mobile — all cut, as before
- Multi-person specialist roles — for a 1-day solo/small push, one person on data (segmentation + OpenDrift + scoring script) and one on frontend is enough; don't over-organize for a day you don't have
