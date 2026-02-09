"""
Read OME metadata from S3 or HTTP: channel names, intensity range, and image dimensions.
Dataset: s3://lsp-public-data/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import s3fs
import ome_types


# Default dataset (Zarr group root)
DATASET_S3 = "s3://lsp-public-data/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0"

# OME metadata URL for this dataset.
METADATA_HTTP_URL: Optional[str] = (
    "https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/OME/METADATA.ome.xml"
)


def get_all_channel_names(metadata_url: Optional[str] = None) -> List[str]:
    """
    Fetch OME XML and return all channel names in the volume.
    Uses METADATA_HTTP_URL by default.
    """
    url = metadata_url or METADATA_HTTP_URL
    if not url:
        return []
    response = requests.get(url)
    response.raise_for_status()
    data = response.text.replace("\u00c2", "").replace("Â", "")
    ome_xml = ome_types.from_xml(data)
    if not ome_xml.images:
        return []
    return [c.name for c in ome_xml.images[0].pixels.channels]


def _s3_to_http_ome_url(s3_path: str, with_trailing_0: bool = False) -> str:
    """Convert s3://bucket/key to https://bucket.s3.amazonaws.com/key/OME/METADATA.ome.xml"""
    if not s3_path.startswith("s3://"):
        return ""
    rest = s3_path.rstrip("/").replace("s3://", "")
    parts = rest.split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    if not with_trailing_0 and key.endswith("/0"):
        key = key[:-2].rstrip("/")
    path = f"{key}/OME/METADATA.ome.xml" if key else "OME/METADATA.ome.xml"
    return f"https://{bucket}.s3.amazonaws.com/{path}"


