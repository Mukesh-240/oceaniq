"""Validate the rule-based look-alike screener against real TTOM oil masks.

What this CAN measure: how often the heuristic wrongly discards a REAL oil
blob (false-discard rate). Every blob in Mask_oil is ground-truth oil, so any
"look-alike" or "noise" verdict there is a mistake.

What this CANNOT measure: the true-positive rate on real look-alikes. The
TTOM look-alike masks are all empty - that dataset marks oil only, so a
look-alike scene has a blank mask and its geometry lives in the 23 GB of
imagery we could not download. No shape-only test can substitute for it.
"""
import glob
import sys
from collections import Counter

import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, ".")
from lookalike_screen import blob_features, classify  # noqa: E402

MASKS = sorted(glob.glob("ttom_masks/Mask_oil/*.tif"))


def one(path):
    a = (np.array(Image.open(path)) > 0).astype(np.uint8)
    _, blobs = blob_features(a)
    out, kept, tot = [], 0, 0
    for f in blobs:
        v, _ = classify(f)
        out.append((v, f["area_px"], f["elongation"], f["roughness"]))
        tot += f["area_px"]
        if v == "oil":
            kept += f["area_px"]
    # per-mask retention: a good average can still hide a scene wiped out entirely
    return out, (kept / tot if tot else 1.0)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(MASKS)
    files = MASKS[:n]
    print(f"screening {len(files)} real oil masks (2048x2048, ground truth = all oil)\n")
    rows = []
    with ProcessPoolExecutor() as ex:
        per_mask = []
        for i, (res, ret) in enumerate(ex.map(one, files, chunksize=8)):
            rows.extend(res)
            per_mask.append(ret)
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(files)} masks, {len(rows)} blobs")

    verdicts = Counter(r[0] for r in rows)
    total = len(rows)
    print(f"\nblobs found: {total}")
    for v, c in verdicts.most_common():
        print(f"  {v:<12} {c:>7}  {100*c/total:5.2f}%")

    wrong = verdicts["look-alike"] + verdicts["noise"]
    print(f"\nfalse-discard rate on REAL oil: {100*wrong/total:.2f}% of blobs")

    kept_area = sum(r[1] for r in rows if r[0] == "oil")
    all_area = sum(r[1] for r in rows)
    print(f"oil AREA retained: {100*kept_area/all_area:.3f}% "
          f"({all_area - kept_area:,} of {all_area:,} px discarded)")

    for label in ("look-alike", "noise"):
        sub = [r for r in rows if r[0] == label]
        if sub:
            a = np.array([r[1] for r in sub])
            print(f"\ndiscarded as {label}: n={len(sub)} "
                  f"area median={np.median(a):.0f}px max={a.max()}px")

    pm = np.array(per_mask)
    print()
    print(f"per-mask oil area retained: mean={100*pm.mean():.2f}% "
          f"median={100*np.median(pm):.2f}% min={100*pm.min():.2f}%")
    print(f"masks losing >10% of their oil area: {(pm < 0.90).sum()} of {len(pm)}")
    print(f"masks losing >50% of their oil area: {(pm < 0.50).sum()} of {len(pm)}")
