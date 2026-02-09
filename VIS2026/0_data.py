import atexit
import logging
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# Suppress aiohttp "Unclosed client session" / "Unclosed connector" on exit
def _suppress_stderr_on_exit():
    sys.stderr = open(os.devnull, "w")
atexit.register(_suppress_stderr_on_exit)

import zarr
import numpy as np
from typing import Dict, Any, List, Tuple
import json
import s3fs
import requests
import ome_types

# Compatible with zarr 2 and 3 (zarr 3 has no hierarchy or items())
if hasattr(zarr, "Group"):
    _ZarrGroup = zarr.Group
    _ZarrArray = zarr.Array
else:
    _ZarrGroup = getattr(zarr.hierarchy, "Group", type(None))
    _ZarrArray = getattr(zarr.core, "Array", type(None))


def _group_items(group):
    """Iterate (key, item) over group members; compatible with zarr 2 and 3."""
    if hasattr(group, "items"):
        yield from group.items()
    else:
        for key in group.keys():
            yield key, group[key]

def get_s3fs():
    """
    Create an S3 filesystem object.
    For public data, we don't need credentials.
    """
    return s3fs.S3FileSystem(anon=True)

def get_channel_names_from_ome(url: str, fs: "s3fs.S3FileSystem | None" = None) -> List[str]:
    """
    Get channel names from OME-XML metadata.
    
    Args:
        url: Base URL of the dataset
        fs: Optional S3 filesystem (for s3:// URLs)
        
    Returns:
        List of channel names
    """
    try:
        # OME-XML file path
        if url.startswith("s3://"):
            metadata_path = url.rstrip("/") + "/OME/METADATA.ome.xml"
            _fs = fs or get_s3fs()
            try:
                with _fs.open(metadata_path, "r") as f:
                    data = f.read()
            except Exception:
                return []
        else:
            import pathlib
            if url.startswith("http://") or url.startswith("https://"):
                metadata_url = url.rstrip("/") + "/OME/METADATA.ome.xml"
                response = requests.get(metadata_url)
                data = response.text
            else:
                metadata_path = pathlib.Path(url).resolve() / "OME" / "METADATA.ome.xml"
                if not metadata_path.exists():
                    return []
                data = metadata_path.read_text(encoding="utf-8")
        
        # Parse the OME-XML
        ome_xml = ome_types.from_xml(data.replace("Â", ""))
        
        # Extract channel names
        channel_names = [c.name for c in ome_xml.images[0].pixels.channels]
        
        return channel_names
    except Exception as e:
        print(f"Error getting channel names from OME-XML: {str(e)}")
        return []

def analyze_zarr_structure(url: str, fs: "s3fs.S3FileSystem | None" = None) -> Dict[str, Any]:
    """
    Analyze the structure of a Zarr array or group.
    
    Args:
        url: URL or path to the Zarr data
        fs: Optional S3 filesystem (for s3:// URLs)
        
    Returns:
        Dictionary containing the structure information
    """
    try:
        # Handle S3 paths
        if url.startswith("s3://"):
            _fs = fs or get_s3fs()
            store = s3fs.S3Map(root=url, s3=_fs)
            z = zarr.open(store, mode='r')
        else:
            z = zarr.open(url, mode='r')
        
        # Initialize result dictionary
        result = {
            'type': 'group' if isinstance(z, _ZarrGroup) else 'array',
            'structure': {}
        }
        
        if isinstance(z, _ZarrGroup):
            # If it's a group, analyze its contents
            for key, item in _group_items(z):
                if isinstance(item, _ZarrArray):
                    result['structure'][key] = {
                        'type': 'array',
                        'shape': item.shape,
                        'dtype': str(item.dtype),
                        'chunks': item.chunks,
                        'compressor': str(getattr(item, 'compressors', getattr(item, 'compressor', None))),
                        'size': item.nbytes / (1024 * 1024 * 1024)  # Size in GB
                    }
                elif isinstance(item, _ZarrGroup):
                    result['structure'][key] = {
                        'type': 'group',
                        'contents': analyze_zarr_structure(f"{url}/{key}", fs=fs)['structure']
                    }
        else:
            # If it's an array, get its properties
            result['structure'] = {
                'shape': z.shape,
                'dtype': str(z.dtype),
                'chunks': z.chunks,
                'compressor': str(getattr(z, 'compressors', getattr(z, 'compressor', None))),
                'size': z.nbytes / (1024 * 1024 * 1024)  # Size in GB
            }
            
        return result
    
    except Exception as e:
        return {'error': str(e)}

