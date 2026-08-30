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

**No pitch deck or problem-statement file exists in this repo.** If deck or
abstract language citing 3.5% or "rare class" exists outside version control
(slides, submission portal, printed problem statement), it is not greppable
from here and needs checking by hand.

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

### Blocked

Retraining itself is blocked on classifier reachability; this document is the
plan to execute once it is back.
