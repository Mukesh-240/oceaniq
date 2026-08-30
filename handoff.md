# OCEANIQ — Hand-off

**Date:** 2026-08-30
**Phase completed:** Pillar 1 (spill detection) + heuristic look-alike screening
**Phase not started:** Pillar 2 (backward drift), Pillar 3 (vessel attribution)

---

## 1. The Final Vision

Source of truth: [`files/OCEANIQ-final-hackathon-POC.md`](files/OCEANIQ-final-hackathon-POC.md). Summary:

Ships illegally dump oil waste at sea. Spotting the oil is not the hard part —
**proving which ship did it** is, because by the time a spill is noticed the ship
has moved on, and offenders often switch off their AIS transponder.

OCEANIQ works backward, like a detective:

1. **Detect** the spill in SAR satellite imagery (radar works at night and through
   cloud — exactly when illegal dumping happens)
2. **Confirm** it is oil, not a look-alike (algae, calm water, biogenic film)
3. **Measure** its size, shape, orientation
4. **Trace it backward in time** with OpenDrift to estimate *where and when the
   spill most likely started* — this is the core differentiator
5. **Query AIS history** for ships actually present at that estimated origin and time
6. **Score each candidate** on multiple transparent clues (position, timing,
   heading consistency with drift, AIS gap) — not one opaque confidence number
7. **Present** a map plus a ranked suspect list with a per-clue explanation

The deliberate design stance: **do not** say "nearest ship is guilty." Do the
backward reconstruction properly, and show the reasoning. Output is
*investigative leads for humans*, never a verdict.

---

## 2. What Is Actually Done

### Pillar 1 — Spill detection: COMPLETE and validated

A U-Net (ResNet34 / ImageNet encoder) trained on SAR imagery, binary
segmentation (background vs. oil spill).

| Metric | Value |
|---|---|
| Best val mIoU | **0.8560** (epoch 14) |
| **Oil-spill IoU** | **0.796** ← the number that matters |
| Background IoU | 0.916 |
| Final train / val loss | 0.1482 / 0.1329 |
| Epochs | all 15, no early stop (25m53s on a T4) |

Val loss was still falling at epoch 15 — **not converged, raising `EPOCHS` should
still help.** No overfitting observed.

- **Live notebook:** https://colab.research.google.com/drive/1y9D8G5FAq_7Ax1gOcL1nMv1VwuN-kZV4
- **Checkpoint:** Google Drive → `MyDrive/oil_spill_runs/unet_resnet34_best.pth`
  (verified: reloads cleanly in a fresh kernel → `loaded epoch 14 | mIoU 0.8560`)
- **DELETE the older notebook** `1_LOu9jVbziE9D2yO3yhmRAaSu1BAK6hk` — it contains a
  broken Kaggle cell and will waste your time if opened by mistake.

### Dataset

`bakhtiyar2222/deep-sar-oil-spill-segmentation-refined` (Kaggle, public, CC BY 4.0).
6,455 train + 1,615 val pairs, 256x256 PNG, perfect filename pairing (verified).
Downloads **directly into Colab in ~39s at 67 MB/s** — never upload it to Drive.

**Measured properties (400 random training masks — trust these, not assumptions):**
- 69% of masks are clean `{0, 255}`; **31% contain intermediate greys** (soft
  boundaries). Masks are therefore **thresholded at >127**, not value-mapped.
  Threshold choice shifts positive-pixel fraction by ~2.5% mean, 10.8% worst case.
- Oil covers a **median 17.7% of pixels** (mean 24.6%). The Step-0 scan over 200
  masks reported 15.23%. This is a *moderate* imbalance, not severe.

> **Correction carried forward:** an earlier estimate of "3.47% oil pixels" came
> from a single image and is **wrong**. Do not repeat it in the pitch. The
> consequence: the usual argument for Dice loss (that CE lets an all-background
> prediction win) does not really apply here — plain cross-entropy would train
> acceptably. Dice is kept only because it optimises the reported IoU directly.

### Classes: binary only

The 5-class taxonomy (sea / oil spill / look-alike / ship / land) belongs to the
**Krestenitis/MKLab** dataset, distributed from `mklab.iti.gr` **by request only**
— not on Kaggle, not available today. A 5-class preset sits commented out in the
notebook's Config cell for whenever it is obtained.

