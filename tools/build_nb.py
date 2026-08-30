import json, ast, sys
from pathlib import Path

# The look-alike rules live in lookalike_screen.py so the scoring engine and
# dashboard can import them. Embed that source here so the Colab notebook stays
# self-contained -- one source of truth, no second file to upload, no drift.
_mod = Path("lookalike_screen.py")
assert _mod.is_file(), (
    f"lookalike_screen.py not found in {Path.cwd()} - run this from the project dir"
)
_src = _mod.read_text(encoding="utf-8")
assert "def demo():" in _src, "expected a demo() block to strip"
LOOKALIKE_SRC = _src.split("def demo():")[0].rstrip() + "\n\nprint('loaded:', LABEL)\n"

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}


def code(s):
    src = s.strip("\n")
    ast.parse("".join(l for l in src.splitlines(keepends=True) if not l.lstrip().startswith(("!", "%"))))
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}


cells = []

cells.append(md("""
# Oil Spill Segmentation - U-Net (ResNet34) Fine-Tuning

Multi-class semantic segmentation with `segmentation_models_pytorch`.

Run the cells **in order, top to bottom** (`Runtime` > `Run all`). Each stage
checks its own prerequisites and stops with a plain-English message if
something is wrong, rather than failing quietly later.

## What this notebook does

1. Confirms a GPU is actually assigned (stops hard if not)
2. Installs dependencies
3. Mounts your Google Drive
4. **Copies the dataset from Drive to Colab's local disk** - training reads
   from local disk, never from Drive
5. Scans your masks to catch label problems before training
6. Trains U-Net/ResNet34, stopping at 15 epochs or 3 hours, whichever is first
7. Saves the best checkpoint back to Drive and plots results

## Before you run anything

**1. Select a GPU runtime.** `Runtime` > `Change runtime type` > **T4 GPU** > `Save`.

**2. Get your Kaggle credentials into Colab Secrets** - then there is nothing
to upload at all. Click the **key icon** in the left sidebar, add
`KAGGLE_USERNAME` and `KAGGLE_KEY`, and turn **Notebook access** ON for both.
Full instructions are in section 5.

The dataset downloads straight from Kaggle into Colab in about a minute.
Uploading the same 1.2 GB from a home connection to Drive can take hours - so
avoid that unless your data is not on Kaggle.

**Using your own data instead?** Set `DATA_SOURCE = "drive"` in Config and put
it in Drive in this layout:

```
MyDrive/oil_spill/          (or oil_spill.zip - a zip is much faster)
- images/
  - train/   img_0001.png ...
  - val/     img_0101.png ...
- masks/
  - train/   img_0001.png   <- same filename as its image
  - val/     img_0101.png
```

Image and mask filenames **must match**.

---

## Classes: binary

This notebook is configured for **2 classes: background + oil spill**, which is
what the **Deep-SAR Oil Spill Segmentation** dataset supports.

Measured on 400 random training masks from the full downloaded dataset:

- **276 of 400 (69%)** are clean `{0, 255}`.
- **124 of 400 (31%)** contain intermediate greys - soft boundaries, not one
  stray file. Within those masks the intermediate pixels average ~5% of the
  image (median 2.8%, worst case 21%).
- Masks are therefore **thresholded at >127**, never value-mapped. The threshold
  shifts the positive-pixel fraction by ~2.5% on average and up to 10.8% in the
  worst case, so it is a real modelling choice, not a formality.
- **Oil covers a median 17.7% of pixels** (mean 24.6%). 15 of 400 masks are
  entirely background.

The 5-class variant (**sea / oil spill / look-alike / ship / land**) comes from
the **Krestenitis/MKLab** dataset, distributed from `mklab.iti.gr` by request -
it is not on Kaggle and is not available today. A preset for it sits commented
out in the Config cell for when it is.

Because there is no trained look-alike class, section 11 adds **heuristic
look-alike screening** - hand-written shape rules, not a classifier. See that
section for what it can and cannot tell you.

The `Step 0` scan cell inspects your actual masks and stops with a clear message
if they disagree with `NUM_CLASSES`.
"""))

cells.append(md("## 1. Verify the GPU runtime"))
cells.append(code("""
!nvidia-smi

import torch
print("torch:", torch.__version__, "| CUDA available:", torch.cuda.is_available())
assert torch.cuda.is_available(), (
    "No GPU. Run the next cell for exactly what to do about it."
)
"""))

cells.append(md("""
### 1b. Confirm the GPU is real and usable

Colab can hand you a CPU-only runtime without saying so. On CPU this training
takes **days instead of ~1-2 hours**, with no error and no visible sign that
anything is wrong - it just appears to be running.

This cell refuses to let that happen. It confirms a GPU is assigned, reports
which one, and runs a real computation on it. If anything is off it **raises an
error and stops `Run all`**, so nothing below it can start on CPU.
"""))
cells.append(code('''
import torch, time

BANNER = "=" * 72

if not torch.cuda.is_available():
    print(BANNER)
    print("STOP - NO GPU ASSIGNED. DO NOT CONTINUE.")
    print(BANNER)
    print()
    print("Training on CPU would take days instead of 1-2 hours, with no error")
    print("message and no sign anything is wrong. Fix this before going further.")
    print()
    print("Do this:")
    print("  1. Menu: Runtime > Change runtime type")
    print("  2. Under 'Hardware accelerator', choose 'T4 GPU'")
    print("  3. Click Save (the session restarts)")
    print("  4. Menu: Runtime > Run all")
    print()
    print("If you already chose T4 GPU and still see this message, the free tier")
    print("has no GPU free for you right now. This is a quota/capacity limit, not")
    print("a mistake on your part. Do this instead:")
    print("  1. Menu: Runtime > Disconnect and delete runtime  (frees your quota)")
    print("  2. Close the tab and wait a few hours (often better next morning)")
    print("  3. Reopen the notebook and start again from the top")
    print()
    print("Do not 'just run it anyway' to see what happens.")
    print(BANNER)
    raise RuntimeError("No GPU assigned - see the instructions printed above.")

name = torch.cuda.get_device_name(0)
total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3

# A real allocation + matmul: proves the GPU computes, not just that it is listed.
t0 = time.time()
x = torch.randn(4000, 4000, device="cuda")
torch.cuda.synchronize()
_ = (x @ x).sum().item()
torch.cuda.synchronize()
gpu_ms = (time.time() - t0) * 1000
del x
torch.cuda.empty_cache()

print(BANNER)
print(f"GPU CONFIRMED: {name}  ({total_gb:.1f} GB)")
print(f"compute test passed in {gpu_ms:.0f} ms")
print(BANNER)

if total_gb < 10:
    print()
    print(f"NOTE: {total_gb:.1f} GB is smaller than the usual T4 (~15 GB).")
    print("If you hit an out-of-memory error later, set BATCH_SIZE = 4 in Config.")

print()
print("Safe to continue.")
'''))

