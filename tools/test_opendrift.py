"""
OCEANIQ - OpenDrift Backward Tracking Test (Colab)

INSTRUCTIONS:
1. Copy this entire script.
2. Paste it into a new cell in your Colab notebook.
3. Run the cell.

This will verify that OpenDrift is installed correctly and can perform a backward simulation
using its built-in sample forcing data.
"""

# 1. Install OpenDrift (uncomment if not already installed in your Colab)
# !pip install opendrift netCDF4 xarray cartopy

from datetime import timedelta
from opendrift.models.oceandrift import OceanDrift
import os

print("Initializing OceanDrift...")
o = OceanDrift(loglevel=20)

# 2. Add sample forcing data that comes bundled with OpenDrift
sample_data_path = os.path.join(o.test_data_folder(), '16Nov2015_NorKyst_z_surface', 'norkyst800_subset_16Nov2015.nc')
print(f"Adding sample forcing data from: {sample_data_path}")
o.add_readers_from_list([sample_data_path])

# 3. Seed elements at a known time and location (based on the sample data's coverage)
# We will use the start_time of the forcing data as our "spill discovered" time
seed_time = o.env.readers[list(o.env.readers.keys())[0]].start_time + timedelta(hours=24)
lon, lat = 4.8, 60.0

print(f"Seeding 100 particles at {lon}, {lat} on {seed_time}...")
o.seed_elements(lon=lon, lat=lat, time=seed_time, number=100)

# 4. Run BACKWARD in time for 24 hours
print("Running backward simulation (-1 hour time steps) for 24 hours...")
o.run(duration=timedelta(hours=24), time_step=timedelta(hours=-1))

# 5. Plot the trajectory
print("Simulation complete. Generating plot...")
o.plot(fast=True)