def _http_get(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL; return response text or None on error (e.g. 404)."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.ok:
            return resp.text
    except Exception:
        pass
    return None


def _fetch_ome_xml(dataset_url: str, metadata_url: Optional[str], fs: Optional[s3fs.S3FileSystem]) -> Optional[str]:
    """Fetch OME XML from S3 or HTTP. Returns None if not found (no exception)."""
    # 1) Explicit metadata URL
    if metadata_url:
        out = _http_get(metadata_url)
        if out:
            return out
        return None

    # 2) S3: dataset_url/OME/METADATA.ome.xml (may not exist)
    if dataset_url.startswith("s3://"):
        meta_path = dataset_url.rstrip("/") + "/OME/METADATA.ome.xml"
        _fs = fs or s3fs.S3FileSystem(anon=True)
        try:
            with _fs.open(meta_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            pass
        for url in (METADATA_HTTP_URL, _s3_to_http_ome_url(dataset_url, with_trailing_0=False)):
            if url:
                out = _http_get(url)
                if out:
                    return out
        return None

    # 3) HTTP dataset URL
    if dataset_url.startswith("http://") or dataset_url.startswith("https://"):
        url = dataset_url.rstrip("/") + "/OME/METADATA.ome.xml"
        return _http_get(url)

    # 4) Local path
    p = Path(dataset_url).resolve() / "OME" / "METADATA.ome.xml"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def _channel_to_dict(ch) -> Dict[str, Any]:
    """Extract all useful attributes from an ome_types Channel."""
    out = {}
    for attr in ("id", "name", "samples_per_pixel", "fluor", "illumination_type"):
        if hasattr(ch, attr):
            v = getattr(ch, attr)
            if v is not None:
                out[attr] = v
    # Display / intensity range if present (OME-NGFF or custom)
    if hasattr(ch, "window"):
        w = getattr(ch, "window")
        if w is not None:
            out["window"] = {"min": getattr(w, "min", None), "max": getattr(w, "max", None)}
    return out


def _metadata_from_zarr_only(dataset_url: str, fs: Optional[s3fs.S3FileSystem]) -> Dict[str, Any]:
    """Build minimal metadata from Zarr group when OME XML is not available."""
    import zarr
    if hasattr(zarr, "Group"):
        _ZarrGroup = zarr.Group
        _ZarrArray = zarr.Array
    else:
        _ZarrGroup = getattr(zarr.hierarchy, "Group", type(None))
        _ZarrArray = getattr(zarr.core, "Array", type(None))

    def _iter_items(g):
        if hasattr(g, "items"):
            yield from g.items()
        else:
            for k in g.keys():
                yield k, g[k]

    result: Dict[str, Any] = {
        "channel_names": [],
        "channels": [],
        "pixels": {},
        "image_count": 0,
        "source": "zarr_only",
    }

    try:
        if dataset_url.startswith("s3://"):
            _fs = fs or s3fs.S3FileSystem(anon=True)
            store = s3fs.S3Map(root=dataset_url, s3=_fs)
            root = zarr.open(store, mode="r")
        else:
            root = zarr.open(dataset_url, mode="r")

        if not isinstance(root, _ZarrGroup):
            return result

        keys = sorted(_iter_items(root), key=lambda x: x[0])
        for key, item in keys:
            if not isinstance(item, _ZarrArray):
                continue
            result["channel_names"].append(str(key))
            result["channels"].append({"name": str(key), "id": key})

        if result["channel_names"] and keys:
            _, first_arr = next((k, v) for k, v in keys if isinstance(v, _ZarrArray))
            result["pixels"]["sizex"] = first_arr.shape[-1] if first_arr.shape else 0
            result["pixels"]["sizey"] = first_arr.shape[-2] if len(first_arr.shape) >= 2 else 0
            result["pixels"]["sizez"] = first_arr.shape[-3] if len(first_arr.shape) >= 3 else 0
            result["pixels"]["sizec"] = len(result["channel_names"])
            result["pixels"]["sizet"] = 1
            result["pixels"]["type"] = str(getattr(first_arr, "dtype", ""))

        ranges = get_intensity_range_from_zarr(dataset_url, fs)
        for ch in result["channels"]:
            name = ch.get("name", "")
            for r in ranges:
                if str(r.get("channel_key")) == str(name):
                    ch["min"] = r.get("min")
                    ch["max"] = r.get("max")
                    break
    except Exception:
        pass
    return result


def read_metadata(
    dataset_url: str = DATASET_S3,
    metadata_url: Optional[str] = METADATA_HTTP_URL,
    fs: Optional[s3fs.S3FileSystem] = None,
) -> Dict[str, Any]:
    """
    Read OME metadata and return channel names, intensity info, and image dimensions.

    Args:
        dataset_url: S3, HTTP, or local path to the Zarr group (e.g. .../0).
        metadata_url: If set, fetch OME XML from this URL instead of dataset_url/OME/METADATA.ome.xml.
        fs: Optional S3 filesystem for s3:// dataset_url.

    Returns:
        Dict with keys:
          - channel_names: list of channel names
          - channels: list of dicts per channel (name, id, and any min/max/window)
          - pixels: dict with SizeX, SizeY, SizeZ, SizeC, SizeT, Type, PhysicalSizeX/Y/Z if present
          - image_count: number of images in OME
    """
    xml_str = _fetch_ome_xml(dataset_url, metadata_url, fs)
    if xml_str is None:
        return _metadata_from_zarr_only(dataset_url, fs)
    xml_str = xml_str.replace("\u00c2", "")  # BOM / bad encoding
    ome = ome_types.from_xml(xml_str)

    result: Dict[str, Any] = {
        "channel_names": [],
        "channels": [],
        "pixels": {},
        "image_count": len(ome.images),
    }

    if not ome.images:
        return result

    img = ome.images[0]
    pixels = img.pixels

    # Pixels dimensions and type
    for attr in ("size_x", "size_y", "size_z", "size_c", "size_t", "type", "dimension_order"):
        if hasattr(pixels, attr):
            v = getattr(pixels, attr)
            if v is not None:
                key = attr.replace("_", "") if attr != "dimension_order" else attr
                result["pixels"][key] = v
    if hasattr(pixels, "physical_size_x") and pixels.physical_size_x is not None:
        result["pixels"]["physical_size_x"] = pixels.physical_size_x
    if hasattr(pixels, "physical_size_y") and pixels.physical_size_y is not None:
        result["pixels"]["physical_size_y"] = pixels.physical_size_y
    if hasattr(pixels, "physical_size_z") and pixels.physical_size_z is not None:
        result["pixels"]["physical_size_z"] = pixels.physical_size_z

    # Channels
    for ch in pixels.channels:
        name = ch.name if hasattr(ch, "name") and ch.name else ""
        result["channel_names"].append(name)
        result["channels"].append(_channel_to_dict(ch))

    return result


def get_channel_names(
    dataset_url: str = DATASET_S3,
    metadata_url: Optional[str] = METADATA_HTTP_URL,
    fs: Optional[s3fs.S3FileSystem] = None,
) -> List[str]:
    """Return only the list of channel names from OME metadata."""
    meta = read_metadata(dataset_url=dataset_url, metadata_url=metadata_url, fs=fs)
    return meta["channel_names"]


def get_intensity_range_from_zarr(dataset_url: str, fs: Optional[s3fs.S3FileSystem] = None) -> List[Dict[str, Any]]:
    """
    Compute min/max (intensity range) per channel by reading from Zarr arrays.
    Use when OME XML does not contain window/min-max. Requires zarr/s3fs.
    """
    import zarr
    if hasattr(zarr, "Group"):
        _ZarrGroup = zarr.Group
        _ZarrArray = zarr.Array
    else:
        _ZarrGroup = getattr(zarr.hierarchy, "Group", type(None))
        _ZarrArray = getattr(zarr.core, "Array", type(None))

    if dataset_url.startswith("s3://"):
        _fs = fs or s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=dataset_url, s3=_fs)
        root = zarr.open(store, mode="r")
    else:
        root = zarr.open(dataset_url, mode="r")

    def _iter_items(g):
        if hasattr(g, "items"):
            yield from g.items()
        else:
            for k in g.keys():
                yield k, g[k]

    out = []
    for key, item in _iter_items(root):
        if not isinstance(item, _ZarrArray):
            continue
        try:
            arr_min = float(item.min())
            arr_max = float(item.max())
        except Exception:
            arr_min = arr_max = None
        out.append({"channel_key": key, "min": arr_min, "max": arr_max})
    return out


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # 0) All channel names from OME
    print("All channel names (from OME):")
    try:
        channel_names = get_all_channel_names()
        for i, name in enumerate(channel_names):
            print(f"  {i}: {name}")
        print(f"  -> {channel_names}\n")
    except Exception as e:
        print(f"  (skip) {e}\n")

    # 1) Full metadata
    print("Dataset:", DATASET_S3)
    meta = read_metadata(dataset_url=DATASET_S3)
    print(json.dumps(meta, indent=2, default=str))

    # 2) Optionally compute intensity range from Zarr
    print("\nIntensity range from Zarr arrays:")
    try:
        ranges = get_intensity_range_from_zarr(DATASET_S3)
        for r in ranges:
            print(f"  {r['channel_key']}: min={r['min']}, max={r['max']}")
    except Exception as e:
        print(f"  (skip) {e}")

    # 3) Save to file
    out_path = Path(__file__).resolve().parent / "output" / "metadata.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"\nMetadata saved to: {out_path}")