### Look-alike screening: implemented, NOT yet validated on real predictions

[`lookalike_screen.py`](lookalike_screen.py) — rule-based post-processing, numpy +
`scipy.ndimage` only. **Not a trained classifier**, and labelled as such in every
line it prints. Three rules per blob, in order:

| # | Condition | Verdict |
|---|---|---|
| 1 | `area < 50 px` | `noise` |
| 2 | round (`elong <= 1.8`) **and** smooth (`rough <= 1.35`) **and** small (`area < 600 px`) | `look-alike` |
| 3 | otherwise | `oil` |

Six synthetic self-checks pass (`python lookalike_screen.py`).

**Calibration note — do not "fix" this:** on a pixel grid a smooth disc measures
roughness **~0.86, not the textbook 1.0**, because boundary-pixel counting reads
low on curves. Thresholds are set from *measured* shapes. Do not re-derive them
from circularity theory.

**Honest limits (already written into the notebook, keep them in the pitch):**
- Cannot flag a **large or elongated** look-alike — an extended algal bloom passes
  straight through as oil.
- **Never validated against labelled look-alikes**, because none are available.
  Thresholds are reasoned defaults, not fitted values.
- Rule 2 **will discard small genuine slicks** that are round and smooth. Real
  recall cost, not a free win.
- Future work: obtain the Krestenitis 5-class set, train the real classifier, and
  **delete these rules** rather than tuning them further.

### Pillar 2 (OpenDrift) — NOT STARTED
Not installed anywhere (`ModuleNotFoundError: No module named 'opendrift'`).
Zero lines run today, forward or backward.

### Pillar 3 (GFW / AIS) — NOT STARTED
No query has ever been made. **No GFW API token has been provided** — the only
credential shared this session was Kaggle. Blocked on the user.

---

## 3. Files Created / Modified

| File | Status | Purpose |
|---|---|---|
| `oil_spill_unet_colab.ipynb` | created | 32-cell Colab training notebook. **Deliverable.** |
| `lookalike_screen.py` | created | Heuristic look-alike screening + self-check |
| `inspect_sample.py` | created | Loads one image/mask pair, prints shapes/classes, saves side-by-side plot |
| `handoff.md` | created | This document |
| `tools/build_nb.py` | created | **Generator for the notebook — single source of truth** |
| `tools/test_limits.py` | created | Simulation checks for the stop/shrink logic |
| `data/deep-sar-sample/` | created | One image+mask pair + `sample_check.png` |
| `data/oil-spill-detection/` | created | Tabular CSV (937x50) — **wrong dataset, ignore** |
| `data/mask_probe/` | created | 9 masks from the binary-vs-5-class investigation |
| `oil_spill.zip` (1.26 GB) | created | Full dataset, pre-packaged for Drive. **Now redundant** |
| `oil_spill_small.zip` (81 MB) | created | 400/100 subset for fast smoke tests. Still useful. |

**Edit the notebook via `tools/build_nb.py`, then regenerate:**

```bash
cd <project root>
python tools/build_nb.py oil_spill_unet_colab.ipynb
```

It embeds `lookalike_screen.py` into a notebook cell at build time, so the Colab
notebook stays self-contained (nothing extra to upload) while the scoring engine
imports the same file. **Editing the `.ipynb` by hand will be overwritten.**

