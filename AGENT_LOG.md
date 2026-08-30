# OCEANIQ — Shared Agent Log

**Purpose:** one file both agents read before starting and append to when finishing,
so nobody re-does work, re-diagnoses a solved bug, or acts on a claim that was
never verified.

**Related files — do not duplicate them here**
- [`handoff.md`](handoff.md) — the work order: vision, state, task list. *Plan.*
- [`contracts/georeferencing.json`](contracts/georeferencing.json) — data contract between pillars.
- `AGENT_LOG.md` (this file) — *what actually happened, with evidence.*

---

## Protocol

1. **Read this file first.** Check the Ownership table before starting anything.
2. **Claim a task** by adding a `CLAIMED` line before you start. Prevents collisions.
3. **When done, append an entry** using the template below. Newest at the bottom.
4. **Evidence or it did not happen.** Paste the real console output — status codes,
   counts, assertion results. "It works" is not an entry.
5. **Status must be one of:**
   - `VERIFIED` — executed, output pasted, assertions passed
   - `WRITTEN` — code exists, **never executed**. Not done.
   - `PARTIAL` — some of it works; say exactly which part does not
   - `BLOCKED` — cannot proceed; name the blocker and who can clear it
6. **If you contradict an earlier entry, say so explicitly** and show why. Do not
   silently overwrite. This has already happened once (see entry 3).
7. **Never commit `.env`, `*.pth`, or the dataset zips.**

### Entry template

```
### <n>. <TASK> — <STATUS>
**Agent:** <who>   **When:** <YYYY-MM-DD HH:MM>
**Did:** one or two lines
**Evidence:**
    <pasted real output>
**Caveats / what is still not proven:**
**Next:**
```

---

## Ownership

| Task | Owner | Status |
|---|---|---|
| 1. OpenDrift backward run | Claude (Colab) | **VERIFIED** |
| 2. GFW query shaping | Other agent | **PARTIAL** — events work, 4wings still malformed |
| 3. Georeferencing contract | Other agent | **VERIFIED** (script runs) |
| 4a. Cell 30 look-alike on real predictions | unclaimed | not started |
| 4b. Retrain with more epochs | unclaimed | optional |
| 5. CMEMS / ERA5 signups | **USER ONLY** | blocked — needs a human |
| 6. Scoring engine | unclaimed | gated on 1-3 |
| 7. Dashboard | unclaimed | gated on 6 |

---

## Log

### 1. Pillar 1 — SAR spill detection — VERIFIED
**Agent:** Claude   **When:** 2026-08-30 (commit `5047f7a`)
**Did:** Trained U-Net/ResNet34 binary segmentation in Colab on Deep-SAR.
**Evidence:**

    epoch  14 | train 0.1486 | val 0.1345 | mIoU 0.8560 | <- best, saved
              IoU: background=0.916  oil spill=0.796
    done: ran all 15 epochs, 0h25m53s elapsed
    best val mIoU = 0.8560
    (fresh kernel) loaded epoch 14 | mIoU 0.8560

**Caveats:** Val loss still falling at epoch 15 — not converged. Training-curve
cell is unrecoverable (kernel restarted, `history` lost).
**Next:** 4b optional retrain with `EPOCHS=30`.

---

### 2. Look-alike screening — WRITTEN (not validated on real data)
**Agent:** Claude   **When:** 2026-08-30 (commit `5047f7a`)
**Did:** `lookalike_screen.py` — three shape rules, not a classifier.
**Evidence:** six synthetic self-checks pass.

    1. small disc    area=  441 elong=1.00 rough=0.86 -> look-alike
    2. long ellipse  area= 1105 elong=10.48 rough=2.04 -> oil
    4. ragged blob   area=  355 elong=1.04 rough=1.71 -> oil (kept on roughness alone)
    ALL LOOK-ALIKE SCREENING CHECKS PASSED

**Caveats:** Thresholds calibrated on **synthetic discs only**. Never run against
real model predictions. Cannot flag large or elongated look-alikes. A disc
measures roughness ~0.86, not 1.0 — do not "fix" this from circularity theory.
**Next:** Task 4a.

---

### 3. GFW auth — VERIFIED — **contradicts an earlier claim**
**Agent:** Claude   **When:** 2026-08-30
**Did:** Queried GFW directly to test the claim that the token lacked dataset
permissions.
**Evidence:**

    GET /v3/vessels/search  -> HTTP 200, total=5480
        XIN LOC BIEN BD95017 | flag=VNM | mmsi=574951179
    GET /v3/events (gaps)   -> HTTP 200, total=34956
        DONGWON NO.16 | flag=KOR | mmsi=440825000

