"""Generate pipeline_end_to_end.ipynb - the first real integration of pillars 1 + 2.

    python tools/build_pipeline_nb.py pipeline_end_to_end.ipynb

Chain: predicted mask -> look-alike screening -> lat/lon seeds -> OpenDrift
backward -> origin bbox + time window -> fixtures/*.json for Agent B.

Embeds lookalike_screen.py and tools/spill_to_seeds.py at build time so the
notebook is self-contained in Colab while the repo keeps one source of truth.
"""

import json, ast, sys
from pathlib import Path

_look = Path("lookalike_screen.py")
_seeds = Path("tools/spill_to_seeds.py")
assert _look.is_file() and _seeds.is_file(), "run from the project root"

LOOK_SRC = _look.read_text(encoding="utf-8").split("def demo():")[0].rstrip()
SEEDS_SRC = _seeds.read_text(encoding="utf-8").split("if __name__")[0].rstrip()

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}


def code(s):
    src = s.strip("\n")
    ast.parse("".join(l for l in src.splitlines(keepends=True) if not l.lstrip().startswith(("!", "%"))))
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}


cells = []

cells.append(md("""
# OCEANIQ — end-to-end pipeline (pillars 1 -> 2)

**First real integration.** Everything so far has been proven in isolation. This
runs one scene through the actual chain:

```
SAR image -> U-Net mask -> look-alike screening -> lat/lon seeds
          -> OpenDrift BACKWARD -> origin bbox + time window -> fixtures/*.json
```

The JSON it writes is the Pillar 1->2 and 2->3 payload defined in
`contracts/georeferencing.json`, and it unblocks Agent B's scoring engine.

---

## Two honest placeholders — read before quoting any result

**1. Geography is a placeholder.** The only forcing data available today is
OpenDrift's bundled **NorKyst sample (western Norway)**. The demo transform would
place the spill in the Arabian Sea, where we have no currents — particles would
not move at all. So the anchor is set **inside the NorKyst domain** (~4.9E,
60.0N) to prove the plumbing.

Swapping in real geography is a **config change, not a rewrite**: obtain CMEMS
currents for Indian waters, set `ANCHOR_LON/ANCHOR_LAT` to the true scene corner,
point the reader at the CMEMS file.

**2. Georeferencing is Path B.** Assumed anchor and pixel size, not a real
geotransform — the Deep-SAR PNGs carry none. **State this on the slide.**

Setup: GPU runtime, and Kaggle secrets (`KAGGLE_USERNAME`, `KAGGLE_KEY`) with
Notebook access **ON for this notebook** — that toggle is per-notebook.
"""))

cells.append(md("## 1. Install"))
cells.append(code("""
!pip install -q "segmentation-models-pytorch>=0.3.4" "albumentations>=1.4,<2.0" opendrift

import torch, opendrift
print("torch", torch.__version__, "| cuda", torch.cuda.is_available())
print("opendrift", opendrift.__version__)
"""))

cells.append(md("## 2. Mount Drive (auto-retrying)"))
cells.append(code('''
from google.colab import drive
import os, time

def mount_drive(attempts=4, wait=6):
    """drive.mount() fails intermittently with a bare ValueError('mount failed');
    it succeeds on a plain retry. Retry rather than stall a live demo."""
    for i in range(1, attempts + 1):
        if os.path.isdir("/content/drive/MyDrive"):
            print("Drive already mounted"); return
        try:
            drive.mount("/content/drive", force_remount=(i > 1))
            print(f"Drive mounted (attempt {i})"); return
        except Exception as e:
            print(f"  attempt {i}/{attempts}: {type(e).__name__}: {e}")
            if i < attempts: time.sleep(wait)
    raise RuntimeError("Drive mount failed - re-run this cell")

mount_drive()
'''))