cells.append(md("## 2. Install dependencies\n\n`albumentations` is pinned below 2.0 - the 2.x release renamed several transform arguments used here."))
cells.append(code("""
!pip install -q "segmentation-models-pytorch>=0.3.4" "albumentations>=1.4,<2.0"
"""))

cells.append(md("""
## 3. Mount Google Drive

A popup will ask you to choose a Google account and grant access. Pick the
account whose Drive holds your dataset, and click **Allow** on every screen.
"""))
cells.append(code("""
from google.colab import drive
drive.mount('/content/drive')
"""))

cells.append(md("## 4. Config\n\nEverything you are likely to change lives in this cell."))
cells.append(code('''
from pathlib import Path

# --- where the data comes from ----------------------------------------------
#   "kaggle" - download straight into Colab. No upload at all. Fastest by far.
#   "drive"  - use a .zip or folder you uploaded to Drive yourself.
DATA_SOURCE = "kaggle"

KAGGLE_DATASET = "bakhtiyar2222/deep-sar-oil-spill-segmentation-refined"

# Only used when DATA_SOURCE == "drive":
DRIVE_SRC  = Path("/content/drive/MyDrive/oil_spill.zip")
# DRIVE_SRC = Path("/content/drive/MyDrive/oil_spill_small.zip")  # 400/100 subset
# DRIVE_SRC = Path("/content/drive/MyDrive/oil_spill")            # folder

# --- local disk: raw download, then the normalised copy training reads ------
RAW_DIR    = Path("/content/raw")
LOCAL_ROOT = Path("/content/oil_spill")   # Colab's fast local disk

assert DATA_SOURCE in ("kaggle", "drive"), 'DATA_SOURCE must be "kaggle" or "drive"'

# --- where checkpoints are written (Drive: survives a disconnect) -----------
CKPT_DIR  = Path("/content/drive/MyDrive/oil_spill_runs")
CKPT_PATH = CKPT_DIR / "unet_resnet34_best.pth"

# --- classes: BINARY (this is what the Deep-SAR dataset supports) -----------
NUM_CLASSES = 2
CLASS_NAMES = ["background", "oil spill"]

# How masks encode the class of a pixel:
#   "binary" - only {0,255}; thresholded to {0,1}  (Deep-SAR)
#   "index"  - greyscale value IS the class id (0,1,2,...)
#   "rgb"    - each class is a distinct RGB colour -> fill CLASS_RGB below
MASK_MODE = "binary"

# Only used when MASK_MODE == "rgb". The Step 0 scan prints the colours actually
# present in your masks - copy them in here, in class-id order.
CLASS_RGB = {
    # 0: (0, 0, 0),
    # 1: (0, 255, 255),
}

# --- 5-class preset (Krestenitis/MKLab, restricted access) ------------------
# Only if you obtain that dataset. Uncomment these three lines:
# NUM_CLASSES = 5
# CLASS_NAMES = ["sea", "oil spill", "look-alike", "ship", "land"]
# MASK_MODE   = "index"

# --- training --------------------------------------------------------------
ENCODER         = "resnet34"
ENCODER_WEIGHTS = "imagenet"
IMAGE_SIZE      = 256          # must be divisible by 32 for U-Net
BATCH_SIZE      = 8
LR              = 3e-4
NUM_WORKERS     = 2            # free Colab gives 2 vCPUs
SEED            = 42

# --- stopping: whichever limit is reached first -----------------------------
EPOCHS            = 15         # hard cap on epochs
TIME_BUDGET_HOURS = 3.0        # hard cap on wall-clock, measured from epoch 1

# --- dataset size -----------------------------------------------------------
MAX_TRAIN_IMAGES = None        # cap the training set up front; None = use all
AUTO_SHRINK      = True        # subsample once if 15 epochs will not fit
MIN_TRAIN_IMAGES = 200         # never shrink below this

assert len(CLASS_NAMES) == NUM_CLASSES, "CLASS_NAMES must have NUM_CLASSES entries"
assert IMAGE_SIZE % 32 == 0, "IMAGE_SIZE must be divisible by 32"
assert MIN_TRAIN_IMAGES >= 2 * BATCH_SIZE, "MIN_TRAIN_IMAGES must leave at least 2 full batches"

import random, numpy as np, torch
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
print("config ok |", NUM_CLASSES, "classes |", MASK_MODE, "masks")
print("source :", KAGGLE_DATASET if DATA_SOURCE == "kaggle" else DRIVE_SRC)
print("staged :", LOCAL_ROOT)
print("ckpts  :", CKPT_PATH)
'''))

