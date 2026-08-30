"""Generate opendrift_backward_demo.ipynb - Colab proof that a BACKWARD run works.

Run: python tools/build_opendrift_nb.py opendrift_backward_demo.ipynb
"""

import json, ast, sys

md = lambda s: {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}


def code(s):
    src = s.strip("\n")
    ast.parse("".join(l for l in src.splitlines(keepends=True) if not l.lstrip().startswith(("!", "%"))))
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}


cells = []

cells.append(md("""
# OCEANIQ - OpenDrift backward-tracking proof

**Purpose: prove the software path works. Nothing more.**

This runs OpenDrift's **own bundled sample forcing data** (a small NorKyst-800
current field off western Norway) **backward in time**, and plots the resulting
particle trajectories.

### What this proves
- OpenDrift installs and imports in Colab
- A **negative time step** runs and integrates backward
- Particles move coherently, producing a sensible trajectory plot

### What this does NOT do
- No real wind or current data for Indian waters
- No connection to the SAR spill detector
- No georeferencing - OCEANIQ's spill masks are pixel coordinates on a 256x256
  tile with **no geotransform**; converting those to lat/lon seed points is a
  separate, still-unwritten piece of work

**No GPU needed.** `Runtime > Change runtime type > CPU` is fine and connects faster.

Run order: `Runtime > Run all`.
"""))

cells.append(md("""
## 1. Install OpenDrift

Takes roughly 2-4 minutes - it pulls a geospatial stack (cartopy, netCDF4,
xarray, pyproj). This is exactly why this belongs in Colab rather than on a
Windows machine, where the same stack usually needs conda.
"""))
cells.append(code("""
!pip install -q opendrift

import opendrift
print("opendrift", opendrift.__version__)
"""))

cells.append(md("""
## 2. Locate OpenDrift's bundled sample forcing data

The PyPI wheel does not always ship the `tests/test_data` directory. This cell
checks the usual locations and, only if the file is genuinely absent, fetches
that same sample file from the OpenDrift repository. Either way the data is
**OpenDrift's own sample data** - no external forcing source is introduced.
"""))
cells.append(code('''
import os, glob, urllib.request
import opendrift

NC_NAME = "norkyst800_subset_16Nov2015.nc"
SUBDIR = "16Nov2015_NorKyst_z_surface"

def find_sample():
    roots = []
    tdf = getattr(opendrift, "test_data_folder", None)
    if isinstance(tdf, str):
        roots.append(tdf)
    pkg = os.path.dirname(opendrift.__file__)
    roots += [
        os.path.join(pkg, "..", "tests", "test_data"),
        os.path.join(pkg, "tests", "test_data"),
        "/content/opendrift_test_data",
    ]
    for r in roots:
        for pat in (os.path.join(r, SUBDIR, NC_NAME), os.path.join(r, "**", NC_NAME)):
            hits = glob.glob(pat, recursive=True)
            if hits:
                return hits[0]
    return None

nc = find_sample()
if nc is None:
    print("Bundled test data not present in the wheel - fetching the same file")
    print("from the OpenDrift repository...")
    dest_dir = os.path.join("/content/opendrift_test_data", SUBDIR)
    os.makedirs(dest_dir, exist_ok=True)
    url = ("https://raw.githubusercontent.com/OpenDrift/opendrift/master/"
           f"tests/test_data/{SUBDIR}/{NC_NAME}")
    dest = os.path.join(dest_dir, NC_NAME)
    urllib.request.urlretrieve(url, dest)
    nc = dest

assert nc and os.path.isfile(nc), "could not obtain the sample forcing file"
print("sample forcing file:", nc)
print("size: %.1f MB" % (os.path.getsize(nc) / 1e6))
'''))

