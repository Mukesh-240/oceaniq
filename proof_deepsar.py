import glob, time, numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

t0 = time.time()
files = sorted(glob.glob('oil_spill/oil_spill/masks/train/*.png'))
print("glob pattern : oil_spill/oil_spill/masks/train/*.png")
print("files found  :", len(files))
print("first file   :", files[0] if files else "NONE")
print("last file    :", files[-1] if files else "NONE")

def stats(p):
    a = np.array(Image.open(p))
    pos = int((a > 127).sum()) if a.max() > 1 else int((a > 0).sum())
    return pos, int(a.size)

with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(stats, files))

pos = np.array([r[0] for r in res], dtype=np.int64)
tot = np.array([r[1] for r in res], dtype=np.int64)
frac = pos / tot

print()
print("total oil pixels     :", int(pos.sum()))
print("total pixels         :", int(tot.sum()))
print("GLOBAL oil fraction  : %.6f  -> %.4f%%" % (pos.sum()/tot.sum(), 100*pos.sum()/tot.sum()))
print("per-image mean       : %.6f  -> %.4f%%" % (frac.mean(), 100*frac.mean()))
print("per-image median     : %.6f  -> %.4f%%" % (np.median(frac), 100*np.median(frac)))
print("masks containing oil : %d / %d = %.4f%%" % ((pos>0).sum(), len(pos), 100*(pos>0).mean()))
print("background:oil ratio : %.4f : 1" % ((tot.sum()-pos.sum())/pos.sum()))
print()
print("elapsed seconds      : %.2f" % (time.time()-t0))
np.save('proof_pos.npy', pos); np.save('proof_tot.npy', tot)
with open('proof_files.txt','w') as f: f.write("\n".join(files))
print("saved: proof_pos.npy proof_tot.npy proof_files.txt")