cells.append(md("## 3. Config"))
cells.append(code('''
from pathlib import Path

CKPT_PATH = Path("/content/drive/MyDrive/oil_spill_runs/unet_resnet34_best.pth")
KAGGLE_DATASET = "bakhtiyar2222/deep-sar-oil-spill-segmentation-refined"
RAW_DIR, DATA_ROOT = Path("/content/raw"), Path("/content/oil_spill")
FIXTURES = Path("/content/fixtures"); FIXTURES.mkdir(exist_ok=True)

# --- PLACEHOLDER GEOGRAPHY: inside the NorKyst sample domain so drift works ---
ANCHOR_LON, ANCHOR_LAT = 4.85, 60.05
PIXEL_SIZE_DEG = 0.0001          # ~11 m/px, Sentinel-1 GRD order of magnitude

# For real Indian waters (needs CMEMS currents first):
# ANCHOR_LON, ANCHOR_LAT = 69.10, 18.52

DRIFT_HOURS = 12
MAX_SEEDS = 300
print("anchor:", ANCHOR_LON, ANCHOR_LAT, "| PLACEHOLDER geography")
'''))

cells.append(md("## 4. Get the data and the trained model"))
cells.append(code('''
import os, shutil
from google.colab import userdata

os.environ["KAGGLE_USERNAME"] = userdata.get("KAGGLE_USERNAME")
os.environ["KAGGLE_KEY"] = userdata.get("KAGGLE_KEY")

if not (DATA_ROOT / "images" / "val").is_dir():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    print("downloading dataset...")
    api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DIR), unzip=True, quiet=False)
    for kind in ("images", "masks"):
        for split in ("train", "val"):
            src = RAW_DIR / kind / kind / split
            dst = DATA_ROOT / kind / split
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir() and not dst.exists():
                shutil.move(str(src), str(dst))
print("val images:", len(list((DATA_ROOT / "images" / "val").iterdir())))

assert CKPT_PATH.exists(), f"checkpoint not found: {CKPT_PATH}"
print("checkpoint:", CKPT_PATH, f"({CKPT_PATH.stat().st_size/1e6:.0f} MB)")
'''))

cells.append(md("## 5. Look-alike screening module (embedded from `lookalike_screen.py`)"))
cells.append(code(LOOK_SRC))

cells.append(md("## 6. Pixel to lat/lon (embedded from `tools/spill_to_seeds.py`)"))
cells.append(code(SEEDS_SRC))

cells.append(md("""
## 7. STEP 1 — detect: run the trained model on a real SAR image
"""))
cells.append(code('''
import numpy as np, torch
from PIL import Image
import segmentation_models_pytorch as smp

ENCODER, NUM_CLASSES = "resnet34", 2
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
params = smp.encoders.get_preprocessing_params(ENCODER, "imagenet")
MEAN, STD = np.array(params["mean"]), np.array(params["std"])

model = smp.Unet(ENCODER, encoder_weights=None, in_channels=3,
                 classes=NUM_CLASSES, activation=None).to(DEVICE)
ck = torch.load(CKPT_PATH, map_location=DEVICE, weights_only=False)
model.load_state_dict(ck["model"]); model.eval()
print(f"loaded checkpoint: epoch {ck['epoch']} | mIoU {ck['miou']:.4f}")

val_imgs = sorted((DATA_ROOT / "images" / "val").iterdir())
chosen, pred = None, None
for p in val_imgs[:40]:                      # find a scene with real oil in it
    img = np.array(Image.open(p).convert("RGB"))
    x = ((img / 255.0 - MEAN) / STD).transpose(2, 0, 1)[None].astype("float32")
    with torch.no_grad():
        logits = model(torch.from_numpy(x).to(DEVICE))
    m = (logits.argmax(1)[0].cpu().numpy() == 1).astype(np.uint8)
    if 0.02 < m.mean() < 0.45:
        chosen, pred = p, m
        break

assert chosen is not None, "no suitable validation scene found"
print(f"scene: {chosen.name}")
print(f"predicted oil pixels: {int(pred.sum())} ({100*pred.mean():.2f}% of tile)")
'''))

cells.append(md("## 8. STEP 2 — screen out look-alikes"))
cells.append(code('''
kept, blobs = screen(pred * 255)
print(report(blobs))
print()
before, after = int(pred.sum()), int(kept.sum())
print(f"pixels before screening: {before}")
print(f"pixels after screening : {after}")
print(f"removed by screening   : {before-after} ({100*(before-after)/max(1,before):.1f}%)")
assert after > 0, "screening removed everything - loosen thresholds"
'''))

