#!/usr/bin/env python3

import zarr
import numpy as np
from pathlib import Path

def test_zarr_open():
    """Test using zarr.open() instead of zarr.open_array()"""
    try:
        zarr_path = Path(__file__).parent / "input" / "selected_channels.zarr"
        print(f"Testing path: {zarr_path}")
        
        if not zarr_path.exists():
            print(f"❌ Path does not exist: {zarr_path}")
            return False
            
        # Try using zarr.open() instead of zarr.open_array()
        try:
            store = zarr.open(str(zarr_path), mode='r')
            print(f"✅ Successfully opened with zarr.open()")
            print(f"Store type: {type(store)}")
            print(f"Store keys: {list(store.keys())}")
            
            if 'data' in store:
                data = store['data']
                print(f"✅ Found 'data' in store")
                print(f"Data type: {type(data)}")
                if hasattr(data, 'shape'):
                    print(f"Data shape: {data.shape}")
                    print(f"Data dtype: {data.dtype}")
                    return True
                else:
                    print(f"Data is not an array")
                    return False
            else:
                print(f"❌ No 'data' key found in store")
                return False
                
        except Exception as e:
            print(f"❌ Failed with zarr.open(): {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        return False

if __name__ == "__main__":
    success = test_zarr_open()
    if success:
        print("✅ Zarr access test passed!")
    else:
        print("❌ Zarr access test failed!")
