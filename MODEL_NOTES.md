# Model Notes

Planning notes for segmentation retraining. No training has been run against
these; see "Blocked" at the end.

Screener validation is deliberately **not** covered here — that lives in
`SCREENING_VALIDATION.md` and stays scoped to the rule-based screener.

## Model Retraining — Revised Imbalance

### Revised class balance

**Oil is 24.9% of pixels in the training set, not 3.5%.** The 3.5% premise is
**superseded**, not averaged with the new figure.

Measured directly, no sampling:

| dataset | masks | oil pixels (mean) | median | background : oil |
|---|---|---|---|---|
| **Deep-SAR `masks/train`** — what the model trains on | 6,455 | **24.94%** | 17.94% | **3.0 : 1** |
| TTOM `Mask_oil` (Zenodo 8346860) | 1,200 | 2.98% | 1.76% | 32.6 : 1 |

#### The two numbers are both real, and belong to different datasets

This is the trap to avoid repeating. The **24.9% figure comes from the 6,455
Deep-SAR training masks** — the data the checkpoint was actually fitted on. It
does **not** come from the 1,200 TTOM oil masks; those measure **2.98%**, which
is essentially the original 3.5% figure.

So the old number was never fabricated. It describes a *different dataset* than
the one we train on. Any future statement about class balance must name the
dataset it refers to, because the two differ by an order of magnitude
(3.0 : 1 versus 32.6 : 1) and imply opposite loss-weighting decisions.

The original 3.47% claim also had a separate provenance problem, already
recorded in `handoff.md`: it was taken from a single image.

#### Why the two differ: sampling methodology, checked not inferred

The gap is **an artefact of how Deep-SAR was built**, not a disagreement about
how much oil is in the ocean. Documented chain:

- **Kaggle card** (`bakhtiyar2222/deep-sar-oil-spill-segmentation-refined`,
  CC BY 4.0) states the classes are "Oil spill / Ocean" and credits
  Zhu et al., source DOI `10.5281/zenodo.15298010`.
- **Zenodo 15298010** confirms it is the *Refined* Deep-SAR Oil Spill (SOS)
  dataset, derived from Zhu et al., IEEE TGRS 2021,
  DOI `10.1109/TGRS.2021.3115492`.
- **The SOS dataset** was built from **21 original SAR scenes**, expanded by
  "cropping, rotation, and noise addition" into 8,070 patches of 256x256. The
  scenes cover the **Gulf of Mexico** and the **Persian Gulf** — two areas
  selected *because* they contain known spills. Annotation came from "manual
  interpretation and GIS expert sampling ... with optimizations addressing
  class imbalance."
- The authors' own repo (`CUG-URS/CBDNet-main`) confirms the split counts —
  Gulf of Mexico 3,101 train / 776 test, Persian Gulf 3,354 train / 839 test —
  which match our file listing exactly (palsar 3,101, sentinel 3,354).

Neither the Kaggle card, the Zenodo record, the authors' README, nor the TGRS
abstract states a crop *stride* or explicit "crop-to-object" rule; the TGRS
full text is paywalled. What is documented is that the tiles come from 21
spill-bearing scenes and that sampling was optimised for class balance.

Measured on disk, consistent with that:

| split | tiles | oil pixels | tiles containing oil | tiles with zero oil |
|---|---|---|---|---|
| train | 6,455 | 24.94% | **96.05%** | 255 |
| val | 1,615 | 27.05% | **95.29%** | 76 |

A uniform survey of ocean would produce mostly empty tiles. 96% of tiles
containing oil is the signature of spill-centric selection. **TTOM, by
contrast, annotates whole Sentinel-1 scenes — which is why it reads 2.98%.**

**Consequence: 24.94% is a property of the training set, not an operating
prior.** At inference over broad SAR scenes, expect something nearer TTOM's
~3%, and often zero.

#### Where the stale language lives

A repo-wide grep for `3.5%`, `3.47`, `rare class`, `class imbalance`,
`severe imbalance` and `1:28` across `.md`, `.py`, `.ipynb`, `.json`, `.html`
and `.txt` turned up **no file asserting the old premise**. The only matches are:

- `handoff.md:18` and `handoff.md:325` — these already *correct* the 3.47%
  figure rather than repeat it. Their cited "400-mask sample: median 17.7%,
  mean 24.6%" is consistent with, and now superseded by, the full 6,455-mask
  measurement above (median 17.94%, mean 24.94%).
- `fixtures/transpose_target.json:31` — a false positive; `1:28` matched a
  timestamp.