cells.append(md("""
## 5. Get the dataset onto local disk

Training reads every image once per epoch. Reading those over the Google Drive
mount is **the single biggest thing that makes a run slow** - every file is a
network round trip. So the data lands on Colab's local disk first, and training
never touches Drive.

### `DATA_SOURCE = "kaggle"` (default, recommended)

Downloads straight from Kaggle into Colab. **Nothing to upload.** Colab's
connection to Kaggle is fast - roughly 1-2 minutes for 1.2 GB - whereas
uploading the same data from a home connection to Drive can take hours.

**One-time setup: put your Kaggle credentials in Colab Secrets.**

1. Click the **key icon** in the left sidebar of Colab ("Secrets")
2. Click **+ Add new secret**. Name: `KAGGLE_USERNAME`, Value: your Kaggle
   username. Turn **Notebook access** ON.
3. Click **+ Add new secret** again. Name: `KAGGLE_KEY`, Value: your Kaggle API
   token. Turn **Notebook access** ON.

Get a token at kaggle.com > your avatar > Settings > API > **Create New Token**
(that downloads `kaggle.json`; the value you want is the `key` field inside).

Secrets live in your Colab account, not in this notebook - the token is never
written into the file, so the notebook stays safe to share.

### `DATA_SOURCE = "drive"`

Use this if the data is not on Kaggle, or you already uploaded it. Point
`DRIVE_SRC` at a `.zip` (much faster) or a folder in your Drive.

### Either way, this cell

- checks free local disk before downloading or copying anything
- checks Drive has room for checkpoints (~100 MB per save)
- **normalises the folder layout** - Kaggle ships this dataset as
  `images/images/train`, which is flattened to `images/train`
- verifies the result: counts images, counts masks, confirms filenames match

The local disk is **wiped when the runtime ends**. That is expected - your
checkpoints go to Drive. After a disconnect, just re-run this cell.
"""))
cells.append(code('''
import shutil, subprocess, sys, time, os

GB = 1024 ** 3
EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

def human(n):
    return f"{n / GB:.2f} GB"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

# --- 1. Drive space for checkpoints (both sources need this) ----------------
CKPT_DIR.mkdir(parents=True, exist_ok=True)
try:
    drive_free = shutil.disk_usage("/content/drive/MyDrive").free
    print(f"Drive free: {human(drive_free)}")
    if drive_free < 0.5 * GB:
        print("WARNING: under 0.5 GB free in Drive. Each checkpoint is ~100 MB.")
        print("If Drive fills up, saving fails and the best model is lost at")
        print("session end. Free up space before training.")
except Exception as e:
    print(f"(could not read Drive free space: {e} - continuing)")

free_local = shutil.disk_usage("/content").free
print(f"local disk free: {human(free_local)}")

t0 = time.time()

# --- 2a. KAGGLE: download straight into Colab -------------------------------
if DATA_SOURCE == "kaggle":
    if free_local < 6 * GB:
        raise RuntimeError(
            f"Only {human(free_local)} free on /content; want ~6 GB for the "
            "download plus the unpacked copy. Runtime > Disconnect and delete "
            "runtime, then start again."
        )
    try:
        from google.colab import userdata
        os.environ["KAGGLE_USERNAME"] = userdata.get("KAGGLE_USERNAME")
        os.environ["KAGGLE_KEY"] = userdata.get("KAGGLE_KEY")
    except Exception as e:
        print("Could not read your Kaggle credentials from Colab Secrets.")
        print()
        print("Set them up (one time):")
        print("  1. Click the KEY icon in the left sidebar ('Secrets')")
        print("  2. + Add new secret -> name KAGGLE_USERNAME, value your username")
        print("  3. + Add new secret -> name KAGGLE_KEY, value your API token")
        print("  4. Turn 'Notebook access' ON for BOTH")
        print()
        print("Get a token: kaggle.com > avatar > Settings > API > Create New Token")
        print("(it downloads kaggle.json; the value you want is its 'key' field)")
        print()
        print("Or set DATA_SOURCE = 'drive' in Config to use an upload instead.")
        raise RuntimeError(f"Kaggle credentials unavailable: {e}")

    print(f"downloading {KAGGLE_DATASET} from Kaggle...")
    # Use the Python API, not "python -m kaggle": Colab's kaggle package has no
    # __main__, so -m fails with "'kaggle' is a package and cannot be directly
    # executed" regardless of whether the credentials are fine.
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        _api = KaggleApi()
        _api.authenticate()
        _api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DIR),
                                    unzip=True, quiet=False)
    except Exception as _e:
        print()
        print(f"Kaggle download failed: {type(_e).__name__}: {_e}")
        print("  - 401/403: token wrong or expired, or the secret's Notebook")
        print("             access toggle is OFF")
        print("  - 404: open the dataset page on kaggle.com once and accept its")
        print("         rules, then re-run this cell")
        print("  - or set DATA_SOURCE = 'drive' in Config to use an upload")
        raise
    src_root = RAW_DIR

# --- 2b. DRIVE: copy or unzip what you uploaded -----------------------------
else:
    if not DRIVE_SRC.exists():
        print("Could not find your dataset in Drive at:")
        print(f"  {DRIVE_SRC}")
        print()
        print("Check that:")
        print("  - the mount cell above printed 'Mounted at /content/drive'")
        print("  - you are signed into the Google account that owns the file")
        print("  - the path is spelled exactly right, including capital letters")
        print()
        print("Files currently in the top level of your Drive:")
        mydrive = Path("/content/drive/MyDrive")
        if mydrive.is_dir():
            for p in sorted(mydrive.iterdir())[:30]:
                print("   ", p.name + ("/" if p.is_dir() else ""))
        raise FileNotFoundError(f"DRIVE_SRC not found: {DRIVE_SRC}")

    is_zip = DRIVE_SRC.is_file() and DRIVE_SRC.suffix.lower() == ".zip"
    if is_zip:
        src_bytes = DRIVE_SRC.stat().st_size
        needed = src_bytes * 2.2
        print(f"source: zip, {human(src_bytes)}")
    else:
        print("source: folder - measuring size (walks Drive; slow for many files)...")
        out = subprocess.run(["du", "-sb", str(DRIVE_SRC)], capture_output=True, text=True)
        src_bytes = int(out.stdout.split()[0]) if out.returncode == 0 else 0
        needed = src_bytes * 1.15
        print(f"source: folder, {human(src_bytes)}")

    if free_local < needed:
        raise RuntimeError(f"Need ~{human(needed)} on /content, have {human(free_local)}")

    if is_zip:
        print("unzipping to local disk...")
        subprocess.run(["unzip", "-q", "-o", str(DRIVE_SRC), "-d", str(RAW_DIR)], check=True)
    else:
        print("copying folder to local disk...")
        subprocess.run(["cp", "-r", str(DRIVE_SRC) + "/.", str(RAW_DIR)], check=True)
    src_root = RAW_DIR

print(f"fetched in {time.time() - t0:.0f}s")

# --- 3. normalise the layout ------------------------------------------------
# Kaggle ships this dataset as images/images/train and masks/masks/train; a zip
# may or may not have a top-level folder. Find the real split dirs wherever they
# are, then put them at LOCAL_ROOT/{images,masks}/{train,val}.
def locate(base, kind, split):
    for c in (base / kind / split, base / kind / kind / split,
              base / "oil_spill" / kind / split):
        if c.is_dir():
            return c
    hits = [p for p in base.rglob(split)
            if p.is_dir() and p.parent.name == kind
            and any(f.suffix.lower() in EXT for f in p.iterdir())]
    return hits[0] if hits else None

for kind in ("images", "masks"):
    for split in ("train", "val"):
        found = locate(src_root, kind, split)
        dest = LOCAL_ROOT / kind / split
        if found is None:
            print(f"Could not find a '{kind}/{split}' directory under {src_root}.")
            print("Directories present:")
            for p in sorted(d for d in src_root.rglob("*") if d.is_dir())[:40]:
                print("   ", p.relative_to(src_root))
            raise FileNotFoundError(f"missing {kind}/{split}")
        if dest.resolve() == found.resolve():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(found), str(dest))
        print(f"  {kind}/{split}: {found.relative_to(src_root)} -> {dest.relative_to(LOCAL_ROOT)}")

DATA_ROOT     = LOCAL_ROOT
TRAIN_IMG_DIR = DATA_ROOT / "images" / "train"
TRAIN_MSK_DIR = DATA_ROOT / "masks"  / "train"
VAL_IMG_DIR   = DATA_ROOT / "images" / "val"
VAL_MSK_DIR   = DATA_ROOT / "masks"  / "val"

# --- 4. verify --------------------------------------------------------------
stems = lambda d: {p.stem for p in d.iterdir() if p.suffix.lower() in EXT}

print()
print(f"data root: {DATA_ROOT}")
problems = []
for split, imgd, mskd in [("train", TRAIN_IMG_DIR, TRAIN_MSK_DIR),
                          ("val",   VAL_IMG_DIR,   VAL_MSK_DIR)]:
    if not imgd.is_dir() or not mskd.is_dir():
        problems.append(f"{split}: missing images/ or masks/ directory")
        continue
    si, sm = stems(imgd), stems(mskd)
    paired = si & sm
    print(f"  {split}: {len(si)} images, {len(sm)} masks, {len(paired)} matched pairs")
    if si - sm:
        print(f"    {len(si - sm)} images with no mask (ignored), e.g. {sorted(si - sm)[:3]}")
    if sm - si:
        print(f"    {len(sm - si)} masks with no image (ignored), e.g. {sorted(sm - si)[:3]}")
    if not paired:
        problems.append(f"{split}: zero matched pairs - image and mask filenames must match")

if problems:
    print()
    for p in problems:
        print("PROBLEM:", p)
    raise RuntimeError("Staged data is not usable - see problems above.")

print()
print(f"dataset staged at {LOCAL_ROOT} (local disk). Training will not read from Drive.")
'''))