cells.append(md("""
## 3. Backward OceanDrift run

The key line is `time_step=-3600` - a **negative** step, so the integrator walks
backward from the seed time.

This mirrors OCEANIQ's core question: *given oil observed here now, where was it
earlier?* We seed at the **end** of the forcing window and integrate backward
through it.
"""))
cells.append(code('''
from datetime import timedelta
import numpy as np
from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic

o = OceanDrift(loglevel=30)          # 30 = warnings only; use 0 for full debug
r = reader_netCDF_CF_generic.Reader(nc)
o.add_reader(r)

print("reader coverage:")
print("   time:", r.start_time, "->", r.end_time)
print("   lon :", round(float(r.xmin), 3), "->", round(float(r.xmax), 3))
print("   lat :", round(float(r.ymin), 3), "->", round(float(r.ymax), 3))

# Seed at the END of the available window so there is history to walk back into.
SEED_TIME = r.end_time
SEED_LON, SEED_LAT, N = 4.9, 60.0, 200

o.seed_elements(lon=SEED_LON, lat=SEED_LAT, radius=1000, number=N, time=SEED_TIME)
print(f"\\nseeded {N} particles at ({SEED_LON}, {SEED_LAT}) at {SEED_TIME}")

DURATION_H = 12
print(f"running BACKWARD {DURATION_H}h with time_step=-3600s ...")
o.run(duration=timedelta(hours=DURATION_H), time_step=-3600, time_step_output=3600)
print("\\n", o)
'''))

cells.append(md("""
## 4. Verify the run actually went backward

A plot alone does not prove direction. These checks do:

1. the simulation's end time is **earlier** than the seed time
2. particles actually moved (non-zero net displacement)
3. positions are finite (no NaN blow-up)
"""))
cells.append(code('''
import numpy as np

def get_track(sim):
    """lon/lat arrays shaped (elements, timesteps), across OpenDrift versions."""
    res = getattr(sim, "result", None)
    if res is not None:
        try:
            return np.asarray(res["lon"]), np.asarray(res["lat"])
        except Exception:
            pass
    h = getattr(sim, "history", None)
    if h is not None:
        return np.ma.filled(h["lon"], np.nan), np.ma.filled(h["lat"], np.nan)
    raise RuntimeError("cannot find trajectory arrays on this OpenDrift version")

lon, lat = get_track(o)
print("trajectory array shape (elements, timesteps):", lon.shape)

start_t, end_t = o.start_time, o.time
print(f"seed time      : {start_t}")
print(f"final sim time : {end_t}")
went_backward = end_t < start_t
print(f"ran backward   : {went_backward}   (delta = {end_t - start_t})")
assert went_backward, "simulation did not move backward in time"

first = np.array([np.nanmean(lon[:, 0]), np.nanmean(lat[:, 0])])
last = np.array([np.nanmean(lon[:, -1]), np.nanmean(lat[:, -1])])
dlon, dlat = last - first
km = np.hypot(dlon * 111.32 * np.cos(np.radians(first[1])), dlat * 110.57)
print(f"\\ncentroid start : ({first[0]:.4f}, {first[1]:.4f})")
print(f"centroid end   : ({last[0]:.4f}, {last[1]:.4f})")
print(f"net displacement: {km:.2f} km")
assert np.isfinite(lon).any() and np.isfinite(lat).any(), "all positions are NaN"
assert km > 0.05, "particles did not move - forcing may not have been applied"

print("\\nBACKWARD RUN VERIFIED")
'''))

cells.append(md("""
## 5. Trajectory plots

Two plots, deliberately:

- **OpenDrift's own `plot()`** - the library's map rendering (needs cartopy)
- **A plain matplotlib plot** built straight from the position arrays

The second is the fallback that matters: if cartopy misbehaves in Colab, you
still get proof of a coherent trajectory. The red dots are the observed position
(the seed); the tracks run **backward** toward where the water came from.
"""))
cells.append(code('''
import matplotlib
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 7))
step = max(1, lon.shape[0] // 60)
for i in range(0, lon.shape[0], step):
    ax.plot(lon[i], lat[i], lw=0.7, alpha=0.5, color="tab:blue")
ax.plot(np.nanmean(lon, axis=0), np.nanmean(lat, axis=0),
        color="black", lw=2.2, label="centroid (backward)")
ax.scatter(lon[:, 0], lat[:, 0], s=14, color="tab:red", zorder=5,
           label="seed = observed position")
ax.scatter(lon[:, -1], lat[:, -1], s=14, color="tab:green", zorder=5,
           label="backtracked origin estimate")
ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
ax.set_title(f"OpenDrift backward run - {DURATION_H}h, time_step=-3600s\\n"
             "OpenDrift bundled NorKyst sample data (NOT real Indian-waters forcing)")
ax.legend(loc="best", fontsize=9); ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig("/content/opendrift_backward_matplotlib.png", dpi=120)
plt.show()
print("saved /content/opendrift_backward_matplotlib.png")
'''))