A pitch deck **does** exist, inside `files.zip` at the repo root — which is
gitignored, so the earlier grep missed it. Checked directly:
`OCEANIQ-pitch-doc.pdf` (4 pages), `OCEANIQ-pitch-doc.html`,
`OCEANIQ-final-hackathon-POC.md`, `OCEANIQ-internal-round-1day.md`. Searched
for `3.5%`, `3.47`, `rare class`, `imbalance`, `1:28`, `class weight`, `24.9`:
**zero hits in any of them.** No pitch language needs updating.

Anything outside version control (slides in Drive, submission portal text) is
still not greppable from here and needs checking by hand.

### Loss function recommendation

At a measured **3.0 : 1** background-to-oil ratio on Deep-SAR:

- **Recommended:** weighted BCE **or** Dice loss with a class weight of about
  **1 : 3** in favour of oil.
- **Superseded:** the ~**1 : 28** weight the 3.5% premise implied. That weight
  is roughly correct for TTOM's 32.6 : 1 distribution, and roughly ten times
  too aggressive for the data we actually train on.

**Recommended against at this prevalence:**

- **Focal loss** — it is designed for genuinely rare positives, and at 3 : 1 it
  overcorrects: down-weighting easy negatives here pushes the model to
  over-predict oil, which costs precision on look-alike and no-oil regions.
- **Aggressive oversampling of oil-containing patches** — same overcorrection,
  and largely a no-op regardless: 96% of Deep-SAR training masks already
  contain oil, so there is almost nothing to oversample.

### Correcting for the sampling bias

The 1:3 weight above is correct **for the training loss**, because the
optimiser only ever sees the training distribution. Do **not** reweight the
loss to a ~1:32 deployment prior — that fights the data you actually have and
destabilises training. The bias is corrected at inference instead:

1. **Shift the decision threshold, not the loss.** Going from a 24.94%
   training prior to a ~2.98% scene prior is a prior-odds shift of **10.8x**.
   For a logit-output model that is a **logit adjustment of +2.38** subtracted
   from the oil logit at inference:

   `logit(0.2494) = -1.1018`, `logit(0.0298) = -3.4830`, difference **2.3812**

   Equivalently, tune the threshold on held-out data drawn from the deployment
   distribution rather than leaving it at 0.5.

2. **Measure the false-positive rate on oil-free ocean before trusting it.**
   The model has seen almost none: only **255 of 6,455** training tiles contain
   zero oil. We already hold a ready-made negative set locally — the **685 TTOM
   `Mask_no_oil` masks, every one of them empty** (`ttom_masks/`, re-downloadable
   in ~30s). Any positive prediction there is a false positive, and that number
   is currently unknown.

3. **Treat the current headline metrics as in-distribution only.** Whichever
   figure you quote — see "Metrics provenance" below, the two runs are not
   equally evidenced — it was measured on a val split that is
   **95.29% oil-bearing tiles at 27.05% oil pixels** — the same biased
   construction as train. Those figures should not be quoted as expected
   performance on broad SAR scenes.

## Metrics provenance — what is actually evidenced

**Two different runs exist, and the evidence for each is of a different
quality.** Read this before quoting any number.

| run | evidence | strength |
|---|---|---|
| **15-epoch run** — mIoU **0.8560**, oil spill **0.796** | `AGENT_LOG.md`, committed `d3e35ae` 2026-08-30 13:47:03, transcribed cell output incl. `done: ran all 15 epochs, 0h25m53s elapsed` and `(fresh kernel) loaded epoch 14 | mIoU 0.8560` | **contemporaneous transcription, no surviving primary output** |
| **partial re-run** — best mIoU **0.8104**, oil spill **0.734** at epoch 3, crashed at epoch 4 | the output **still rendered in the live Colab notebook** (screenshots below) | **primary artifact** |

These do not contradict each other — they are separate runs. The later partial
run overwrote the displayed output of the earlier complete one.

**The risk this creates:** the partial re-run printed `<- best, saved` at
epochs 1, 2 and 3, meaning it wrote its own checkpoints to the same path. The
file now in Drive may therefore be the **epoch-3 / 0.8104** checkpoint, not the
epoch-14 / 0.8560 one. Which it is has not been established.

**Recommended posture for judges:** quote **0.8104 / 0.734** if you want a
number backed by output you can show on screen. Quoting 0.8560 / 0.796 is
defensible only as "recorded at the time, primary output since overwritten" —
and should not be paired with a live demo of the checkpoint until its embedded
`epoch` / `miou` fields have been read back.

### What was searched

| location | result |
|---|---|
| local filesystem, `*.pth` / `*unet_resnet34*` | **no checkpoint**; every hit was an unrelated Python `.pth` path file in anaconda |
| `oil_spill_unet_colab.ipynb` (local) | 32 cells, **0 with stored outputs** — generated source, never round-tripped from Colab |
| Google Drive | **checkpoint EXISTS**: `oil_spill_runs/unet_resnet34_best.pth`, modified **Aug 30** |
| live Colab session, notebook `1y9D8G5FAq_7Ax1gOcL1nMv1VwuN-kZV4` | training cell output **still rendered** — this is the only surviving metrics artifact |

