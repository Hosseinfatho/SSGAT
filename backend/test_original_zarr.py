import zarr
from pathlib import Path

print("Testing original Zarr file with different approaches...")

# Use the same path as in server.py
zarr_path = Path(__file__).parent / "input" / "selected_channels.zarr"
print(f"Zarr path: {zarr_path}")
print(f"Path exists: {zarr_path.exists()}")
print(f"Absolute path: {zarr_path.absolute()}")

# Method 1: Try with path as string
try:
    print("\nMethod 1: Using path as string")
    path_str = str(zarr_path.absolute())
    zarr_group = zarr.open_group(path_str, mode='r')
    print("✅ Success! Group keys:", list(zarr_group.keys()))
    data = zarr_group['data']
    print(f"Data shape: {data.shape}")
    print(f"Data dtype: {data.dtype}")
except Exception as e:
    print(f"❌ Method 1 failed: {e}")

# Method 2: Try with store
try:
    print("\nMethod 2: Using DirectoryStore")
    import zarr.storage
    store = zarr.storage.DirectoryStore(str(zarr_path.absolute()))
    zarr_group = zarr.open_group(store=store, mode='r')
    print("✅ Success! Group keys:", list(zarr_group.keys()))
    data = zarr_group['data']
    print(f"Data shape: {data.shape}")
    print(f"Data dtype: {data.dtype}")
except Exception as e:
    print(f"❌ Method 2 failed: {e}")

# Method 3: Try with different zarr version
try:
    print("\nMethod 3: Using zarr v2 compatibility")
    import zarr.v2
    zarr_group = zarr.v2.open_group(str(zarr_path.absolute()), mode='r')
    print("✅ Success! Group keys:", list(zarr_group.keys()))
    data = zarr_group['data']
    print(f"Data shape: {data.shape}")
    print(f"Data dtype: {data.dtype}")
except Exception as e:
    print(f"❌ Method 3 failed: {e}")

# Method 4: Try with consolidated metadata
try:
    print("\nMethod 4: Using consolidated metadata")
    import json
    with open(zarr_path / "zarr.json", 'r') as f:
        metadata = json.load(f)
    print("Metadata:", metadata)
    
    if metadata.get("consolidated_metadata"):
        print("Has consolidated metadata")
        zarr_group = zarr.open_consolidated(str(zarr_path), mode='r')
        print("✅ Success! Group keys:", list(zarr_group.keys()))
        data = zarr_group['data']
        print(f"Data shape: {data.shape}")
        print(f"Data dtype: {data.dtype}")
    else:
        print("No consolidated metadata")
except Exception as e:
    print(f"❌ Method 4 failed: {e}")
