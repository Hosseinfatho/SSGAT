"""
Read each channel .npy, normalize to [0, 1] using 5th–90th percentiles (90th -> 1),
set values below 5% of max to 0 (noise filter), save to data/NormalizedChannel.

Dimension convention everywhere: (channel, z, y, x) = (C, Z, Y, X).
Here each saved file is one channel: shape (Z, Y, X). Stacking all gives (C, Z, Y, X).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNELS_DIR = Path(__file__).resolve().parent / "data" / "channels"
NORMALIZED_DIR = Path(__file__).resolve().parent / "data" / "NormalizedChannel"
CHANNEL_MIN_MAX_PATH = Path(__file__).resolve().parent / "output" / "channel_min_max.json"
CHANNEL_INVESTIGATION_PATH = CHANNELS_DIR / "channel_investigation.json"

# Percentile-based normalization: scale so 90th percentile -> 1; values below 5% of max -> 0 (noise)
PERCENTILE_LOW = 5
PERCENTILE_HIGH = 90
NOISE_THRESHOLD = 0.05  # normalized values below this (5% of max) set to 0


def load_min_max_per_channel(
    min_max_path: Path = CHANNEL_MIN_MAX_PATH,
    fallback_path: Path = CHANNEL_INVESTIGATION_PATH,
) -> List[Tuple[Optional[float], Optional[float]]]:
    """
    Load min/max for each channel (by index). Returns list of (min, max) for channel 0, 1, ...
    """
    for path in (min_max_path, fallback_path):
        if not path.exists():
            continue
        with open(path) as f:
            data = json.load(f)
        if not data:
            continue
        out = []
        for rec in data:
            mn = rec.get("min")
            mx = rec.get("max")
            if mn is not None:
                mn = float(mn)
            if mx is not None:
                mx = float(mx)
            out.append((mn, mx))
        return out
    return []


def load_channel_metadata(
    min_max_path: Path = CHANNEL_MIN_MAX_PATH,
) -> List[Tuple[Optional[float], Optional[float], str]]:
    """
    Load min, max, and name for each channel. Returns list of (min, max, name).
    """
    if not min_max_path.exists():
        return []
    with open(min_max_path) as f:
        data = json.load(f)
    if not data:
        return []
    out = []
    for rec in data:
        mn = rec.get("min")
        mx = rec.get("max")
        name = rec.get("name", "unknown")
        if mn is not None:
            mn = float(mn)
        if mx is not None:
            mx = float(mx)
        out.append((mn, mx, name))
    return out


def normalize_channel(arr: np.ndarray, min_val: Optional[float], max_val: Optional[float]) -> np.ndarray:
    """
    Normalize array to [0, 1] using min_val and max_val; round to 2 decimal places.
    If max_val <= min_val or either is None, return zeros (or 0.5).
    """
    arr = np.asarray(arr, dtype=np.float64)
    if min_val is None or max_val is None:
        return np.zeros_like(arr, dtype=np.float32)
    if max_val <= min_val:
        return np.full_like(arr, 0.5, dtype=np.float32)
    out = (arr - min_val) / (max_val - min_val)
    out = np.clip(out, 0.0, 1.0)
    out = np.round(out, 2).astype(np.float32)
    return out


def normalize_channel_percentile(
    arr: np.ndarray,
    p_low: float = PERCENTILE_LOW,
    p_high: float = PERCENTILE_HIGH,
    noise_threshold: float = NOISE_THRESHOLD,
) -> np.ndarray:
    """
    Normalize using percentiles: p_low -> 0, p_high -> 1 (values >= p_high become 1).
    Set all values below noise_threshold (5% of max) to 0 to remove noise.
    Round to 2 decimal places.
    """
    arr = np.asarray(arr, dtype=np.float64)
    pl = float(np.percentile(arr, p_low))
    ph = float(np.percentile(arr, p_high))
    if ph <= pl:
        out = np.zeros_like(arr, dtype=np.float32)
        return out
    out = (arr - pl) / (ph - pl)
    out = np.clip(out, 0.0, 1.0)
    out[out < noise_threshold] = 0.0
    out = np.round(out, 2).astype(np.float32)
    return out


def normalize_and_save_all(
    channels_dir: Path = CHANNELS_DIR,
    normalized_dir: Path = NORMALIZED_DIR,
    min_max_path: Path = CHANNEL_MIN_MAX_PATH,
) -> List[Path]:
    """
    Read each channel .npy, normalize to [0,1] using 5th–90th percentiles (90th -> 1),
    set values < 5% of max to 0 (noise), save to normalized_dir.
    Print each channel's max and mean after normalization.
    Returns list of saved paths.
    """
    meta = load_channel_metadata(min_max_path)
    if not meta:
        min_max_list = load_min_max_per_channel(min_max_path)
        if not min_max_list:
            raise FileNotFoundError(
                f"No channel min/max found. Run investigate.py first to create {CHANNEL_MIN_MAX_PATH}"
            )
        meta = [(mn, mx, f"channel_{i}") for i, (mn, mx) in enumerate(min_max_list)]
    normalized_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    print("\n" + "=" * 60)
    print("Normalized channels (5th–90th percentile, noise < 5% set to 0): max and mean")
    print("=" * 60)
    for i, (_min_val, _max_val, name) in enumerate(meta):
        npy_path = channels_dir / f"{i}.npy"
        if not npy_path.exists():
            logger.warning("Skip channel %d: %s not found", i, npy_path)
            continue
        arr = np.load(npy_path)
        arr_norm = normalize_channel_percentile(
            arr,
            p_low=PERCENTILE_LOW,
            p_high=PERCENTILE_HIGH,
            noise_threshold=NOISE_THRESHOLD,
        )
        logger.info(
            "Normalizing channel %d %s (percentiles %s–%s, noise < %s)",
            i, name, PERCENTILE_LOW, PERCENTILE_HIGH, NOISE_THRESHOLD,
        )
        out_path = normalized_dir / f"{i}.npy"
        np.save(out_path, arr_norm)
        saved.append(out_path)
        ch_max = float(np.max(arr_norm))
        ch_mean = float(np.mean(arr_norm))
        print(f"  {name}:  max={ch_max:.2f}, mean={ch_mean:.2f}")
    print("=" * 60)
    logger.info("Saved %d normalized channels to %s", len(saved), normalized_dir)
    return saved


if __name__ == "__main__":
    paths = normalize_and_save_all()
    print(f"Normalized {len(paths)} channels -> {NORMALIZED_DIR}")