### Raw output, verbatim from the Colab cell

```
GPU        : Tesla T4
reading    : /content/oil_spill/images/train  (local disk)
train/val  : 6455 / 1615 pairs
limits     : 15 epochs or 3.0h, whichever comes first
checkpoint : /content/drive/MyDrive/oil_spill_runs/unet_resnet34_best.pth

epoch   1 | train 0.2746 | val 0.2372 | mIoU 0.7471 | 0h01m39s | total 0h01m39s  <- best, saved
        IoU: background=0.840  oil spill=0.654
epoch   2 | train 0.2290 | val 0.1822 | mIoU 0.8087 | 0h01m43s | total 0h03m23s  <- best, saved
        IoU: background=0.886  oil spill=0.731
epoch   3 | train 0.2144 | val 0.1870 | mIoU 0.8104 | 0h01m41s | total 0h05m04s  <- best, saved
        IoU: background=0.887  oil spill=0.734
epoch   4 | train 0.2020 | val 0.2245 | mIoU 0.7634 | 0h01m41s | total 0h06m45s
        IoU: background=0.849  oil spill=0.678
[then repeated _MultiProcessingDataLoaderIter.__del__ AssertionError tracebacks]
```

Screenshots: `golden_case/colab_training_output0.png`, `…output.png`, `…output2.png`.

This rendered run **stops at epoch 4**, with no `best val mIoU = …` summary
line, and the "Training curves" cell below shows `[ ]` — never executed. Its
loss trajectory is consistent with the logged 15-epoch run continuing from
here (train 0.2020 at epoch 4 -> 0.1486 at epoch 14), and its ~1m41s epochs
match the logged `0h25m53s` for 15 epochs.

### Defensible statement for judges

> On the Deep-SAR (Refined SOS) validation split of 1,615 tiles, a U-Net with
> a ResNet34 ImageNet encoder reached **mIoU 0.8104** (background 0.887,
> oil spill 0.734) at epoch 3 on a Colab T4, ~1m41s per epoch.

That is the strongest claim backed by output that can be shown on screen. A
completed 15-epoch run reaching **0.8560 / 0.796** is recorded in
`AGENT_LOG.md` at the time it happened, but its primary output no longer
exists.

### What "val" means here

The 1,615 pairs are the SOS dataset's own **test split** (776 Gulf of Mexico +
839 Persian Gulf), matching the authors' published counts. The training loader
never reads them, so there is no direct train-on-val contamination.

**Leakage risk is real but showed no evidence.** All 8,070 tiles derive from
only 21 original scenes via cropping, rotation and noise, and no source
documents a scene-level split. Tested with 16x16 thumbnail nearest-neighbour
similarity (`leakage_test.py`):

| comparison | median cosine | frac > 0.99 |
|---|---|---|
| random unrelated train-train pairs | 0.9675 | 8.6% |
| train tile -> nearest *other train* tile | 0.9927 | 64.8% |
| **val tile -> nearest train tile** | **0.9931** | **62.3%** |

Val is no closer to train than train is to itself, so the high absolute
similarity is generic SAR-texture, not duplication. Zero exact image-hash
collisions across splits. **This test is weak** — it cannot detect a val tile
that partially overlaps a train tile's footprint, or a rotated crop of the same
region. Scene-level independence remains undocumented and unproven.

### Sanity check against the published benchmark

CBD-Net, the purpose-built network from the paper that introduced SOS
(Zhu et al., TGRS 2021), reports **mIoU 83.42%** on this dataset. The observed
**0.8104** sits just below it — exactly where a stock U-Net/ResNet34 baseline
should land. The unsupported **0.856** would mean a 26-minute off-the-shelf
baseline *beat* the paper's specialised architecture, which should not be
claimed without an artifact. (The refined masks could plausibly lift scores
above the original paper, so it is not impossible — merely unevidenced.)

### Live re-run: attempted, blocked

The checkpoint exists in Drive, so re-evaluating is possible in principle.
Reconnecting the Colab runtime stalled at "Connecting" for 85+ seconds with
`Could not connect to the reCAPTCHA service` — Colab gates runtime allocation
behind reCAPTCHA, which fails under browser automation. **A human on a normal
browser can do this**: reconnect the runtime, re-run the config and data cells,
then the checkpoint-reload cell, which prints
`loaded epoch {ckpt['epoch']} | mIoU {ckpt['miou']:.4f}` — the checkpoint's own
embedded metadata, which will settle whether a 15-epoch run ever completed.

### Blocked

Retraining itself is blocked on classifier reachability; this document is the
plan to execute once it is back.
