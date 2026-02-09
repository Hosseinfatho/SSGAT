"""
Preprocess: load normalized channels (C, Z, Y, X), aggregate Z every 16 voxels to 1 (average).
Save one .npy as a table where each row is (channel, value, z, y, x).
Value is read from the normalized (and Z-aggregated) channel at (z, y, x).
Example: channel 2 at x=600, y=320, z=10 with value 0.2 -> row (2, 0.2, 10, 320, 600).
Saved array shape: (N, 5) with columns [channel, value, z, y, x]; N = C * Z * Y * X.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CHANNEL_SET_PATH = BASE_DIR / "data" / "channels" / "channel_set.json"
NORMALIZED_DIR = BASE_DIR / "data" / "NormalizedChannel"
PREPROCESSED_DIR = BASE_DIR / "data" / "preprocessed"
PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Same channel/microenvironment config as model.py
CHANNEL_NAMES: List[str] = ["PMEL", "MART1", "PRAME"]
MICROENVIRONMENT_NAME: str = "Melanocytic tumor identity"
# Z aggregation: every this many voxels (along z) are averaged into 1
Z_AGGREGATE = 16

def get_channel_indices(channel_names: List[str]) -> List[int]:
    """Resolve channel names to indices using channel_set.json."""
    if not CHANNEL_SET_PATH.exists():
        raise FileNotFoundError(f"Channel set not found: {CHANNEL_SET_PATH}")
    with open(CHANNEL_SET_PATH) as f:
        channel_set = json.load(f)
    name_to_index = {rec["name"]: rec["channel_index"] for rec in channel_set}
    indices = []
    for name in channel_names:
        if name not in name_to_index:
            raise ValueError(f"Channel name '{name}' not found in channel_set.json")
        indices.append(name_to_index[name])
    return indices


def load_normalized_channels(channel_indices: List[int]) -> np.ndarray:
    """Load normalized .npy for each channel; return (channel, z, y, x) = (C, Z, Y, X)."""
    channels = []
    for i in channel_indices:
        path = NORMALIZED_DIR / f"{i}.npy"
        if not path.exists():
            raise FileNotFoundError(f"Normalized channel not found: {path}")
        arr = np.load(path).astype(np.float32)
        channels.append(arr)
    return np.stack(channels, axis=0)


def aggregate_z(volume: np.ndarray, z_bin: int = Z_AGGREGATE) -> np.ndarray:
    """
    Average every z_bin voxels along axis 1 (Z). Dimension order (channel, z, y, x).
    volume: (C, Z, Y, X) -> out: (C, Z_new, Y, X) with Z_new = Z // z_bin.
    """
    C, Z, Y, X = volume.shape
    n_bins = Z // z_bin  # 194 // 16 = 12
    out = np.zeros((C, n_bins, Y, X), dtype=np.float32)
    for i in range(n_bins):
        start = i * z_bin
        end = min((i + 1) * z_bin, Z)
        out[:, i, :, :] = volume[:, start:end, :, :].mean(axis=1)
    return out


def microenvironment_to_filename(name: str) -> str:
    """Short filename from microenvironment: e.g. 'Melanocytic tumor identity' -> 'Melanocytic'."""
    s = name.strip().split()[0] if name.strip() else "preprocessed"
    return "".join(c for c in s if c.isalnum() or c in "._-") or "preprocessed"


def load_preprocessed_table(npy_path: Path) -> np.ndarray:
    """Load preprocessed .npy; returns (N, 5) with columns [channel, value, z, y, x]."""
    data = np.load(npy_path).astype(np.float32)
    if data.ndim != 2 or data.shape[1] != 5:
        raise ValueError(f"Expected shape (N, 5), got {data.shape}")
    return data


def get_value_at(data: np.ndarray, channel: int, z: int, y: int, x: int) -> float | None:
    """
    Get value for one (channel, z, y, x) from preprocessed table (N, 5).
    Columns: [channel, value, z, y, x]. Returns the value or None if not found.
    Example: get_value_at(data, channel=1, z=10, y=200, x=600)
    """
    mask = (
        (data[:, 0] == channel)
        & (data[:, 2] == z)
        & (data[:, 3] == y)
        & (data[:, 4] == x)
    )
    rows = data[mask]
    if len(rows) == 0:
        return None
    return float(rows[0, 1])


def run_preprocess(
    channel_names: List[str] | None = None,
    microenvironment_name: str | None = None,
    z_aggregate: int = Z_AGGREGATE,
    output_dir: Path | None = None,
) -> Path:
    """
    Load normalized channels (C, Z, Y, X), aggregate Z every z_aggregate voxels.
    Save as .npy: each row = (channel, value, z, y, x); value from normalized channel at (z,y,x).
    """
    channel_names = channel_names or CHANNEL_NAMES
    microenvironment_name = microenvironment_name or MICROENVIRONMENT_NAME
    output_dir = output_dir if output_dir is not None else PREPROCESSED_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not 1 <= len(channel_names) <= 4:
        raise ValueError("Provide 1 to 4 channel names.")

    logger.info("Channels: %s", channel_names)
    logger.info("Microenvironment: %s", microenvironment_name)

    indices = get_channel_indices(channel_names)
    volume = load_normalized_channels(indices)
    # volume: (channel, z, y, x) = (C, Z, Y, X)
    C, Z, Y, X = volume.shape
    logger.info("Loaded volume shape (C,Z,Y,X): %s", volume.shape)

    aggregated = aggregate_z(volume, z_bin=z_aggregate)
    # aggregated: (channel, z, y, x) = (C, Z_agg, Y, X); value at [c,z,y,x] from normalized channel
    Z_agg, Y_agg, X_agg = aggregated.shape[1], aggregated.shape[2], aggregated.shape[3]
    logger.info("After Z aggregate (every %d -> 1): (C,Z_agg,Y,X) = %s", z_aggregate, aggregated.shape)

    # Round values; then build table: each row = (channel, value, z, y, x)
    aggregated = np.round(aggregated.astype(np.float32), 2)
    rows = []
    for c in range(C):
        for z in range(Z_agg):
            for y in range(Y_agg):
                for x in range(X_agg):
                    value = float(aggregated[c, z, y, x])
                    rows.append([c, value, z, y, x])
    out = np.array(rows, dtype=np.float32)  # (N, 5) columns: channel, value, z, y, x
    filename = microenvironment_to_filename(microenvironment_name) + ".npy"
    out_path = output_dir / filename
    np.save(out_path, out)
    logger.info("Saved %s with shape (N, 5); each row = (channel, value, z, y, x)", out_path)
    N = out.shape[0]

    # Print final .npy dimensions and properties to console
    print("\n" + "=" * 50)
    print("Final .npy file: dimensions and properties")
    print("=" * 50)
    print(f"  Path:          {out_path}")
    print(f"  Shape:         (N, 5)  columns = [channel, value, z, y, x]")
    print(f"  N rows:        {N}  (C*Z*Y*X = {C}*{Z_agg}*{Y_agg}*{X_agg})")
    print(f"  ndim:          {out.ndim}")
    print(f"  dtype:         {out.dtype}")
    print(f"  nbytes:        {out.nbytes:,} bytes ({out.nbytes / (1024**2):.2f} MB)")
    print("  Per channel (values in column 1 where column 0 == c):")
    for c in range(C):
        ch_name = channel_names[c] if c < len(channel_names) else f"channel_{c}"
        col0 = out[:, 0]
        vals = out[col0 == c, 1]
        mn = float(np.min(vals)) if len(vals) else 0.0
        mx = float(np.max(vals)) if len(vals) else 0.0
        mu = float(np.mean(vals)) if len(vals) else 0.0
        print(f"    {ch_name}:  min={mn:.2f}, max={mx:.2f}, mean={mu:.2f}")
    print("  Example row: (channel, value, z, y, x) e.g. (2, 0.2, 10, 320, 600)")
    print("  To get value at (channel, z, y, x): use get_value_at(data, channel, z, y, x)")
    print("=" * 50 + "\n")

    return out_path


if __name__ == "__main__":
    run_preprocess(
        channel_names=CHANNEL_NAMES,
        microenvironment_name=MICROENVIRONMENT_NAME,
        z_aggregate=Z_AGGREGATE,
        output_dir=PREPROCESSED_DIR,
    )
    # Example: read value for channel 1 at x=600, y=200, z=10
    out_path = PREPROCESSED_DIR / (microenvironment_to_filename(MICROENVIRONMENT_NAME) + ".npy")
    if out_path.exists():
        data = load_preprocessed_table(out_path)
        value = get_value_at(data, channel=1, z=10, y=100, x=600)
        print("Example lookup: channel=1, z=10, y=200, x=600 -> value =", value)
