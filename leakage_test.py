"""Test whether Deep-SAR train and val tiles overlap.

SOS was built from only 21 original SAR scenes, expanded by cropping, rotation
and noise. No source documents a scene-level split. If tiles from the same
scene (or rotations of the same tile) land on both sides, the val split is not
independent and val mIoU overstates generalisation.

Cheap proxy: downscale every image to 16x16, quantise, hash. Identical hashes
across splits = duplicate/near-duplicate tiles. Also report nearest-neighbour
distance distribution for a sample.
"""
import glob
import hashlib
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

def sig(p):
    a = Image.open(p).convert('L').resize((16, 16), Image.BILINEAR)
    v = np.asarray(a, dtype=np.float32)
    q = (v / 8).astype(np.uint8)                  # coarse quantise
    return hashlib.md5(q.tobytes()).hexdigest(), v.ravel()

for kind in ('images', 'masks'):
    tr = sorted(glob.glob(f'oil_spill/oil_spill/{kind}/train/*.png'))
    va = sorted(glob.glob(f'oil_spill/oil_spill/{kind}/val/*.png'))
    with ThreadPoolExecutor(16) as ex:
        rt = list(ex.map(sig, tr)); rv = list(ex.map(sig, va))
    ht = set(x[0] for x in rt); hv = [x[0] for x in rv]
    dup = sum(1 for h in hv if h in ht)
    print(f'{kind:>7}: train={len(tr)} val={len(va)}  exact 16x16-hash collisions val-in-train: '
          f'{dup} ({100*dup/len(va):.2f}%)')

# nearest-neighbour distance, images only, sampled for speed
tr = sorted(glob.glob('oil_spill/oil_spill/images/train/*.png'))
va = sorted(glob.glob('oil_spill/oil_spill/images/val/*.png'))
with ThreadPoolExecutor(16) as ex:
    Vt = np.stack([x[1] for x in ex.map(sig, tr)])
    Vv = np.stack([x[1] for x in ex.map(sig, va)])
Vt /= (np.linalg.norm(Vt, axis=1, keepdims=True) + 1e-9)
Vv /= (np.linalg.norm(Vv, axis=1, keepdims=True) + 1e-9)
rng = np.random.default_rng(0)
idx = rng.choice(len(Vv), size=min(400, len(Vv)), replace=False)
sims = (Vv[idx] @ Vt.T).max(axis=1)
print()
print('cosine similarity of each sampled val tile to its NEAREST train tile (16x16 thumbs):')
for q in (50, 75, 90, 95, 99):
    print(f'   p{q:<3} {np.percentile(sims, q):.4f}')
print(f'   max  {sims.max():.4f}')
print(f'   val tiles with a train neighbour >0.99 similar: {(sims>0.99).sum()}/{len(sims)} '
      f'({100*(sims>0.99).mean():.1f}%)')
print(f'   val tiles with a train neighbour >0.95 similar: {(sims>0.95).sum()}/{len(sims)} '
      f'({100*(sims>0.95).mean():.1f}%)')