**Correction:** the earlier report that "the token does not have permission to
access the vessel datasets" was **wrong**. The 403 was Cloudflare bot-blocking
(`error code: 1010`) on the client signature. Adding a browser `User-Agent`
turns the identical request into HTTP 200. The user was told to go change GFW
account permissions — that advice should be withdrawn; nothing is wrong there.
**Next:** Task 2 — query shaping (4wings 0 rows, events date filter ignored).

---

### 4. OpenDrift backward run — VERIFIED
**Agent:** Claude (Colab)   **When:** 2026-08-30
**Did:** Built `opendrift_backward_demo.ipynb` and **executed it in Colab**.
OpenDrift 1.14.11, OceanDrift, 200 particles, `time_step=-3600`.
Notebook: https://colab.research.google.com/drive/1Ne80O_dYOAgnSNXt_PNTjK_M9wbXgotg
**Evidence:**

    reader coverage:
       time: 2015-11-16 00:00:00 -> 2015-11-18 18:00:00
    seeded 200 particles at (4.9, 60.0) at 2015-11-18 18:00:00
    running BACKWARD 12h with time_step=-3600s ...

    trajectory array shape (elements, timesteps): (200, 13)
    seed time      : 2015-11-18 18:00:00
    final sim time : 2015-11-18 06:00:00
    ran backward   : True   (delta = -1 day, 12:00:00)
    centroid start : (4.9013, 59.9988)
    centroid end   : (4.7940, 59.8540)
    net displacement: 17.10 km
    BACKWARD RUN VERIFIED

Both plots rendered (matplotlib + native cartopy). Trajectories fan coherently
southwest from seed to backtracked origin. 17.1 km / 12 h ~= 0.40 m/s — plausible
for NorKyst coastal currents.

**Finding that matters:** the **PyPI wheel does not ship `tests/test_data`.** The
notebook's fallback fetched the sample NetCDF (7.1 MB) from the OpenDrift repo.
Any script calling `o.test_data_folder()` without a fallback fails here.
**Caveats:** Norwegian sample forcing, not Indian waters. Not connected to the
detector. No ensemble/uncertainty — single realisation.
**Next:** Task 5 (real forcing), then ensemble.

---

### 5. GFW query shaping — PARTIAL
**Agent:** Other agent   **When:** 2026-08-30
**Did:** Rewrote `tools/gfw_client.py` with the User-Agent fix; deleted the two
broken scripts.
**Evidence:** reported ~13M events returned for a 2024 date filter.
**UNVERIFIED — needs checking:** the original bug was that the date filter was
*silently ignored* (a Jan-2025 window returned events starting in 2017). A large
result count does **not** prove filtering works. Assert that every returned
event's `start` falls inside the requested window before calling this done.
**Still broken:** 4wings POST returns "body malformed" — geometry format wrong.
**Next:** fix the 4wings geojson body; add the date assertion.

---

### 6. Georeferencing contract — VERIFIED (runs)
**Agent:** Other agent (written) / Claude (executed)   **When:** 2026-08-30
**Did:** `tools/spill_to_seeds.py` + `contracts/georeferencing.json`.
**Evidence (Claude ran it):**

    Testing mask_to_seed_points with Path (B) Demo Transform...
    Generated 100 seed points.
    Sample seed: {'lat': 18.488, 'lon': 68.514, 'time': '2024-01-15T12:00:00Z'}

`pixel_size_deg=0.0001` ~= 11 m/px, a reasonable Sentinel-1 GRD approximation.
**Caveats:** This is **Path B — demo placement**, an *assumed* anchor and pixel
size, not real georeferencing. **It must be stated on the slide.** Path A (real
Sentinel-1 GeoTIFF transforms) remains unbuilt. Not yet wired to real detector
output.
**Next:** feed a real predicted mask through it into the OpenDrift seeds.

---

## Open questions

1. **Who runs Task 4a?** Cell 30 has never produced output. Needs Colab, exact
   cell order `2,4,6,8,10,12,14,16,18,20 -> 28 -> 26 -> 30` (skip 22 and 24).
2. **Task 5 (CMEMS/ERA5) cannot be done by an agent.** Registration needs a human
   with an email address and licence acceptance. **User action required.**
3. **Nothing is integrated yet.** Every pillar has been proven *in isolation*. The
   first real end-to-end attempt — detector mask -> seeds -> backward run ->
   origin bbox -> GFW query — has not been tried and will surface its own bugs.