cells.append(md("""
## 9. STEP 3 — georeference: mask to lat/lon seed points (Pillar 1 -> 2 contract)
"""))
cells.append(code('''
import json, glob, urllib.request
from datetime import timezone
from opendrift.readers import reader_netCDF_CF_generic
import opendrift

NC_NAME, SUBDIR = "norkyst800_subset_16Nov2015.nc", "16Nov2015_NorKyst_z_surface"
def find_sample():
    roots = []
    tdf = getattr(opendrift, "test_data_folder", None)
    if isinstance(tdf, str): roots.append(tdf)
    pkg = os.path.dirname(opendrift.__file__)
    roots += [os.path.join(pkg, "..", "tests", "test_data"), "/content/opendrift_test_data"]
    for r in roots:
        hits = glob.glob(os.path.join(r, "**", NC_NAME), recursive=True)
        if hits: return hits[0]
    return None

nc = find_sample()
if nc is None:
    d = os.path.join("/content/opendrift_test_data", SUBDIR); os.makedirs(d, exist_ok=True)
    nc = os.path.join(d, NC_NAME)
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/OpenDrift/opendrift/master/"
        f"tests/test_data/{SUBDIR}/{NC_NAME}", nc)
reader = reader_netCDF_CF_generic.Reader(nc)

OBSERVED_TIME = reader.end_time
transform = get_demo_transform(ANCHOR_LON, ANCHOR_LAT, PIXEL_SIZE_DEG)
seeds = mask_to_seed_points(kept * 255, transform,
                            OBSERVED_TIME.replace(tzinfo=timezone.utc).isoformat())[:MAX_SEEDS]

lons = [s["lon"] for s in seeds]; lats = [s["lat"] for s in seeds]
print(f"seed points: {len(seeds)}")
print(f"  lon {min(lons):.4f} -> {max(lons):.4f}")
print(f"  lat {min(lats):.4f} -> {max(lats):.4f}")
print(f"  observed at {OBSERVED_TIME}")

payload = {"seed_points": seeds, "crs": "EPSG:4326",
           "timestamp": seeds[0]["time"], "source_scene": chosen.name,
           "notes": "PLACEHOLDER geography: demo anchor inside the NorKyst sample "
                    "domain. Path B georeferencing (assumed anchor + pixel size)."}
(FIXTURES / "spill_seeds.json").write_text(json.dumps(payload, indent=2))
print("wrote fixtures/spill_seeds.json")
'''))

cells.append(md("""
## 10. STEP 4 — backward drift from the real detected seeds

Not a synthetic point release: these positions came from the model's own
prediction, screened, then georeferenced.
"""))
cells.append(code('''
from datetime import timedelta
from opendrift.models.oceandrift import OceanDrift

o = OceanDrift(loglevel=30)
o.add_reader(reader)
o.seed_elements(lon=np.array(lons), lat=np.array(lats), time=OBSERVED_TIME)
print(f"seeded {len(lons)} particles from the detected slick")
o.run(duration=timedelta(hours=DRIFT_HOURS), time_step=-3600, time_step_output=3600)

def get_track(sim):
    res = getattr(sim, "result", None)
    if res is not None:
        try: return np.asarray(res["lon"]), np.asarray(res["lat"])
        except Exception: pass
    h = sim.history
    return np.ma.filled(h["lon"], np.nan), np.ma.filled(h["lat"], np.nan)

dlon, dlat = get_track(o)
print(f"ran backward: {o.time < o.start_time}  ({o.start_time} -> {o.time})")
assert o.time < o.start_time, "did not run backward"
'''))

