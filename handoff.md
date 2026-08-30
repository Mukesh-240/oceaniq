# OCEANIQ — Hand-off / Work Order

**Last updated:** 2026-08-30 (revision 2)
**Commits:** `5047f7a` (pillar 1), `f2b3c8e` (OpenDrift notebook + mount retry)

Read sections 0 and 1 before touching anything. Section 5 is your actual job.

---

## 0. Corrections — read this first

Prior claims in this project that turned out to be **wrong**. Do not repeat them,
and do not act on them.

| Claim | Reality | Evidence |
|---|---|---|
| "GFW token lacks permission to access vessel datasets" | **False.** The token works. | `HTTP 200`, `total=5480` vessels returned |
| "Oil covers ~3.47% of pixels" | **False** — came from one image | 400-mask sample: median 17.7%, mean 24.6% |
| "Deep-SAR masks are binary except one stray file" | **Incomplete** — 31% have intermediate greys | 400-mask sample: 276 clean, 124 with soft edges |

### The GFW 403 is Cloudflare, not permissions

Both `tools/test_gfw_api.py` (no User-Agent) and my first attempt (urllib default
UA) got `HTTP 403 / error code: 1010`. That is **Cloudflare bot-blocking on the
client signature**, not an auth or entitlement failure.

**Adding a browser User-Agent turns the identical request into HTTP 200.**

```python
req.add_header("User-Agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
```

Do **not** ask the user to change GFW account permissions. Nothing is wrong there.

---

## 1. The Final Vision

Source of truth: [`files/OCEANIQ-final-hackathon-POC.md`](files/OCEANIQ-final-hackathon-POC.md).

Ships illegally dump oil at sea. Spotting the oil is not the hard part —
**proving which ship did it** is, because the ship has moved on by the time a
spill is seen, and offenders often switch off AIS.

OCEANIQ works backward, like a detective:

1. **Detect** the spill in SAR imagery (radar sees at night and through cloud)
2. **Confirm** it is oil, not a look-alike (algae, calm water, biogenic film)
3. **Measure** size, shape, orientation
4. **Trace it backward in time** with OpenDrift to estimate *where and when it
   started* — the core differentiator
5. **Query AIS history** for ships at that estimated origin and time
6. **Score candidates** on transparent clues (position, timing, heading vs. drift,
   AIS gap) — never one opaque confidence number
7. **Present** a map + ranked suspects with per-clue explanation

Stance: never "nearest ship is guilty." Output is *investigative leads for
humans*, never a verdict.

---

## 2. Current State

| Pillar | State | Blocker |
|---|---|---|
| 1. SAR spill detection | **DONE** — 0.796 oil IoU, checkpoint on Drive | — |
| 1b. Look-alike screening | Code done + 6 self-checks pass; **never run on real predictions** | Task 4 |
| 2. Backward drift | Notebook **written and statically verified, NEVER EXECUTED** | Task 1 |
| 3. Vessel attribution | **Auth proven, real data returned.** Query shaping broken | Task 2 |
| 4. Georeferencing (px → lat/lon) | **Does not exist. Unowned.** | Task 3 |
| 5. Scoring engine | Not started | Depends on 2+3+4 |
| 6. Dashboard | Not started | Depends on 5 |

### Pillar 1 — detection (done)

U-Net / ResNet34 / ImageNet, binary (background vs oil). All 15 epochs, 25m53s on
a T4.

| Metric | Value |
|---|---|
| Best val mIoU | **0.8560** (epoch 14) |
| **Oil-spill IoU** | **0.796** |
| Background IoU | 0.916 |
| Final train / val loss | 0.1482 / 0.1329 |

Val loss was **still falling** at epoch 15 — not converged; raising `EPOCHS`
should still help.

- Notebook: https://colab.research.google.com/drive/1y9D8G5FAq_7Ax1gOcL1nMv1VwuN-kZV4
- Checkpoint: `MyDrive/oil_spill_runs/unet_resnet34_best.pth` (verified reloadable)
- **Delete stale notebook** `1_LOu9jVbziE9D2yO3yhmRAaSu1BAK6hk` — broken Kaggle cell

### Dataset

`bakhtiyar2222/deep-sar-oil-spill-segmentation-refined` (Kaggle, public, CC BY 4.0).
6,455 train / 1,615 val pairs, 256×256 PNG, perfect filename pairing.
**Downloads into Colab in ~39s at 67 MB/s — never upload it to Drive.**

Measured over 400 random training masks:
- 69% clean `{0,255}`; **31% contain intermediate greys** → threshold at `>127`,
  never value-map. Threshold choice moves positive fraction ~2.5% mean, 10.8% worst.
- Oil = **median 17.7%** of pixels (mean 24.6%). Moderate imbalance, not severe.

**No 5-class labels exist.** The sea/oil/look-alike/ship/land taxonomy is the
Krestenitis/MKLab set, `mklab.iti.gr`, by request only. A preset sits commented
out in the notebook Config cell.

### Pillar 3 — what actually works today

Verified live against the API:

```
GET /v3/vessels/search           -> HTTP 200, total=5480
   XIN LOC BIEN BD95017 | flag=VNM | mmsi=574951179
GET /v3/events (gap events)      -> HTTP 200, total=34956
   DONGWON NO.16 | flag=KOR | mmsi=440825000
```

Broken, and your job to fix (Task 2):
- `POST /v3/4wings/report` for the Arabian Sea box returned **HTTP 200 but 0 rows**
- Events **date filter did not apply** — 2017 events came back for a Jan-2025 window

---

## 3. Files

| File | Who | Purpose |
|---|---|---|
| `oil_spill_unet_colab.ipynb` | me | 32-cell training notebook. **Deliverable.** |
| `tools/build_nb.py` | me | **Generator — single source of truth for that notebook** |
| `opendrift_backward_demo.ipynb` | me | 15-cell backward-drift proof. **Never executed.** |
| `tools/build_opendrift_nb.py` | me | Generator for it |
| `lookalike_screen.py` | me | Rule-based screening + 6 self-checks |
| `tools/test_limits.py` | me | Simulation checks for stop/shrink logic |
| `inspect_sample.py` | me | Single image/mask inspector |
| `tools/test_gfw_api.py` | other agent | **Broken** — no User-Agent, wrong `datasets=` param |
| `tools/test_opendrift.py` | other agent | **Never run.** Calls `o.test_data_folder()` and `o.env.readers[...]`, neither of which exists in current OpenDrift |
| `tools/check_datasets.py` | other agent | Unreviewed |
| `.env` | other agent | Holds `GFW_API_TOKEN`. **Gitignored — keep it that way** |

**Never hand-edit the two `.ipynb` files.** Edit the generator, then:

```bash
python tools/build_nb.py oil_spill_unet_colab.ipynb
python tools/build_opendrift_nb.py opendrift_backward_demo.ipynb
```

`build_nb.py` embeds `lookalike_screen.py` into a notebook cell at build time, so
Colab stays self-contained while the scoring engine imports the same file.

---

## 4. Gotchas — each of these cost real time

1. **`python -m kaggle` fails on Colab** (`No module named kaggle.__main__`). Use
   `KaggleApi().authenticate()` + `dataset_download_files(...)`. Already fixed.
   The failure message looks nothing like the real cause.
2. **Colab Secrets' "Notebook access" is PER-NOTEBOOK.** Re-uploading a notebook
   needs the toggle set again. Symptom: `TimeoutException`, not a permissions error.
3. **`drive.mount()` failed 3 separate times** with bare `ValueError: mount failed`,
   succeeding on plain retry every time. **Now auto-retries** (4 attempts) in
   `build_nb.py`. Copy that helper into any new notebook.
4. **Colab kernels restart.** After training, `history`/`model`/`CLASS_NAMES` were
   wiped and plot cells died with `NameError`. Checkpoints on Drive survive;
   in-memory state does not.
5. **Colab virtualizes off-screen cells** and renders many outputs in cross-origin
   iframes — browser automation cannot read them via JS. Scroll the cell into view
   and use an accessibility snapshot.
6. **Do not batch-click Colab run buttons.** A queued cell's button becomes *stop*;
   a second click cancels it. Single click, in order.
7. **`matplotlib` is imported in cell 18** of the training notebook. Skip it and
   cells 26/30 die with `NameError: name 'plt' is not defined`.

---

## 5. YOUR JOB

Ordered by risk retired per hour. **Do them in order.** Report back after each
with the actual console output, not a summary.

---

### TASK 1 — Execute the OpenDrift backward notebook (~30 min) — HIGHEST PRIORITY

The notebook exists and is statically verified. **It has never been run.** Written
≠ working; that distinction is the whole point of this task.

**Steps**
1. Colab → `File > Upload notebook` → `opendrift_backward_demo.ipynb`
2. `Runtime > Change runtime type > CPU` (no GPU needed; connects faster)
3. `Runtime > Run all`
4. Install takes 2–4 min (cartopy, netCDF4, xarray, pyproj)

**Success criteria — all four**
- `opendrift <version>` prints
- Cell 4 prints `BACKWARD RUN VERIFIED` (it asserts `end_time < seed_time` and
  net displacement > 0.05 km — a plot alone does not prove direction)
- A trajectory plot renders showing coherent particle paths
- Net displacement is a plausible few km over 12 h, not 0 and not 10,000

**Known failure modes**
- *Sample data missing from wheel* → cell 2 auto-downloads it from the OpenDrift
  repo. Expected, not an error.
- *cartopy plot fails* → the matplotlib fallback still proves the trajectory. Fine.
- *`OpenOil` config keys differ by version* → wrapped in try/except; OceanDrift is
  the proof that matters.
- *`o.result` vs `o.history`* → `get_track()` handles both.

**Deliverable:** the trajectory PNG + pasted text of the cell-4 verification block.

---

### TASK 2 — Fix GFW query shaping (~45 min)

Auth is **proven**. Do not re-test auth. Two specific bugs.