cells.append(md("""
## Step 0 - Scan the masks before training

This reads your actual mask files and reports what is in them. It **stops the
notebook** if labels fall outside `[0, NUM_CLASSES)`.

Worth the 30 seconds: out-of-range labels reaching `CrossEntropyLoss` surface
as an opaque `CUDA device-side assert triggered` several minutes into training,
with no indication of the real cause.
"""))
cells.append(code('''
import numpy as np
from PIL import Image
from collections import Counter

def decode_mask(path):
    """Return an int64 HxW array of class ids, per MASK_MODE."""
    if MASK_MODE == "rgb":
        arr = np.array(Image.open(path).convert("RGB"))
        out = np.zeros(arr.shape[:2], dtype=np.int64)
        for cid, rgb in CLASS_RGB.items():
            out[np.all(arr == np.array(rgb, dtype=arr.dtype), axis=-1)] = cid
        return out
    arr = np.array(Image.open(path).convert("L"))
    if MASK_MODE == "binary":
        # thresholded, not remapped: some masks carry anti-aliased edge values
        return (arr > 127).astype(np.int64)
    return arr.astype(np.int64)

def scan_masks(mask_dir, limit=200):
    paths = sorted(p for p in Path(mask_dir).iterdir()
                   if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"})
    assert paths, f"No mask files found in {mask_dir}"
    seen, px = set(), Counter()
    for p in paths[:limit]:
        m = decode_mask(p)
        v, c = np.unique(m, return_counts=True)
        seen |= set(v.tolist())
        px.update(dict(zip(v.tolist(), c.tolist())))
    return paths, sorted(seen), px

paths, values, px = scan_masks(TRAIN_MSK_DIR)
total = sum(px.values())
print(f"{len(paths)} masks in {TRAIN_MSK_DIR} (scanned up to 200)")
print("class ids present:", values)
for v in values:
    name = CLASS_NAMES[v] if v < NUM_CLASSES else "OUT OF RANGE"
    print(f"  {v}: {100 * px[v] / total:6.2f}%  {name}")

if MASK_MODE == "rgb" and not CLASS_RGB:
    raw = np.array(Image.open(paths[0]).convert("RGB")).reshape(-1, 3)
    uniq = np.unique(raw, axis=0)
    print()
    print("MASK_MODE='rgb' but CLASS_RGB is empty. Colours in the first mask:")
    for c in uniq[:20]:
        print("   ", tuple(int(x) for x in c))
    raise SystemExit("Fill CLASS_RGB in the Config cell with the colours above.")

bad = [v for v in values if v < 0 or v >= NUM_CLASSES]
assert not bad, (
    f"Labels {bad} are outside [0, {NUM_CLASSES}). Either NUM_CLASSES is wrong "
    f"or MASK_MODE is wrong. Masks holding only 0 and 255 are the binary "
    f"Deep-SAR set: use the binary preset in the Config cell."
)
missing = [CLASS_NAMES[i] for i in range(NUM_CLASSES) if i not in values]
if missing:
    print()
    print(f"WARNING: no pixels for {missing} in the scanned masks.")
    print("These output channels will train on nothing and their IoU will read 0.")
print()
print("mask scan passed")
'''))

