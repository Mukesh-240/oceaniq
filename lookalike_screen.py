"""Heuristic look-alike screening for binary oil-spill segmentation masks.

NOT a trained classifier. These are hand-written shape rules applied to the
blobs a segmentation model already produced. They encode one domain
observation: wind- and current-driven oil slicks tend to be elongated with
ragged edges, while common SAR look-alikes (algal blooms, calm-water "black
holes", biogenic films) tend to be small, round and smooth.

The rules are a screening aid, not evidence. A real look-alike classifier needs
labelled look-alike examples -- the restricted-access Krestenitis/MKLab 5-class
dataset (sea / oil spill / look-alike / ship / land, mklab.iti.gr, by request).
That is future work.

Depends only on numpy + scipy.ndimage, both preinstalled in Colab.
"""

import numpy as np
from scipy import ndimage

LABEL = "heuristic look-alike screening (rule-based, not a trained classifier)"

# --- thresholds -------------------------------------------------------------
# Calibrated against synthetic discs/ellipses; see demo() at the bottom.
# Tune these on your own imagery -- they are the knobs, not the algorithm.
MIN_AREA_PX = 50            # below this, treat as speckle noise, not a detection
SMALL_AREA_PX = 600         # "small" for the round-and-smooth rule
ROUND_ELONGATION_MAX = 1.8  # <= this is "not elongated" (1.0 = circle)
SMOOTH_ROUGHNESS_MAX = 1.35 # <= this is "smooth-edged" (1.0 = perfect circle)


def _perimeter_px(blob):
    """Boundary-pixel count: blob pixels having at least one 4-neighbour outside.

    A digital approximation, and it reads LOW on smooth curves: a disc measures
    roughness ~0.86, not the textbook 1.0, because one boundary pixel can cover
    more than one unit of arc. Thresholds below are set from measured shapes for
    exactly this reason -- do not re-derive them from circularity theory.
    """
    p = np.pad(blob, 1)
    interior = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return int((blob & ~interior).sum())


def _elongation(ys, xs):
    """Major/minor axis ratio from second moments. 1.0 = round, higher = longer."""
    if len(ys) < 2:
        return 1.0
    cov = np.cov(np.stack([ys.astype(float), xs.astype(float)]))
    cov = np.atleast_2d(cov)
    if not np.all(np.isfinite(cov)):
        return 1.0
    eigs = np.linalg.eigvalsh(cov)
    lo, hi = float(max(eigs.min(), 0.0)), float(max(eigs.max(), 0.0))
    if hi <= 0:
        return 1.0
    if lo <= 1e-9:
        return float("inf")     # perfectly straight line: maximally elongated
    return float(np.sqrt(hi / lo))


def blob_features(mask):
    """One dict per connected blob: area, elongation, roughness.

    roughness = perimeter / perimeter of a circle of the same area.
    1.0 is a smooth disc; larger means a more ragged outline.
    """
    binary = np.asarray(mask) > 0
    labels, n = ndimage.label(binary)
    out = []
    for i in range(1, n + 1):
        blob = labels == i
        area = int(blob.sum())
        ys, xs = np.nonzero(blob)
        perim = _perimeter_px(blob)
        equiv = 2.0 * np.sqrt(np.pi * area)          # circle of equal area
        out.append({
            "label": i,
            "area_px": area,
            "elongation": round(_elongation(ys, xs), 3),
            "roughness": round(perim / equiv, 3) if equiv > 0 else 0.0,
            "perimeter_px": perim,
            "centroid_yx": (round(float(ys.mean()), 1), round(float(xs.mean()), 1)),
        })
    return labels, out


def classify(f,
             min_area_px=MIN_AREA_PX,
             small_area_px=SMALL_AREA_PX,
             round_elongation_max=ROUND_ELONGATION_MAX,
             smooth_roughness_max=SMOOTH_ROUGHNESS_MAX):
    """Three rules, in order. Returns (verdict, reason)."""
    if f["area_px"] < min_area_px:
        return "noise", f"area {f['area_px']}px < {min_area_px}px"

    if (f["elongation"] <= round_elongation_max
            and f["roughness"] <= smooth_roughness_max
            and f["area_px"] < small_area_px):
        return "look-alike", (
            f"round (elong {f['elongation']:.2f}), smooth (rough "
            f"{f['roughness']:.2f}), small ({f['area_px']}px)"
        )

    return "oil", (f"elong {f['elongation']:.2f}, rough {f['roughness']:.2f}, "
                   f"{f['area_px']}px")


def screen(mask, **thresholds):
    """Filter a binary prediction mask.

    Returns (kept_mask, blobs); kept_mask keeps only 'oil' blobs, and each blob
    dict carries 'verdict' and 'reason'.
    """
    labels, blobs = blob_features(mask)
    kept = np.zeros(labels.shape, dtype=np.uint8)
    for f in blobs:
        f["verdict"], f["reason"] = classify(f, **thresholds)
        if f["verdict"] == "oil":
            kept[labels == f["label"]] = 1
    return kept, blobs


