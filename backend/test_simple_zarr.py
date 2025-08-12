#!/usr/bin/env python3

import zarr
import numpy as np
from pathlib import Path

def test_simple_zarr():
    """Test using the exact same approach as the reference server"""
    try:
        # Use the exact same constants as the reference server
        LOCAL_ZARR_PATH = Path(__file__).parent / 'input' / 'selected_channels.zarr'
        ZARR_IMAGE_GROUP_PATH = "data"
        TARGET_RESOLUTION_PATH = ""  # Empty string
        
        # Build the path exactly like the reference server
        zarr_path = LOCAL_ZARR_PATH / ZARR_IMAGE_GROUP_PATH / TARGET_RESOLUTION_PATH
        
        print(f"Testing path: {zarr_path}")
        print(f"Path exists: {zarr_path.exists()}")
        print(f"Is directory: {zarr_path.is_dir()}")
        
        if not zarr_path.exists():
            print(f"❌ Path does not exist: {zarr_path}")
            return False
            
        # List directory contents
        print(f"Directory contents: {list(zarr_path.iterdir())}")
        
        # Try to open the Zarr array directly
        try:
            target_image_arr = zarr.open_array(str(zarr_path), mode='r')
            print(f"✅ Successfully opened target Zarr array")
            print(f"Array shape: {target_image_arr.shape}")
            print(f"Array dtype: {target_image_arr.dtype}")
            return True
        except Exception as e:
            print(f"❌ Failed to open array: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        return False

if __name__ == "__main__":
    success = test_simple_zarr()
    if success:
        print("✅ Zarr access test passed!")
    else:
        print("❌ Zarr access test failed!")