cells.append(md("""
## 6. Dataset + augmentation

The dataset is small, so augmentation is deliberately aggressive on geometry -
flips and rotations are label-preserving for overhead SAR imagery, which has no
canonical orientation. Noise is kept mild; SAR speckle is already part of the
signal and heavy noise erases the thin, low-contrast spill boundaries.

Augmentation is applied to **train only**. Geometric transforms are applied to
image and mask together; Albumentations uses nearest-neighbour on masks, so no
interpolated fractional class ids are introduced.
"""))
cells.append(code('''
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset, DataLoader, Subset
import segmentation_models_pytorch as smp

params = smp.encoders.get_preprocessing_params(ENCODER, ENCODER_WEIGHTS)
MEAN, STD = params["mean"], params["std"]

train_tf = A.Compose([
    A.PadIfNeeded(IMAGE_SIZE, IMAGE_SIZE, border_mode=0),
    A.RandomCrop(IMAGE_SIZE, IMAGE_SIZE),
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.5),
    A.RandomRotate90(p=0.5),
    A.ShiftScaleRotate(shift_limit=0.06, scale_limit=0.1, rotate_limit=30,
                       border_mode=0, p=0.5),
    A.GaussNoise(var_limit=(5.0, 25.0), p=0.3),
    A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.3),
    A.Normalize(mean=MEAN, std=STD),
    ToTensorV2(),
])

val_tf = A.Compose([
    A.PadIfNeeded(IMAGE_SIZE, IMAGE_SIZE, border_mode=0),
    A.CenterCrop(IMAGE_SIZE, IMAGE_SIZE),
    A.Normalize(mean=MEAN, std=STD),
    ToTensorV2(),
])

IMG_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

class OilSpillDataset(Dataset):
    def __init__(self, img_dir, mask_dir, transform):
        self.img_dir, self.mask_dir, self.transform = Path(img_dir), Path(mask_dir), transform
        masks = {p.stem: p for p in self.mask_dir.iterdir() if p.suffix.lower() in IMG_EXT}
        self.pairs = sorted(
            (p, masks[p.stem]) for p in self.img_dir.iterdir()
            if p.suffix.lower() in IMG_EXT and p.stem in masks
        )
        assert self.pairs, f"No image/mask pairs matched between {img_dir} and {mask_dir}."

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, i):
        img_p, msk_p = self.pairs[i]
        # SAR is greyscale; the ImageNet encoder expects 3 channels
        img = np.array(Image.open(img_p).convert("RGB"))
        msk = decode_mask(msk_p)
        out = self.transform(image=img, mask=msk)
        return out["image"], out["mask"].long()

def subsample(ds, n, seed=SEED):
    """Deterministic random subset of n items. Random, not the first n: files are
    sorted by name, and taking a prefix would bias toward one scene or capture."""
    g = torch.Generator().manual_seed(seed)
    idx = torch.randperm(len(ds), generator=g)[:n].tolist()
    return Subset(ds, idx)

train_ds = OilSpillDataset(TRAIN_IMG_DIR, TRAIN_MSK_DIR, train_tf)
val_ds   = OilSpillDataset(VAL_IMG_DIR,   VAL_MSK_DIR,   val_tf)
full_train_n = len(train_ds)

if MAX_TRAIN_IMAGES is not None and MAX_TRAIN_IMAGES < len(train_ds):
    train_ds = subsample(train_ds, MAX_TRAIN_IMAGES)
    print(f"MAX_TRAIN_IMAGES: using {len(train_ds)} of {full_train_n} training pairs")

def make_train_dl(ds):
    return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=True,
                      num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)

train_dl = make_train_dl(train_ds)
val_dl   = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                      num_workers=NUM_WORKERS, pin_memory=True)

print(f"train: {len(train_ds)} pairs | val: {len(val_ds)} pairs")
'''))

cells.append(md("### Sanity check: look at an augmented batch\n\nConfirm masks still line up with their images after the geometric transforms."))
cells.append(code('''
import matplotlib.pyplot as plt

imgs, msks = next(iter(train_dl))
print("image batch:", tuple(imgs.shape), "| mask batch:", tuple(msks.shape))
print("mask values in batch:", torch.unique(msks).tolist())

n = min(4, imgs.shape[0])
fig, ax = plt.subplots(2, n, figsize=(3.2 * n, 6.4))
for i in range(n):
    vis = imgs[i].permute(1, 2, 0).numpy() * np.array(STD) + np.array(MEAN)
    ax[0, i].imshow(np.clip(vis, 0, 1))
    ax[0, i].set_title("image"); ax[0, i].axis("off")
    ax[1, i].imshow(msks[i], vmin=0, vmax=NUM_CLASSES - 1, cmap="tab10", interpolation="nearest")
    ax[1, i].set_title(f"mask {torch.unique(msks[i]).tolist()}"); ax[1, i].axis("off")
plt.tight_layout(); plt.show()
'''))

