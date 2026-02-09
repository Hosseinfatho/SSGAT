"""
Read channel .npy files from data/channels one by one; compute name, dimension, min, max, mean; write to JSON.
Use this to fill channel_min_max.json from local .npy files (not from remote Zarr).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNELS_DIR = Path(__file__).resolve().parent / "data" / "channels"
CHANNEL_SET_PATH = CHANNELS_DIR / "channel_set.json"
OUTPUT_INVESTIGATION = CHANNELS_DIR / "channel_investigation.json"
OUTPUT_MIN_MAX = Path(__file__).resolve().parent / "output" / "channel_min_max.json"


def load_channel_set(channel_set_path: Path) -> List[Dict[str, Any]]:
    """Load channel names and paths from channel_set.json."""
    if not channel_set_path.exists():
        return []
    with open(channel_set_path) as f:
        return json.load(f)


def investigate_channel(npy_path: Path) -> Dict[str, Any]:
    """Load one .npy, return dimension (shape), min, max, mean."""
    arr = np.load(npy_path)
    arr = np.asarray(arr)
    return {
        "dimension": list(arr.shape),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "dtype": str(arr.dtype),
    }


def investigate_all(
    channels_dir: Path = CHANNELS_DIR,
    channel_set_path: Path = CHANNEL_SET_PATH,
    output_investigation: Path = OUTPUT_INVESTIGATION,
    output_min_max: Path = OUTPUT_MIN_MAX,
) -> List[Dict[str, Any]]:
    """
    Read each channel .npy from channels_dir one by one; compute name, dimension, min, max, mean; save to JSON.
    Writes: channel_investigation.json (full) and output/channel_min_max.json (name, dimension, min, max, mean).
    """
    channel_set = load_channel_set(channel_set_path)
    if not channel_set:
        # Fallback: find 0.npy, 1.npy, ... and use index as name
        results = []
        for i in range(70):
            p = channels_dir / f"{i}.npy"
            if not p.exists():
                continue
            logger.info("Reading %s", p.name)
            info = investigate_channel(p)
            results.append({
                "channel_index": i,
                "name": str(i),
                "dimension": info["dimension"],
                "min": info["min"],
                "max": info["max"],
                "mean": info["mean"],
                "dtype": info["dtype"],
            })
    else:
        results = []
        for rec in channel_set:
            c = rec["channel_index"]
            name = rec["name"]
            npy_path = Path(rec.get("npy_path", channels_dir / f"{c}.npy"))
            if not npy_path.is_absolute():
                npy_path = channels_dir / npy_path.name
            if not npy_path.exists():
                npy_path = channels_dir / f"{c}.npy"
            if not npy_path.exists():
                logger.warning("Skip channel %d (%s): file not found", c, name)
                results.append({
                    "channel_index": c,
                    "name": name,
                    "dimension": rec.get("shape", []),
                    "min": None,
                    "max": None,
                    "mean": None,
                    "dtype": None,
                })
                continue
            logger.info("Reading channel %d: %s", c, name)
            info = investigate_channel(npy_path)
            results.append({
                "channel_index": c,
                "name": name,
                "dimension": info["dimension"],
                "min": info["min"],
                "max": info["max"],
                "mean": info["mean"],
                "dtype": info["dtype"],
            })

    output_investigation.parent.mkdir(parents=True, exist_ok=True)
    with open(output_investigation, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved %d channels to %s", len(results), output_investigation)

    # Also write output/channel_min_max.json (name, dimension, min, max, mean)
    output_min_max.parent.mkdir(parents=True, exist_ok=True)
    min_max_list = [
        {"name": r["name"], "dimension": r["dimension"], "min": r["min"], "max": r["max"], "mean": r["mean"]}
        for r in results
    ]
    with open(output_min_max, "w") as f:
        json.dump(min_max_list, f, indent=2)
    logger.info("Saved %s", output_min_max)

    return results


if __name__ == "__main__":
    results = investigate_all()
    print(f"Wrote {OUTPUT_INVESTIGATION} and {OUTPUT_MIN_MAX}")
    for r in results[:5]:
        mean_str = f"{r['mean']:.2f}" if r.get('mean') is not None else "N/A"
        print(f"  {r['channel_index']}: {r['name']} dim={r['dimension']} min={r['min']} max={r['max']} mean={mean_str}")
    print("  ...")
