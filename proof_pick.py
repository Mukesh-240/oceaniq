"""Re-read chosen masks from disk and print raw per-file numbers.

Counting matches the verified aggregate: channels are proven identical across
all 6,455 masks, so a 3-D mask is counted on channel 0 only. total_px is
therefore the single-channel pixel count; the raw array size is shown too so
the 3x inflation on 3-D files stays visible rather than hidden.
"""
import sys
import numpy as np
from PIL import Image

THRESH = 127
files = open('proof_files.txt').read().splitlines()

resolved = []            # (token, index_or_None)
for tok in sys.argv[1:]:
    if tok.isdigit():
        i = int(tok)
        resolved.append((tok, i if 0 <= i < len(files) else None))
    else:
        hits = [i for i, f in enumerate(files) if f.split(chr(92))[-1] == tok + '.png']
        resolved.append((tok, hits[0] if hits else None))

hdr = (f"{'#':>3} {'token':>14} {'idx':>5}  {'path':<44} {'dims':>15} {'D':>3} "
       f"{'uniq':>5} {'oil_px':>8} {'total_px':>9} {'array_sz':>9} {'frac':>8}")
print(hdr)
print('-' * len(hdr))

sum_oil = sum_tot = 0
n2d = n3d = 0
missing = []
for n, (tok, i) in enumerate(resolved, 1):
    if i is None:
        print(f"{n:>3} {tok:>14} {'--':>5}  !! DOES NOT EXIST - no substitution made")
        missing.append(tok)
        continue
    p = files[i]
    a = np.array(Image.open(p))
    ndim = a.ndim
    arr_sz = int(a.size)
    ch = a[:, :, 0] if ndim == 3 else a
    uniq = int(len(np.unique(ch)))
    oil = int((ch > THRESH).sum())
    tot = int(ch.size)
    sum_oil += oil
    sum_tot += tot
    n3d += (ndim == 3)
    n2d += (ndim == 2)
    print(f"{n:>3} {tok:>14} {i:>5}  {p:<44} {str(a.shape):>15} {ndim:>2}D "
          f"{uniq:>5} {oil:>8} {tot:>9} {arr_sz:>9} {oil/tot:>7.4f}")

print('-' * len(hdr))
print()
print("CHECK 1 - shape split across these 20 only")
n = n2d + n3d
print(f"  2-D: {n2d}/{n} = {100*n2d/n:.1f}%   (dataset-wide claim: 2455/6455 = 38.0%)")
print(f"  3-D: {n3d}/{n} = {100*n3d/n:.1f}%   (dataset-wide claim: 4000/6455 = 62.0%)")
print()
print("CHECK 2 - aggregate oil fraction across these 20 only")
print(f"  sum oil_px   = {sum_oil}")
print(f"  sum total_px = {sum_tot}")
print(f"  fraction     = {sum_oil/sum_tot:.6f} -> {100*sum_oil/sum_tot:.4f}%")
print(f"  (dataset-wide verified figure: 24.94%)")
if missing:
    print()
    print(f"MISSING / UNRESOLVED TOKENS: {missing}")