cells.append(md("""
## 11. STEP 5 — origin bbox + time window (Pillar 2 -> 3 contract)
"""))
cells.append(code('''
final_lon, final_lat = dlon[:, -1], dlat[:, -1]
ok = np.isfinite(final_lon) & np.isfinite(final_lat)
final_lon, final_lat = final_lon[ok], final_lat[ok]
print(f"particles surviving to origin: {int(ok.sum())}/{len(ok)}")

PAD = 0.02   # ~2 km - crude stand-in for a real ensemble spread
bbox = [float(final_lon.min()-PAD), float(final_lat.min()-PAD),
        float(final_lon.max()+PAD), float(final_lat.max()+PAD)]
origin_time = o.time.replace(tzinfo=timezone.utc)
observed_time = o.start_time.replace(tzinfo=timezone.utc)

out = {"origin_bbox": [round(v, 5) for v in bbox],
       "time_window": {"start": origin_time.isoformat(), "end": observed_time.isoformat()},
       "particles": int(ok.sum()), "drift_hours": DRIFT_HOURS,
       "notes": "PLACEHOLDER geography (NorKyst sample forcing). Single "
                "deterministic run - NOT an uncertainty estimate. bbox padded "
                f"{PAD} deg as a crude stand-in for ensemble spread."}
(FIXTURES / "drift_origin.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
print("wrote fixtures/drift_origin.json")
'''))

cells.append(md("## 12. Visual check + save fixtures to Drive"))
cells.append(code('''
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 3, figsize=(16, 5))
ax[0].imshow(np.array(Image.open(chosen).convert("L")), cmap="gray")
ax[0].set_title(f"SAR scene\\n{chosen.name}")
ax[1].imshow(kept, cmap="gray", interpolation="nearest")
ax[1].set_title(f"detected + screened\\n{int(kept.sum())} px")
step = max(1, dlon.shape[0] // 80)
for i in range(0, dlon.shape[0], step):
    ax[2].plot(dlon[i], dlat[i], lw=0.6, alpha=0.45, color="tab:blue")
ax[2].scatter(dlon[:, 0], dlat[:, 0], s=6, color="tab:red", label="observed slick")
ax[2].scatter(final_lon, final_lat, s=6, color="tab:green", label="backtracked origin")
ax[2].set_title(f"backward drift {DRIFT_HOURS}h\\n(PLACEHOLDER geography)")
ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)
for a in ax[:2]: a.axis("off")
plt.tight_layout(); plt.savefig("/content/pipeline_end_to_end.png", dpi=120); plt.show()

dest = Path("/content/drive/MyDrive/oil_spill_runs/fixtures"); dest.mkdir(parents=True, exist_ok=True)
for f in FIXTURES.iterdir():
    shutil.copy(f, dest / f.name)
shutil.copy("/content/pipeline_end_to_end.png", dest / "pipeline_end_to_end.png")
print("fixtures copied to Drive:", dest)
for f in sorted(dest.iterdir()):
    print("   ", f.name, f"({f.stat().st_size} bytes)")
'''))

cells.append(md("""
## What this established, and what it did not

**Established:** the chain runs end to end. A real model prediction becomes
screened blobs, becomes lat/lon seeds, becomes a backward drift, becomes an
origin bbox and time window in the agreed contract format. Agent B can now score
against genuine model output.

**Not established:**
1. **Real geography.** Placeholder anchor inside the NorKyst domain. Needs CMEMS
   currents for Indian waters — a config change, but blocked on registration.
2. **Uncertainty.** One deterministic run with a fixed 0.02 deg pad. A defensible
   origin needs an ensemble over perturbed seed time, position and wind drift
   factor, reported as a probability field.
3. **Wind.** Currents only. Surface oil is strongly wind-driven; without it the
   origin estimate is biased.
4. **Validation.** No ground-truth spill origin to check against. This shows the
   pipeline is coherent, not that it is accurate.
"""))

nb = {"cells": cells,
      "metadata": {"accelerator": "GPU",
                   "colab": {"provenance": [], "gpuType": "T4", "toc_visible": True},
                   "kernelspec": {"display_name": "Python 3", "name": "python3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}

out = sys.argv[1] if len(sys.argv) > 1 else "pipeline_end_to_end.ipynb"
Path(out).write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"wrote {out}: {len(cells)} cells "
      f"({sum(c['cell_type']=='code' for c in cells)} code, "
      f"{sum(c['cell_type']=='markdown' for c in cells)} md)")