cells.append(md("""
## 7. Model, loss, optimizer

`activation=None` means the model emits raw logits, which is what both
`CrossEntropyLoss` and `DiceLoss(mode="multiclass")` expect - do not add a
softmax here.

Loss is Dice + cross-entropy.

Measured over 400 training masks, oil covers a **median 17.7% of pixels**
(mean 24.6%). That is a moderate imbalance, not a severe one - so the usual
argument for Dice (that cross-entropy lets an all-background prediction win)
does **not** really apply here. Plain cross-entropy would train acceptably.

Dice is kept for a narrower reason: it optimises region overlap directly, which
is the quantity being reported as mIoU, and it behaves better on the minority of
frames where oil is a thin sliver. If you want a simpler baseline to compare
against, `criterion = ce_loss` is a legitimate thing to try - this is a tuning
choice, not a correctness requirement.
"""))
cells.append(code('''
import torch.nn as nn

assert torch.cuda.is_available(), "GPU vanished since cell 1b - rerun from the top."
DEVICE = "cuda"

model = smp.Unet(
    encoder_name=ENCODER,
    encoder_weights=ENCODER_WEIGHTS,
    in_channels=3,
    classes=NUM_CLASSES,
    activation=None,
).to(DEVICE)

dice_loss = smp.losses.DiceLoss(mode="multiclass", from_logits=True)
ce_loss   = nn.CrossEntropyLoss()

def criterion(logits, target):
    return 0.5 * dice_loss(logits, target) + 0.5 * ce_loss(logits, target)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
scaler    = torch.amp.GradScaler("cuda")

n_params = sum(p.numel() for p in model.parameters()) / 1e6
print(f"U-Net / {ENCODER} / {ENCODER_WEIGHTS} | {NUM_CLASSES} classes | {n_params:.1f}M params")
print("model on:", next(model.parameters()).device)
'''))

cells.append(md("""
## 8. Train

Best checkpoint is selected on **validation mean IoU**, not loss, and written to
Drive so it survives a runtime disconnect.

### Stopping

Training stops at **15 epochs or 3 hours, whichever comes first** (`EPOCHS` and
`TIME_BUDGET_HOURS` in Config). The clock starts at epoch 1, so it excludes
install, mount, and staging time.

The time check runs *between* epochs, not inside one: after each epoch it stops
if another epoch of the same length would overrun the budget. So the run ends
under 3 hours rather than being killed partway through an epoch with that
epoch's work thrown away. A single epoch longer than the whole budget still
completes once - there is no way to know it will overrun before running it.

### If it is running slow

After epoch 1, if 15 epochs project past the budget, the training set is
subsampled once so the full 15 fit. The **validation set is never touched**, so
mIoU stays comparable across runs.

With the data staged on local disk this should rarely trigger. If it does,
lower `IMAGE_SIZE` or `BATCH_SIZE` before accepting fewer images - fewer images
means less variety and a lower ceiling, not just a shorter run. Set
`AUTO_SHRINK = False` to keep every image and simply stop at whichever limit
arrives first.
"""))
cells.append(code('''
from tqdm.auto import tqdm
import time

def evaluate(model, loader):
    """Mean loss and per-class IoU. IoU uses dataset-wide accumulated counts,
    not an average of per-batch IoUs."""
    model.eval()
    tp = fp = fn = tn = None
    losses = []
    with torch.no_grad():
        for imgs, msks in loader:
            imgs, msks = imgs.to(DEVICE, non_blocking=True), msks.to(DEVICE, non_blocking=True)
            with torch.amp.autocast("cuda"):
                logits = model(imgs)
                losses.append(criterion(logits, msks).item())
            pred = logits.argmax(1)
            b = smp.metrics.get_stats(pred, msks, mode="multiclass", num_classes=NUM_CLASSES)
            b = [x.sum(0) for x in b]
            if tp is None:
                tp, fp, fn, tn = b
            else:
                tp, fp, fn, tn = [a + c for a, c in zip((tp, fp, fn, tn), b)]
    iou = smp.metrics.iou_score(tp, fp, fn, tn, reduction=None)
    return float(np.mean(losses)), iou.squeeze()

def hms(s):
    return f"{int(s // 3600)}h{int(s % 3600 // 60):02d}m{int(s % 60):02d}s"

# --- preflight -------------------------------------------------------------
assert torch.cuda.is_available(), "No GPU - do not train on CPU. Rerun from cell 1b."
assert str(next(model.parameters()).device).startswith("cuda"), "model is not on the GPU"
assert not str(TRAIN_IMG_DIR).startswith("/content/drive"), (
    "Training would read from Drive. Re-run the staging cell (section 5)."
)
print(f"GPU        : {torch.cuda.get_device_name(0)}")
print(f"reading    : {TRAIN_IMG_DIR}  (local disk)")
print(f"train/val  : {len(train_ds)} / {len(val_ds)} pairs")
print(f"limits     : {EPOCHS} epochs or {TIME_BUDGET_HOURS}h, whichever comes first")
print(f"checkpoint : {CKPT_PATH}")
print()

best_miou = -1.0
history = []
budget_s = TIME_BUDGET_HOURS * 3600
t_start = time.time()
stop_reason = f"ran all {EPOCHS} epochs"

for epoch in range(1, EPOCHS + 1):
    t_epoch = time.time()
    model.train()
    running = 0.0
    bar = tqdm(train_dl, desc=f"epoch {epoch}/{EPOCHS}", leave=False)
    for imgs, msks in bar:
        imgs, msks = imgs.to(DEVICE, non_blocking=True), msks.to(DEVICE, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda"):
            loss = criterion(model(imgs), msks)
        scaler.scale(loss).backward()
        scaler.step(optimizer); scaler.update()
        running += loss.item()
        bar.set_postfix(loss=f"{loss.item():.4f}")
    scheduler.step()

    train_loss = running / len(train_dl)
    val_loss, iou = evaluate(model, val_dl)
    miou = float(iou.mean())
    history.append((epoch, train_loss, val_loss, miou))

    per_class = "  ".join(f"{n}={v:.3f}" for n, v in zip(CLASS_NAMES, iou.tolist()))
    flag = ""
    if miou > best_miou:
        best_miou = miou
        CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"model": model.state_dict(), "epoch": epoch, "miou": miou,
                    "num_classes": NUM_CLASSES, "class_names": CLASS_NAMES,
                    "encoder": ENCODER}, CKPT_PATH)
        flag = "  <- best, saved"

    epoch_s = time.time() - t_epoch
    elapsed = time.time() - t_start
    print(f"epoch {epoch:3d} | train {train_loss:.4f} | val {val_loss:.4f} | mIoU {miou:.4f}"
          f" | {hms(epoch_s)} | total {hms(elapsed)}{flag}")
    print(f"          IoU: {per_class}")

    # Shrink once, after epoch 1, if the full run will not fit the time budget.
    # ponytail: one-shot on the epoch-1 measurement, not a per-epoch controller.
    # Epoch 1 is the slowest (cold page cache, cuDNN autotune), so the estimate
    # runs pessimistic and errs toward keeping fewer images. Re-tune by hand with
    # MAX_TRAIN_IMAGES if that trade is wrong for you.
    if AUTO_SHRINK and epoch == 1 and len(train_ds) > MIN_TRAIN_IMAGES:
        projected = epoch_s * EPOCHS
        if projected > budget_s:
            keep = max(MIN_TRAIN_IMAGES, int(len(train_ds) * (budget_s * 0.9) / projected))
            if keep < len(train_ds):
                print(f"  AUTO_SHRINK: epoch 1 took {hms(epoch_s)}; {EPOCHS} epochs project to "
                      f"{hms(projected)} > {TIME_BUDGET_HOURS}h budget.")
                print(f"  Reducing training set {len(train_ds)} -> {keep} images "
                      f"(val set unchanged, so mIoU stays comparable).")
                train_ds = subsample(train_ds, keep)
                train_dl = make_train_dl(train_ds)

    # Stop before starting an epoch that will not finish inside the budget.
    if epoch < EPOCHS and elapsed + epoch_s > budget_s:
        stop_reason = (f"hit the {TIME_BUDGET_HOURS}h budget after epoch {epoch} "
                       f"(another epoch would overrun it)")
        break

print()
print(f"done: {stop_reason}, {hms(time.time() - t_start)} elapsed")
print(f"best val mIoU = {best_miou:.4f} -> {CKPT_PATH}")
'''))

