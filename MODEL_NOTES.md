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

**RESOLVED by a live read of the checkpoint (2026-08-31).** The 15-epoch run
is real and its weights are the ones in Drive.

Raw output, verbatim, from a cell run against the live Colab runtime:

```
Mounted at /content/drive
exists   : True
size     : 97.9 MB
modified : 2026-08-30 07:07:36
keys     : ['model', 'epoch', 'miou', 'num_classes', 'class_names', 'encoder']
loaded epoch 14 | mIoU 0.8560
```

Screenshot: `golden_case/checkpoint_verification.png`.

**val mIoU 0.8560 is safe to present.** It is now backed by the checkpoint's
own embedded metadata, read live, not by recollection.

#### Ruled out: the file contains no per-class breakdown

Every key dumped with its value type, and recursed to depth 4 for any
per-class-shaped sequence (weights excluded):

```
type(ckpt): dict | n_keys = 6

model        OrderedDict  n_tensors=278  first3=['encoder.conv1.weight', ...]
epoch        int    repr=14
miou         float  repr=0.8560433387756348
num_classes  int    repr=2
class_names  list   repr=['background', 'oil spill']
encoder      str    repr='resnet34'

  -> 4 leaf values outside model
keys matching iou/class/metric/score/background/oil : ['miou','num_classes','class_names']
is per-class IoU present anywhere outside model? -> NO
```

`class_names` holds labels, not values. **There is no per-class IoU in the
checkpoint under any key, nested or otherwise.**

Two precisions that still matter:

- **The checkpoint stores `miou` only.** `background = 0.916` and
  `oil spill = 0.796` come from the `AGENT_LOG.md` transcription (commit
  `d3e35ae`, 2026-08-30 13:47:03), not from the file, and are confirmed absent
  from it by the scan above. They are one evidential tier below the 0.8560.
- **The earlier worry that a partial re-run overwrote the checkpoint was
  wrong.** The file's mtime is `2026-08-30 07:07:36` and it still holds epoch
  14, so the epochs 1-3 `<- best, saved` writes visible in the notebook's
  rendered output never replaced it. That rendered output is a *stale saved
  snapshot* of a different, earlier partial run - not the last thing that
  wrote this file.

### The other run, for the record

The notebook's rendered output shows a separate partial run: epochs 1-4, best
mIoU 0.8104 / oil spill 0.734 at epoch 3, ending in DataLoader shutdown
AssertionErrors. Its loss trajectory (train 0.2020 at epoch 4) and ~1m41s
epochs are consistent with the 15-epoch run that produced the checkpoint.

### What was searched

| location | result |
|---|---|
| local filesystem, `*.pth` / `*unet_resnet34*` | **no checkpoint**; every hit was an unrelated Python `.pth` path file in anaconda |
| `oil_spill_unet_colab.ipynb` (local) | 32 cells, **0 with stored outputs** — generated source, never round-tripped from Colab |
| Google Drive | **checkpoint EXISTS**: `oil_spill_runs/unet_resnet34_best.pth`, modified **Aug 30** |
| live Colab session, notebook `1y9D8G5FAq_7Ax1gOcL1nMv1VwuN-kZV4` | training cell output **still rendered** (a stale partial run), and the checkpoint read live — see above |

### Raw output of the stale partial run, verbatim

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

> On the Deep-SAR (Refined SOS) validation split of 1,615 tiles, U-Net +
> ResNet34 reached **val mIoU 0.8560 — verified from the checkpoint's own
> metadata, read live** (epoch 14 of 15, Colab T4, ~26 min). The
> background/oil-spill split is **reported as 0.916 / 0.796 in contemporaneous
> run logs — not independently reproduced, and not present in the checkpoint.**

**Never state the two at the same confidence.** TIER 1 is the mIoU: read out
of the artifact. TIER 2 is the per-class split: written down at the time by
whoever watched the run. If a judge asks specifically about oil-spill IoU, the
answer is "0.796 from the run log; we have not re-derived it" — not "0.796".

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
(Zhu et al., TGRS 2021), reports **mIoU 83.42%**. Our verified **0.8560**
slightly exceeds it. Expect to be asked how a stock U-Net beats the paper's
specialised architecture; the honest answer is that we train on the *refined*
masks, where roughly 38% of training and 50% of validation annotations were
manually corrected after that paper was published, so the two numbers are not
measured against identical ground truth. Do not claim architectural
superiority.

### Still not verified — OPEN, not closed

**Explicit status: the reproduction has NOT been run, and this is NOT being
treated as closed by the metadata read.**

Reading `ckpt['miou']` confirms *what the run recorded about itself*. It does
not recompute anything. If the run's own metric computation had a bug, the
checkpoint would faithfully store the wrong number and this check would not
notice. That is a real gap, not a formality.

What would actually close it: run `evaluate(model, val_dl)` from cell 8's
helper against these weights over the 1,615-tile val split, and compare the
returned mIoU to 0.8560 and the per-class vector to [0.916, 0.796]. That
single run would move **both** numbers to tier 1 and settle the per-class
figures, which no amount of metadata reading can.

Cost: dataset staging (~40s from Kaggle) plus one evaluation pass. On a GPU
runtime that is a couple of minutes; on CPU roughly 10-20 minutes. Nothing
blocks it except that it has not been done.

Until it is, the two-tier framing above stands.

### Blocked

Retraining itself is blocked on classifier reachability; this document is the
plan to execute once it is back.