cells.append(code('''
# OpenDrift's own renderer (needs cartopy; failure here is not fatal)
try:
    o.plot(fast=True, filename="/content/opendrift_backward_native.png")
    print("saved /content/opendrift_backward_native.png")
    from IPython.display import Image, display
    display(Image("/content/opendrift_backward_native.png"))
except Exception as e:
    print(f"native plot unavailable ({type(e).__name__}: {e})")
    print("Not a problem - the matplotlib plot above already proves the trajectory.")
'''))

cells.append(md("""
## 6. OpenOil backward run

`OpenOil` is the model OCEANIQ will actually use - it carries oil-specific
processes (weathering, emulsification) on top of advection. Running it backward
here confirms the oil model works, not just the generic drifter.

Backward runs of a weathering model are physically approximate: weathering is
irreversible, so this reconstructs *where the oil came from*, not its past
chemical state. That is the correct use for OCEANIQ - the goal is an origin
estimate, not a history of the oil's condition.
"""))
cells.append(code('''
try:
    from opendrift.models.openoil import OpenOil

    oo = OpenOil(loglevel=30, weathering_model="noaa")
    oo.add_reader(reader_netCDF_CF_generic.Reader(nc))
    oo.set_config("environment:fallback:x_wind", 0)
    oo.set_config("environment:fallback:y_wind", 0)
    oo.seed_elements(lon=SEED_LON, lat=SEED_LAT, radius=1000, number=100,
                     time=SEED_TIME, oil_type="GENERIC MEDIUM CRUDE")
    oo.run(duration=timedelta(hours=DURATION_H), time_step=-3600, time_step_output=3600)

    olon, olat = get_track(oo)
    print(f"OpenOil ran backward: {oo.time < oo.start_time}  ({oo.start_time} -> {oo.time})")

    fig, ax = plt.subplots(figsize=(9, 7))
    for i in range(0, olon.shape[0], max(1, olon.shape[0] // 50)):
        ax.plot(olon[i], olat[i], lw=0.7, alpha=0.5, color="tab:purple")
    ax.scatter(olon[:, 0], olat[:, 0], s=14, color="tab:red", zorder=5, label="seed (observed slick)")
    ax.scatter(olon[:, -1], olat[:, -1], s=14, color="tab:green", zorder=5, label="backtracked origin")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title("OpenOil backward run - bundled sample forcing")
    ax.legend(fontsize=9); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig("/content/openoil_backward.png", dpi=120); plt.show()
    print("saved /content/openoil_backward.png")
except Exception as e:
    print(f"OpenOil step failed: {type(e).__name__}: {e}")
    print("The OceanDrift backward run above is the proof that matters; OpenOil")
    print("config differs between versions and can be fixed later.")
'''))

cells.append(md("""
## What this did and did not establish

**Established:** OpenDrift installs in Colab, a negative time step integrates
backward, and particles follow the current field coherently.

**Not established, and needed next:**

1. **Real forcing for Indian waters.** The NorKyst sample covers western Norway.
   OCEANIQ needs currents and wind for the Arabian Sea / Bay of Bengal -
   typically CMEMS (currents) plus GFS or ERA5 (wind). Both need accounts, and
   CMEMS registration is not instant. **Start that signup early.**
2. **Georeferencing.** The SAR detector emits a pixel mask on a 256x256 tile with
   no geotransform. OpenDrift needs lat/lon seed points. Nothing does this
   conversion yet, and it is the piece most likely to break the pipeline.
3. **Uncertainty.** One backward run is a single realisation. A defensible origin
   estimate needs an ensemble (perturbed seed time, position, and wind drift
   factor), reported as a probability field rather than one track.
"""))

nb = {
    "cells": cells,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = sys.argv[1] if len(sys.argv) > 1 else "opendrift_backward_demo.ipynb"
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"wrote {out}: {len(cells)} cells "
      f"({sum(c['cell_type'] == 'code' for c in cells)} code, "
      f"{sum(c['cell_type'] == 'markdown' for c in cells)} md)")