**First, write `tools/gfw_client.py`** — one place, correct by construction:
- `User-Agent` header baked in (non-negotiable — see section 0)
- token from `.env` via `GFW_API_TOKEN`, never hardcoded
- array params as `datasets[0]=`, not `datasets=`
- print status + first 300 chars of body on any non-200

Then delete or rewrite `tools/test_gfw_api.py`, which is wrong on both counts.

**Bug A — 4wings report returns 0 rows**
`POST /v3/4wings/report`, Arabian Sea box (68–73°E, 18–23°N), `2025-01-01,2025-02-01`
→ HTTP 200, zero rows, zero hours. Implausible for that region; the query is wrong,
not the ocean. Try, in order:
1. Widen `date-range` to a full year — the dataset may lag
2. `temporal-resolution=YEARLY`, `spatial-resolution=HIGH`
3. `group-by=VESSEL_ID` instead of `FLAG`
4. `region` by EEZ id instead of inline `geojson`
5. Confirm the dataset id against `GET /v3/datasets`

**Bug B — events date filter ignored**
`GET /v3/events?start-date=2025-01-01&end-date=2025-02-01` returned events starting
in **2017**. Param names or filter semantics are wrong. Check the v3 events schema;
also add `region`/bbox so results are confined to the demo area.

**Deliverable:** apparent fishing hours for the Arabian Sea box in a known window,
**and** AIS gap events filtered to that bbox and date range. Paste real rows.

---

### TASK 3 — Georeferencing contract (~2 h) — THE BIGGEST RISK

**This is the piece most likely to sink the demo, and nobody owns it.**

The detector emits a **pixel mask on a 256×256 tile**. OpenDrift needs **lat/lon
seed points**. Nothing performs that conversion, and the Deep-SAR PNGs carry **no
geotransform metadata at all**. Until this exists, pillars 1 and 2 cannot connect
— they are two demos, not a pipeline.

**Decide and write down** which path:
- **(a) Real georeferencing** — source Sentinel-1 GRD GeoTIFFs (Copernicus Open
  Access Hub / ASF) that carry a CRS + geotransform, run the model on tiles cut
  from them, map pixels back through the transform. Honest, slower.
- **(b) Demo placement** — anchor one Deep-SAR scene at chosen Arabian Sea coords
  with an assumed pixel size, and **state that assumption on the slide**.
  Defensible for a hackathon *if disclosed*. Fast.

Recommendation: **(b) for the demo, (a) documented as the production path.** Do
not silently do (b) and present it as (a).

**Deliverable:** `spill_to_seeds.py` exposing

```python
mask_to_seed_points(mask, transform, when) -> list[{lat, lon, time}]
```

plus a written JSON contract for Pillar 1 → 2 (seed points, CRS, timestamp) and
Pillar 2 → 3 (origin bbox + time window). Contract first, code second.

---

### TASK 4 — Close the Pillar 1 gaps (~30 min)

**4a. Run look-alike screening on real predictions.** Cell 30 has *never* produced
output. After a kernel restart, run in this exact order, and **single-click**:

```
2, 4, 6, 8, 10, 12, 14, 16, 18, 20   (rebuild state; 18 imports matplotlib)
28   (defines screen())
26   (loads checkpoint from Drive)
30   (applies screening to real predictions)
```

Skip 22 (training, 26 min) and 24 (needs dead `history`).

**Deliverable:** cell 30 output — the blob table with verdicts — plus the
before/after mask figure. This is the first real test of thresholds that were
calibrated only on synthetic discs.

**4b. Optional:** retrain with `EPOCHS = 30`. Val loss was still falling.

---

### TASK 5 — Start real-forcing signups NOW (~15 min, then waiting)

Blocking with a lead time; start it early even though it is used later.
- **CMEMS** (currents) — registration is **not instant**
- **ERA5 / CDS** (wind) — API key + accepted licence

Store keys in `.env` (gitignored). **Deliverable:** one successful data fetch.

---

### TASK 6 — Scoring engine (only after 1–3)

Per `files/OCEANIQ-final-hackathon-POC.md`: transparent per-clue points, not one
number. Clues: proximity to backtracked origin, temporal overlap, heading
consistency with drift, AIS gap during the window. Each clue must be independently
displayable with its own justification — that explainability *is* the pitch.

---

## 6. Do not

- **Do not** tell the user to fix GFW account permissions. The token is fine.
- **Do not** re-upload the dataset to Drive. Kaggle-direct is 39s.
- **Do not** set `NUM_CLASSES = 5`. Those labels do not exist; Step 0 will halt.
- **Do not** present look-alike screening as a trained classifier, anywhere.
- **Do not** quote "3.47% oil pixels."
- **Do not** hand-edit the `.ipynb` files — edit the generators.
- **Do not** commit `.env` or `*.pth`.
- **Do not** claim a component works because the code was written. Run it, paste
  the output. Three separate "done" claims this project have failed on execution.

## 7. Report back with

For each task: the **command you ran**, the **actual output** (not a summary),
what failed and why, and what you changed. If something is blocked, say so
plainly and move to the next task rather than reporting partial success as done.
