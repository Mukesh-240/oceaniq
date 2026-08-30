# Rule-based look-alike screening: validation against real data

Run: `python validate_screen_ttom.py` against 1,200 real Sentinel-1 oil masks
from Trujillo-Acatitla et al. 2024 (Zenodo 8346860, CC-BY-4.0), 2048x2048,
binary. Every blob in those masks is ground-truth oil, so any non-"oil"
verdict is a mistake by definition.

## Result

| metric | value |
|---|---|
| blobs examined | 82,117 |
| kept as oil | 10,480 (12.76%) |
| discarded as noise | 68,802 (83.79%) |
| discarded as look-alike | 2,835 (3.45%) |
| **true oil AREA retained** | **99.493%** |
| per-mask retention | mean 99.28%, median 99.72%, min 84.17% |
| masks losing >10% of oil area | 2 of 1,200 |
| masks losing >50% of oil area | 0 of 1,200 |

The 87% blob-level discard rate looks alarming and is not: the discarded
blobs are speckle. Median area of a "noise" discard is 1 pixel; the whole
discarded population is 0.5% of oil area. The screener is removing
annotation and prediction speckle while keeping essentially all real oil.

## What this does NOT measure

The true-positive rate on real look-alikes. All 685 look-alike masks and all
685 no-oil masks in that dataset are entirely empty - it annotates oil only,
so a look-alike scene carries a blank mask and its geometry lives in the
imagery. Measuring "does this correctly flag an algal bloom as not-oil"
requires the 23 GB look-alike image archive.

At the measured 241 KB/s sustained to Zenodo, the three image archives
(40.7 + 23.0 + 22.9 GB) are about four days of downloading, so a trained
classifier was not attempted.

## Verdict

Keep the rule-based screener for the demo. It is measurably safe on the half
we can test - it costs 0.5% of true oil area - and the trained alternative is
not reachable within the time available. It remains labelled
"heuristic look-alike screening (rule-based, not a trained classifier)".