Also outside the repo: `C:\Users\Mukesh\oil_spill_build\` holds the extracted
1.3 GB dataset. Safe to delete — Colab re-downloads in 39s.

---

## 4. Gotchas That Cost Real Time Today

Each of these was hit for real. Do not rediscover them.

1. **`python -m kaggle` fails on Colab** — `No module named kaggle.__main__`.
   Colab's kaggle package has no `__main__`. Use the Python API:
   `KaggleApi().authenticate()` then `dataset_download_files(...)`. Already fixed
   in the notebook. Note the failure looks nothing like a credentials problem.
2. **Colab Secrets' "Notebook access" is PER-NOTEBOOK.** Granting it on one
   notebook does not carry to a re-upload. Symptom: `TimeoutException` from
   `userdata.get()`, not a permissions message.
3. **`drive.mount()` is flaky — it failed 3 separate times** with a bare
   `ValueError: mount failed`. It succeeds on a simple re-run every time. Build a
   retry in, or expect to click twice. **This is a live demo-day hazard.**
4. **The Colab runtime restarted after training**, wiping `history`, `model`,
   `CLASS_NAMES`. Downstream plot cells then died with `NameError`. The
   checkpoint survived on Drive; the **training-curve cell is unrecoverable**
   without retraining (per-epoch numbers are preserved above).
5. **Colab virtualizes off-screen cells** and renders many outputs in
   cross-origin iframes — automation cannot read them via JS. Scroll the cell
   into view and use an accessibility snapshot.
6. **Do not batch-click Colab run buttons.** A queued cell's button becomes a
   *stop* button; clicking again cancels it. Single click, in order.

---

## 5. Your Job, Next Agent — In Priority Order

The single biggest risk: **OCEANIQ's three pillars have never been connected, and
two have never run at all.** Detection is solid, but a spill mask is only the
*input* to backtracking, and backtracking output is only the *input* to
attribution. Detection alone took a full day and hit four real bugs — assume the
other two legs are not faster.

Convert unknowns into knowns before attempting integration.

### Task 1 — Prove the OpenDrift path (do this first)

Run OpenDrift's **own bundled example, backward in time**, using its **included
sample/test data**. Do **not** touch real forcing data yet. Goal is solely: does
the software path work, and does a backward run produce a sensible trajectory?

**Run it in Colab, not on the Windows machine.** OpenDrift pulls GDAL / cartopy /
netCDF4, which on Windows routinely needs conda. Colab installs them cleanly and
is where the model already lives.

Success = a backward run completes and plots a trajectory that moves in a
physically sensible direction. Nothing more.

### Task 2 — Prove the GFW path

**BLOCKED: ask the user for the GFW API token and the target demo region +
date window.** Neither exists in the repo or environment. Do not guess a token,
and do not fabricate a response.

Then run one query and confirm **real vessel data** returns. Show a sample of the
actual payload.

### Task 3 — Close the two gaps in Pillar 1

- Run notebook **cell 30** (look-alike screening against real model predictions).
  It has never produced output. Cell 28 loads the module fine; cell 30 has not
  been seen to run. Requires cells 2-20 re-run first to rebuild kernel state,
  then 28, 26, 30. Skip cell 22 (training) and cell 24 (needs dead `history`).
- Note `matplotlib` is imported in **cell 18** — skipping it makes cells 26/30
  die with `NameError: name 'plt' is not defined`.

### Task 4 — Only then, the integration contract

The riskiest unwritten piece is the **coordinate-system contract** between
pillars, and it is where this class of pipeline usually breaks:

- The model emits a **pixel mask on a 256x256 tile**. OpenDrift needs
  **lat/lon seed points**. Nothing today performs that georeferencing — the
  Deep-SAR dataset ships plain PNGs with **no geotransform metadata at all**.
  Decide early: source GeoTIFFs, or hand-place the demo scene at known coords.
- Define, in writing, what Pillar 1 hands Pillar 2 (seed polygon/points, CRS,
  timestamp) and what Pillar 2 hands Pillar 3 (origin bounding box + time window).

### Do not do

- Do not re-upload the dataset to Drive. Kaggle-direct is ~39s; the upload was
  heading for hours.
- Do not raise `NUM_CLASSES` to 5 — the labels do not exist. Step 0 will halt.
- Do not present the look-alike screening as a classifier, anywhere.
- Do not quote "3.47% oil pixels."

---

## 6. Status Summary

| Pillar | State | Blocker |
|---|---|---|
| 1. SAR spill detection | **Done** — 0.796 oil IoU, checkpoint on Drive | — |
| 1b. Look-alike screening | Code done + unit-tested; **unvalidated on real predictions** | Run cell 30 |
| 2. Backward drift (OpenDrift) | **Not started** | Not installed |
| 3. Vessel attribution (GFW) | **Not started** | **No API token from user** |
| 4. Scoring engine | Not started | Depends on 2 + 3 |
| 5. Dashboard | Not started | Depends on 4 |
| — | Georeferencing (px to lat/lon) | **Unowned, unwritten, blocks 1 to 2** |

**An end-to-end demo is not achievable today.** Realistic target: Tasks 1 and 2
above, which turn the two remaining unknowns into knowns and leave only the glue.