def report(blobs, max_rows=20):
    """Plain-text summary. Always names the method, so downstream output cannot
    accidentally present this as a trained classifier's result."""
    header = LABEL.upper()
    if not blobs:
        return f"{header}\n0 blobs detected"
    counts = {}
    for f in blobs:
        counts[f["verdict"]] = counts.get(f["verdict"], 0) + 1
    lines = [
        header,
        f"{len(blobs)} blobs: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())),
        f"{'id':>3} {'area':>7} {'elong':>6} {'rough':>6}  verdict",
    ]
    for f in sorted(blobs, key=lambda b: -b["area_px"])[:max_rows]:
        lines.append(f"{f['label']:>3} {f['area_px']:>7} {f['elongation']:>6.2f} "
                     f"{f['roughness']:>6.2f}  {f['verdict']}")
    if len(blobs) > max_rows:
        lines.append(f"... {len(blobs) - max_rows} more")
    return "\n".join(lines)


def demo():
    """Self-check on synthetic shapes. Run: python lookalike_screen.py"""
    def disc(canvas, cy, cx, r):
        ys, xs = np.ogrid[:canvas.shape[0], :canvas.shape[1]]
        canvas[(ys - cy) ** 2 + (xs - cx) ** 2 <= r * r] = 1
        return canvas

    def ellipse(canvas, cy, cx, ry, rx):
        ys, xs = np.ogrid[:canvas.shape[0], :canvas.shape[1]]
        canvas[((ys - cy) / ry) ** 2 + ((xs - cx) / rx) ** 2 <= 1] = 1
        return canvas

    rng = np.random.default_rng(0)

    # 1. small smooth disc -> look-alike (algae / calm water)
    m = disc(np.zeros((200, 200), np.uint8), 100, 100, 12)
    _, b = blob_features(m)
    v, _ = classify(b[0])
    assert v == "look-alike", (v, b[0])
    print(f"1. small disc    area={b[0]['area_px']:5d} elong={b[0]['elongation']:.2f} "
          f"rough={b[0]['roughness']:.2f} -> {v}")

    # 2. long thin ellipse -> oil (wind-driven slick)
    m = ellipse(np.zeros((200, 200), np.uint8), 100, 100, 6, 60)
    _, b = blob_features(m)
    v, _ = classify(b[0])
    assert v == "oil", (v, b[0])
    print(f"2. long ellipse  area={b[0]['area_px']:5d} elong={b[0]['elongation']:.2f} "
          f"rough={b[0]['roughness']:.2f} -> {v}")

    # 3. large round blob -> oil (round, but too big to dismiss)
    m = disc(np.zeros((200, 200), np.uint8), 100, 100, 40)
    _, b = blob_features(m)
    v, _ = classify(b[0])
    assert v == "oil", (v, b[0])
    print(f"3. big disc      area={b[0]['area_px']:5d} elong={b[0]['elongation']:.2f} "
          f"rough={b[0]['roughness']:.2f} -> {v}")

    # 4. SMALL ragged blob -> oil. Round and under SMALL_AREA_PX, so only the
    #    roughness rule can save it: this is the test that the roughness term
    #    actually does work, rather than size quietly carrying every case.
    base = disc(np.zeros((200, 200), np.uint8), 100, 100, 9).astype(bool)
    ring = ndimage.binary_dilation(base, iterations=3) & ~ndimage.binary_erosion(base)
    m = (base | (ring & (rng.random(base.shape) < 0.55))).astype(np.uint8)
    labels, b = blob_features(m)
    big = max(b, key=lambda x: x["area_px"])
    assert big["area_px"] < SMALL_AREA_PX, f"test is not exercising roughness: {big}"
    assert big["elongation"] <= ROUND_ELONGATION_MAX, f"test blob is elongated: {big}"
    v, _ = classify(big)
    assert v == "oil", (v, big)
    assert big["roughness"] > SMOOTH_ROUGHNESS_MAX, big
    print(f"4. ragged blob   area={big['area_px']:5d} elong={big['elongation']:.2f} "
          f"rough={big['roughness']:.2f} -> {v}  (small+round; kept on roughness alone)")

    # 5. speck -> noise
    m = np.zeros((200, 200), np.uint8)
    m[10:14, 10:14] = 1
    _, b = blob_features(m)
    v, _ = classify(b[0])
    assert v == "noise", (v, b[0])
    print(f"5. speck         area={b[0]['area_px']:5d} -> {v}")

    # 6. end to end: slick + algae disc + speck -> only the slick survives
    m = np.zeros((300, 300), np.uint8)
    m = ellipse(m, 80, 150, 7, 70)      # slick
    m = disc(m, 220, 80, 11)            # algae
    m[280:284, 280:284] = 1             # speck
    kept, blobs = screen(m)
    verdicts = sorted(f["verdict"] for f in blobs)
    assert verdicts == ["look-alike", "noise", "oil"], verdicts
    assert 0 < kept.sum() < m.sum()
    print(f"6. mixed scene   {m.sum()}px in -> {kept.sum()}px kept ({verdicts})")
    print()
    print(report(blobs))
    print()
    print("ALL LOOK-ALIKE SCREENING CHECKS PASSED")


if __name__ == "__main__":
    demo()
