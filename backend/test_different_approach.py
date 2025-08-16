#!/usr/bin/env python3

import zarr
import numpy as np
from pathlib import Path
import os

def test_different_approach():
    """Test using a completely different approach"""
    try:
        # Try using os.path instead of pathlib
        current_dir = os.path.dirname(os.path.abspath(__file__))
        zarr_path = os.path.join(current_dir, "input", "selected_channels.zarr", "data")
        
        print(f"Testing path: {zarr_path}")
        print(f"Path exists: {os.path.exists(zarr_path)}")
        print(f"Is directory: {os.path.isdir(zarr_path)}")
        
        if not os.path.exists(zarr_path):
            print(f"❌ Path does not exist: {zarr_path}")
            return False
            
        # List directory contents
        print(f"Directory contents: {os.listdir(zarr_path)}")
        
        # Try to open the Zarr array using os.path
        try:
            target_image_arr = zarr.open_array(zarr_path, mode='r')
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
    success = test_different_approach()
    if success:
        print("✅ Zarr access test passed!")
    else:
        print("❌ Zarr access test failed!")