cells.append(md("## 9. Training curves"))
cells.append(code('''
ep, tr, vl, mi = zip(*history)
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(ep, tr, label="train"); ax[0].plot(ep, vl, label="val")
ax[0].set_xlabel("epoch"); ax[0].set_ylabel("loss"); ax[0].legend(); ax[0].grid(alpha=.3)
ax[1].plot(ep, mi, color="tab:green"); ax[1].set_xlabel("epoch")
ax[1].set_ylabel("val mIoU"); ax[1].grid(alpha=.3)
plt.tight_layout(); plt.show()
'''))

cells.append(md("## 10. Qualitative check - predictions vs ground truth\n\nReloads the best checkpoint rather than using the final-epoch weights."))
cells.append(code('''
ckpt = torch.load(CKPT_PATH, map_location=DEVICE, weights_only=False)
model.load_state_dict(ckpt["model"])
model.eval()
print(f"loaded epoch {ckpt['epoch']} | mIoU {ckpt['miou']:.4f}")

imgs, msks = next(iter(val_dl))
with torch.no_grad(), torch.amp.autocast("cuda"):
    pred = model(imgs.to(DEVICE)).argmax(1).cpu()

n = min(4, imgs.shape[0])
fig, ax = plt.subplots(3, n, figsize=(3.2 * n, 9.6))
for i in range(n):
    vis = imgs[i].permute(1, 2, 0).numpy() * np.array(STD) + np.array(MEAN)
    ax[0, i].imshow(np.clip(vis, 0, 1)); ax[0, i].set_title("image")
    ax[1, i].imshow(msks[i], vmin=0, vmax=NUM_CLASSES - 1, cmap="tab10", interpolation="nearest")
    ax[1, i].set_title("ground truth")
    ax[2, i].imshow(pred[i], vmin=0, vmax=NUM_CLASSES - 1, cmap="tab10", interpolation="nearest")
    ax[2, i].set_title("prediction")
    for r in range(3):
        ax[r, i].axis("off")
plt.tight_layout(); plt.show()
'''))

