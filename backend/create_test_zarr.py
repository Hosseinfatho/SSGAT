import zarr
import numpy as np
from pathlib import Path

# Create a simple test Zarr file
print("Creating test Zarr file...")

# Create test data
test_data = np.random.randint(0, 1000, size=(1, 6, 50, 100, 100), dtype=np.uint16)

# Create Zarr group
zarr_path = Path(__file__).parent / "input" / "test_zarr.zarr"
if zarr_path.exists():
    import shutil
    shutil.rmtree(zarr_path)

# Create the group using the correct API
group = zarr.group(str(zarr_path))

# Create the data array
data_array = group.create_dataset('data', data=test_data, chunks=(1, 1, 10, 50, 50))

print(f"✅ Created test Zarr file at: {zarr_path}")
print(f"Data shape: {data_array.shape}")
print(f"Data dtype: {data_array.dtype}")

# Test reading it back
print("\nTesting reading back...")
try:
    group_read = zarr.open_group(str(zarr_path), mode='r')
    data_read = group_read['data']
    print(f"✅ Successfully read back: {data_read.shape}")
    print(f"Data matches: {np.array_equal(test_data, data_read[:])}")
except Exception as e:
    print(f"❌ Failed to read back: {e}")
