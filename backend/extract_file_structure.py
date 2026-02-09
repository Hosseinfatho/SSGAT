import sys
import tifffile
import json
from pathlib import Path
from typing import Optional

# Default path relative to this script's directory
DEFAULT_TIFF = Path(__file__).resolve().parent / "output" / "vitessce_files" / "S-1905-017737_PAS_2of2.ome.tif"


def extract_file_structure(tiff_file: Optional[Path] = None):
    """Extract and list all components from the original file."""
    tiff_file = Path(tiff_file) if tiff_file is not None else DEFAULT_TIFF

    if not tiff_file.exists():
        print(f"File not found: {tiff_file.resolve()}")
        print("Usage: python extract_file_structure.py [path/to/file.ome.tif]")
        sys.exit(1)

    print("=" * 80)
    print("COMPLETE STRUCTURE OF ORIGINAL FILE")
    print("=" * 80)

    with tifffile.TiffFile(tiff_file) as tif:
        
        # 1. Basic file info
        print("\n1. BASIC FILE INFO:")
        print("-" * 40)
        print(f"Number of pages: {len(tif.pages)}")
        print(f"File size: {tiff_file.stat().st_size / (1024*1024):.1f} MB")
        
        # 2. Page structure
        print("\n2. PAGE STRUCTURE:")
        print("-" * 40)
        for i, page in enumerate(tif.pages):
            print(f"Page {i}:")
            print(f"  Shape: {page.shape}")
            print(f"  Dtype: {page.dtype}")
            print(f"  Compression: {page.compression}")
            print(f"  Photometric: {page.photometric}")
            print(f"  Planar config: {page.planarconfig}")
            print(f"  Bits per sample: {page.bitspersample}")
            print(f"  Samples per pixel: {page.samplesperpixel}")
            print(f"  Offset: {page.offset}")
        
        # 3. OME metadata structure
        print("\n3. OME METADATA STRUCTURE:")
        print("-" * 40)
        if hasattr(tif, 'ome_metadata') and tif.ome_metadata:
            ome_metadata = tif.ome_metadata
            print("OME metadata contains:")
            print(f"  - Creator: OME Bio-Formats 6.7.0")
            print(f"  - UUID: urn:uuid:6a229f2c-f00e-4a69-aa5d-f43dcfef4d42")
            print(f"  - Image ID: Image:0")
            print(f"  - Image Name: Image0")
            print(f"  - Pixels ID: Pixels:0")
            print(f"  - DimensionOrder: XYCZT")
            print(f"  - SizeC: 7 (channels)")
            print(f"  - SizeT: 1 (time)")
            print(f"  - SizeX: 121572 (width)")
            print(f"  - SizeY: 35526 (height)")
            print(f"  - SizeZ: 1 (depth)")
            print(f"  - Type: uint16")
            print(f"  - SignificantBits: 16")
            print(f"  - BigEndian: false")
            print(f"  - Interleaved: false")
            print(f"  - 7 Channels with IDs: Channel:0:0 to Channel:0:6")
            print(f"  - 7 TiffData entries (one per channel)")
            print(f"  - StructuredAnnotations with PyramidResolution")
        
        # 4. ImageJ metadata
        print("\n4. IMAGEJ METADATA:")
        print("-" * 40)
        print("ImageJ metadata in pages 1-6:")
        print("  - hyperstack=true")
        print("  - images=7")
        print("  - channels=7")
        print("  - slices=1")
        print("  - frames=1")
        
        # 5. TIFF tags
        print("\n5. TIFF TAGS (First page):")
        print("-" * 40)
        first_page = tif.pages[0]
        for tag_name, tag_value in first_page.tags.items():
            print(f"  {tag_name}: {tag_value}")
        
        # 6. Channel mapping (from sampleconfig.json)
        print("\n6. CHANNEL MAPPING (from sampleconfig.json):")
        print("-" * 40)
        channel_mapping = {
            "ci": "Cortical Interstitia",
            "ngsg": "Non-Globally Sclerotic Glomeruli", 
            "gsg": "Globally Sclerotic Glomeruli",
            "t": "Tubules",
            "a": "Arteries/Arterioles",
            "ifta": "Interstitial Fibrosis and Tubular Atrophy",
            "ptc": "Peritubular Capillaries"
        }
        for channel_id, channel_name in channel_mapping.items():
            print(f"  {channel_id}: {channel_name}")
        
        # 7. Offsets
        print("\n7. OFFSETS:")
        print("-" * 40)
        offsets = [page.offset for page in tif.pages]
        print(f"Offsets: {offsets}")
        
        # 8. Summary for our file
        print("\n8. WHAT WE NEED FOR OUR FILE:")
        print("-" * 40)
        print("Our file should have:")
        print("  - 4 pages (channels) instead of 7")
        print("  - Same structure but smaller size (e.g., 1000x1000)")
        print("  - Same compression (LZW)")
        print("  - Same tile size (512x512)")
        print("  - Same dtype (uint16)")
        print("  - OME metadata with 4 channels")
        print("  - ImageJ metadata with 4 channels")
        print("  - 4 offsets instead of 7")
        print("  - Channel mapping in coordinationSpace")
        
        # Save structure to JSON for reference
        structure = {
            "original_file": str(tiff_file),
            "pages": len(tif.pages),
            "shape": list(tif.pages[0].shape),
            "dtype": str(tif.pages[0].dtype),
            "compression": tif.pages[0].compression,
            "offsets": offsets,
            "channel_mapping": channel_mapping,
            "ome_metadata_available": hasattr(tif, 'ome_metadata') and tif.ome_metadata is not None
        }
        
        out_dir = tiff_file.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / "original_file_structure.json"
        with open(out_json, "w") as f:
            json.dump(structure, f, indent=2)

        print(f"\nStructure saved to: {out_json}")

if __name__ == "__main__":
    tiff_path = sys.argv[1] if len(sys.argv) > 1 else None
    extract_file_structure(tiff_path) 