cells.append(md("""
## 11. Heuristic look-alike screening

**This is not a trained classifier.** It is a handful of shape rules applied to
the blobs the segmentation model already found, and it is labelled that way
everywhere it prints.

Not every dark patch in SAR is oil. Algal blooms, biogenic films and
wind-sheltered calm water all scatter little radar energy back and appear dark,
exactly like a slick. A binary oil/background model has never been shown a
labelled look-alike, so it cannot distinguish them - and it will report them as
oil with high confidence.

These rules encode one domain observation: wind- and current-driven slicks tend
to be **elongated with ragged edges**, while common look-alikes tend to be
**small, round and smooth**.

Three rules, applied per blob, in order:

| # | Condition | Verdict |
|---|-----------|---------|
| 1 | `area < 50 px` | `noise` - speckle, not a detection |
| 2 | round (`elongation <= 1.8`) **and** smooth (`roughness <= 1.35`) **and** small (`area < 600 px`) | `look-alike` |
| 3 | anything else | `oil` |

`elongation` is the major/minor axis ratio from second moments (1.0 = circle).
`roughness` is perimeter divided by the perimeter of a circle of equal area -
measured on a pixel grid, where a smooth disc reads about **0.86**, not 1.0.
The thresholds were calibrated from measured synthetic shapes for that reason.

### What this cannot do

- It **cannot detect a look-alike that is large or elongated.** An extended
  algal bloom passes straight through as oil.
- It has **never been validated against labelled look-alikes**, because none are
  available. The thresholds are reasoned defaults, not fitted values.
- It will **discard small genuine slicks** that happen to be round and smooth.
  Rule 2 trades recall for precision; that trade is not free.

Treat the output as a screening aid that flags blobs worth a second look, never
as evidence a detection is false.

### Future work

A real look-alike classifier needs labelled look-alike examples: the
**Krestenitis/MKLab 5-class dataset** (sea / oil spill / look-alike / ship /
land), available from `mklab.iti.gr` by request. With it, the correct fix is to
train the 5-class model directly and delete these rules, rather than to tune
them further.
"""))
cells.append(code(LOOKALIKE_SRC))

cells.append(md("""
### Apply screening to the model's predictions

Left to right: the SAR image, the model's raw prediction, and the prediction
after screening. Blobs the rules reject are listed underneath with the reason.
"""))
cells.append(code('''
OIL_CLASS = CLASS_NAMES.index("oil spill") if "oil spill" in CLASS_NAMES else 1

imgs, msks = next(iter(val_dl))
with torch.no_grad(), torch.amp.autocast("cuda"):
    pred = model(imgs.to(DEVICE)).argmax(1).cpu().numpy()

n = min(4, imgs.shape[0])
fig, ax = plt.subplots(3, n, figsize=(3.2 * n, 9.6))
for i in range(n):
    raw = (pred[i] == OIL_CLASS).astype(np.uint8)
    kept, blobs = screen(raw)

    vis = imgs[i].permute(1, 2, 0).numpy() * np.array(STD) + np.array(MEAN)
    ax[0, i].imshow(np.clip(vis, 0, 1)); ax[0, i].set_title("image")
    ax[1, i].imshow(raw, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    ax[1, i].set_title(f"raw pred ({raw.sum()} px)")
    ax[2, i].imshow(kept, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    ax[2, i].set_title(f"after screening ({kept.sum()} px)")
    for r in range(3):
        ax[r, i].axis("off")

    rejected = [b for b in blobs if b["verdict"] != "oil"]
    print(f"--- image {i}: {len(blobs)} blobs, {len(rejected)} screened out")
    for b in rejected:
        print(f"    blob {b['label']} at {b['centroid_yx']}: {b['verdict']} - {b['reason']}")

plt.tight_layout(); plt.show()

print()
print(LABEL.upper())
print("Screening is rule-based post-processing. It is not a trained look-alike")
print("classifier, and it has not been validated against labelled look-alikes.")
'''))

cells.append(md("""
## Troubleshooting

**"No GPU assigned"** - cell 1b prints exactly what to do. Short version:
`Runtime` > `Change runtime type` > `T4 GPU` > `Save`. If you already did that,
the free tier has no GPU spare right now; disconnect, wait a few hours, retry.

**"DRIVE_SRC not found"** - the staging cell prints what is actually in the top
level of your Drive. Compare it against the `DRIVE_SRC` path in Config, and
check you signed the mount popup into the right Google account.

**"zero matched pairs"** - image and mask filenames must be identical
(`img_001.png` in both `images/train` and `masks/train`). The staging cell
prints examples of the mismatches.

**`CUDA device-side assert triggered`** - a label id is `>= NUM_CLASSES`.
Re-run the Step 0 scan cell; it catches this on CPU with a readable message.

**A class sits at IoU 0.000 forever** - usually that class has no pixels in the
training masks. The Step 0 scan warns about this.

**Out of GPU memory** - set `BATCH_SIZE = 4` (or 2) in Config and re-run from
the Config cell down.

**The run stopped before 15 epochs** - it hit the 3h budget; the last line says
which limit ended it. The best checkpoint is still saved.

**Disconnected mid-run** - the best checkpoint so far is already in Drive at
`CKPT_PATH`. Reconnect, `Run all`, and let it re-stage; or skip training and
run only the last cell to look at what you already have.

## Free-tier notes

- **Keep the browser tab open** and the machine awake. Colab disconnects idle
  sessions, and a closed laptop lid counts as idle. A 3-hour budget means about
  3 hours of the tab staying open.
- **Do not run other Colab notebooks at the same time.** They share one GPU
  quota, and a second notebook can cost you this one's GPU.
- **GPU availability is not guaranteed** on the free tier and varies by time of
  day. Early morning is usually easier than evenings.
- **The local disk is wiped** when the runtime ends - only Drive persists. That
  is why checkpoints go to `CKPT_DIR` in Drive.
- `EPOCHS = 15` is a cap, not a target. Still climbing at the end means raise
  the cap; plateauing early while train loss keeps falling means overfitting.
- The **cosine LR schedule is sized to `EPOCHS`**, so a run cut short by the
  time budget ends mid-schedule at a higher LR than intended. Harmless for one
  run, but when comparing runs, compare ones that ended the same way.
"""))

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4", "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = sys.argv[1]
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"wrote {out}: {len(cells)} cells "
      f"({sum(c['cell_type'] == 'code' for c in cells)} code, "
      f"{sum(c['cell_type'] == 'markdown' for c in cells)} md)")
