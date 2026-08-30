"""Load one Deep-SAR image/mask pair, report shapes + classes, save a side-by-side plot."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

IMG = "data/deep-sar-sample/image/palsar_0.png"
MSK = "data/deep-sar-sample/mask/palsar_0.png"
OUT = "data/deep-sar-sample/sample_check.png"

# ponytail: both files are grayscale stored as 3 identical RGB channels -> convert("L")
img = np.array(Image.open(IMG).convert("L"))
msk = np.array(Image.open(MSK).convert("L"))
assert img.shape == msk.shape, f"image/mask dims differ: {img.shape} vs {msk.shape}"

print(f"image shape: {img.shape}  dtype={img.dtype}  range=[{img.min()}, {img.max()}]")
print(f"mask  shape: {msk.shape}  dtype={msk.dtype}")

vals, counts = np.unique(msk, return_counts=True)
print(f"mask unique class values (raw): {vals.tolist()}")
for v, c in zip(vals, counts):
    print(f"  value {v}: {c} px ({100 * c / msk.size:.2f}%)")

# raw mask is binary {0,255}; map to class ids {0,1} for training
labels = (msk > 127).astype(np.uint8)
print(f"mask unique class values (as labels): {np.unique(labels).tolist()}  "
      f"-> 0=background, 1=oil spill ({100 * labels.mean():.2f}% positive)")

fig, ax = plt.subplots(1, 2, figsize=(11, 5))
ax[0].imshow(img, cmap="gray")
ax[0].set_title(f"SAR image {img.shape}")
ax[1].imshow(labels, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
ax[1].set_title(f"mask {labels.shape}  classes={np.unique(labels).tolist()}")
for a in ax:
    a.axis("off")
fig.tight_layout()
fig.savefig(OUT, dpi=120)
print(f"saved -> {OUT}")
