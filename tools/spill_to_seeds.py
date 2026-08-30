import numpy as np

def mask_to_seed_points(mask, transform, when):
    """
    Converts a binary pixel mask of a spill into a list of real-world seed points (lat, lon, time).
    
    Args:
        mask (np.ndarray): 256x256 binary mask (e.g., >127 is oil).
        transform (tuple or object): Geotransform to convert (x, y) pixels to (lon, lat).
                                     For the demo, we pass an anchoring function.
        when (str or datetime): The timestamp of the satellite image (when the spill was discovered).
        
    Returns:
        list of dict: [{"lat": lat, "lon": lon, "time": when}, ...]
    """
    points = []
    
    # 1. Find all pixel coordinates where the mask is positive (oil)
    # mask > 127 is the threshold validated in Pillar 1
    y_coords, x_coords = np.where(mask > 127)
    
    # 2. To avoid simulating millions of particles for large spills,
    # we can sample the points or just take every Nth pixel.
    # For demo purposes, let's take up to 1000 points.
    step = max(1, len(x_coords) // 1000)
    
    for x, y in zip(x_coords[::step], y_coords[::step]):
        # Apply the geotransform
        if callable(transform):
            lon, lat = transform(x, y)
        else:
            # Standard affine transform (e.g. from rasterio: ~affine.Affine)
            lon, lat = transform * (x, y)
            
        points.append({
            "lat": float(lat),
            "lon": float(lon),
            "time": when
        })
        
    return points

def get_demo_transform(anchor_lon=68.5, anchor_lat=18.5, pixel_size_deg=0.0001):
    """
    PATH (B) - Demo Placement
    Creates a callable transform that anchors the top-left of the 256x256 tile
    to a specific coordinate in the Arabian Sea, assuming a fixed pixel size.
    
    This is explicitly for the hackathon demo. For production (Path A), 
    Sentinel-1 GeoTIFFs should be used with rasterio.transform.
    """
    def transform(x, y):
        # lon increases to the right (x), lat decreases downwards (y)
        lon = anchor_lon + (x * pixel_size_deg)
        lat = anchor_lat - (y * pixel_size_deg)
        return lon, lat
    return transform

if __name__ == "__main__":
    # Smoke test
    print("Testing mask_to_seed_points with Path (B) Demo Transform...")
    dummy_mask = np.zeros((256, 256), dtype=np.uint8)
    dummy_mask[120:130, 140:150] = 255 # Create a 10x10 spill block
    
    demo_transform = get_demo_transform(anchor_lon=68.5, anchor_lat=18.5)
    
    seeds = mask_to_seed_points(dummy_mask, demo_transform, "2024-01-15T12:00:00Z")
    print(f"Generated {len(seeds)} seed points.")
    print("Sample seed:", seeds[0])