def print_zarr_tree(url: str, indent: int = 0, fs: "s3fs.S3FileSystem | None" = None) -> None:
    """
    Print a tree representation of the Zarr structure.
    
    Args:
        url: URL or path to the Zarr data
        indent: Current indentation level
        fs: Optional S3 filesystem (for s3:// URLs)
    """
    try:
        # Handle S3 paths
        if url.startswith("s3://"):
            _fs = fs or get_s3fs()
            store = s3fs.S3Map(root=url, s3=_fs)
            z = zarr.open(store, mode='r')
        else:
            z = zarr.open(url, mode='r')
        
        if isinstance(z, _ZarrGroup):
            for key, item in _group_items(z):
                print(' ' * indent + f'├── {key}')
                if isinstance(item, _ZarrGroup):
                    print_zarr_tree(f"{url}/{key}", indent + 4, fs)
                else:
                    size_gb = item.nbytes / (1024 * 1024 * 1024)
                    print(' ' * (indent + 4) + f'├── shape: {item.shape}')
                    print(' ' * (indent + 4) + f'├── dtype: {item.dtype}')
                    print(' ' * (indent + 4) + f'└── size: {size_gb:.2f} GB')
        else:
            size_gb = z.nbytes / (1024 * 1024 * 1024)
            print(' ' * indent + f'├── shape: {z.shape}')
            print(' ' * indent + f'├── dtype: {z.dtype}')
            print(' ' * indent + f'└── size: {size_gb:.2f} GB')
            
    except Exception as e:
        print(f"Error: {str(e)}")

def get_channel_info(url: str, fs: "s3fs.S3FileSystem | None" = None) -> List[Tuple[int, str]]:
    """
    Get channel names and their indices from the Zarr data.
    
    Args:
        url: URL or path to the Zarr data
        fs: Optional S3 filesystem (for s3:// URLs)
        
    Returns:
        List of tuples containing (index, channel_name)
    """
    try:
        # First try to get channel names from OME-XML (with fs for S3)
        channel_names = get_channel_names_from_ome(url, fs=fs)
        
        if channel_names:
            return [(idx, name) for idx, name in enumerate(channel_names)]
        
        # If OME-XML method fails, fall back to Zarr method
        if url.startswith("s3://"):
            _fs = fs or get_s3fs()
            store = s3fs.S3Map(root=url, s3=_fs)
            z = zarr.open(store, mode='r')
        else:
            z = zarr.open(url, mode='r')
        
        channel_info = []
        
        if isinstance(z, _ZarrGroup):
            # Look for channel names in group attributes
            if hasattr(z, 'attrs') and 'channel_names' in z.attrs:
                channel_names = z.attrs['channel_names']
                for idx, name in enumerate(channel_names):
                    channel_info.append((idx, name))
            else:
                # If no channel names found, use array names as channels
                for idx, (key, item) in enumerate(_group_items(z)):
                    if isinstance(item, _ZarrArray):
                        channel_info.append((idx, key))
        else:
            # If it's a single array, check its attributes
            if hasattr(z, 'attrs') and 'channel_names' in z.attrs:
                channel_names = z.attrs['channel_names']
                for idx, name in enumerate(channel_names):
                    channel_info.append((idx, name))
            else:
                # If no channel names found, use default naming
                channel_info.append((0, 'channel_0'))
        
        return channel_info
    
    except Exception as e:
        print(f"Error getting channel info: {str(e)}")
        return []

def get_channel_index(channel_name: str, channel_list: List[str]) -> int:
    """
    Get the index of a specific channel in the channel list.
    
    Args:
        channel_name: Name of the channel to find
        channel_list: List of all channel names
        
    Returns:
        Index of the channel (0-based) or -1 if not found
    """
    try:
        return channel_list.index(channel_name)
    except ValueError:
        return -1

if __name__ == "__main__":
    # Example usage
    url = "s3://lsp-public-data/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0"
    # url = "D:/Research/vis2025/BestCameraPosition/backend/Input/default_channels_20250521_095553.zarr"

    def _run(fs):
        print("Analyzing Zarr structure...")
        structure = analyze_zarr_structure(url, fs=fs)
        print("\nDetailed structure:")
        print(json.dumps(structure, indent=2))
        print("\nTree representation:")
        print_zarr_tree(url, fs=fs)

    if url.startswith("s3://"):
        fs = get_s3fs()
        _run(fs)
    else:
        _run(None) 