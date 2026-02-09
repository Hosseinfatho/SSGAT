import zarr
import numpy as np
import s3fs
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple

import dask.array as da
from dask.diagnostics import ProgressBar

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VolumeConfig:
    source: str  # "tiff" or "zarr_s3"
    zarr_url: str
    zarr_component: int
    project_root: Path
    data_dir: Path
    channels: Tuple[int, ...]
    base_sx: float
    base_sy: float
    base_sz: float


def default_config() -> VolumeConfig:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    return VolumeConfig(
        source="zarr_s3",
        zarr_url="https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0",
        zarr_component=5,
        project_root=project_root,
        data_dir=data_dir,
        channels=(0,),
        base_sx=0.14,
        base_sy=0.14,
        base_sz=0.28,
    )


def _zarr_url_to_s3_path(zarr_url: str) -> str:
    """Convert HTTPS S3 URL to s3:// path for s3fs. Bucket is from hostname (e.g. lsp-public-data.s3.amazonaws.com -> lsp-public-data)."""
    if zarr_url.startswith("s3://"):
        return zarr_url
    if zarr_url.startswith("https://"):
        # e.g. https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/.../0
        after_slash = zarr_url.split("//", 1)[-1]
        host = after_slash.split("/", 1)[0]
        path = after_slash.split("/", 1)[1] if "/" in after_slash else ""
        bucket = host.split(".")[0]
        return f"s3://{bucket}/{path}"
    return zarr_url


def extract_channels_from_zarr(config: VolumeConfig):
    """Extract selected channels from Zarr using dask and config."""
    try:
        if config.source != "zarr_s3":
            logger.error(f"Unsupported source: {config.source}")
            return None, None, None

        s3_path_full = _zarr_url_to_s3_path(config.zarr_url)
        s3_path = s3_path_full.replace("s3://", "")
        group_url = s3_path_full
        component = str(config.zarr_component)

        logger.info("Creating S3 filesystem...")
        s3 = s3fs.S3FileSystem(anon=True)
        logger.info(f"Loading from group: {group_url}, component: {component}")

        dask_array = da.from_zarr(
            group_url,
            component=component,
            storage_options={"anon": True},
        )
        logger.info(f"Dask array shape: {dask_array.shape}")
        logger.info(f"Chunk size: {dask_array.chunksize}")

        channel_indices = list(config.channels)
        logger.info(f"Selecting channels: {channel_indices}")

        # Assume shape (t, c, z, y, x) or (c, z, y, x)
        ndim = dask_array.ndim
        if ndim == 5:
            selected_channels = dask_array[:, channel_indices, :, :, :]
        elif ndim == 4:
            selected_channels = dask_array[channel_indices, :, :, :]
        else:
            logger.error(f"Unexpected array ndim: {ndim}")
            return None, None, None

        logger.info(f"Selected channels shape: {selected_channels.shape}")
        return selected_channels, channel_indices, dask_array.chunksize

    except Exception as e:
        logger.error(f"Error extracting channels: {e}", exc_info=True)
        return None, None, None

def save_as_zarr(data, output_path, channel_names, chunks):
    """Save data as Zarr format"""
    try:
        # Create output directory
        output_path = Path(output_path).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Creating output directory at: {output_path}")

        # Create Zarr store - use the path directly
        store = str(output_path)
        root = zarr.group(store=store, overwrite=True)

        # Add metadata
        root.attrs['channel_names'] = channel_names
        root.attrs['axes'] = ['t', 'c', 'z', 'y', 'x']
        root.attrs['dimensions'] = {
            't': 1,
            'c': len(channel_names),
            'z': data.shape[2],
            'y': data.shape[3],
            'x': data.shape[4]
        }

        # Create dataset
        dataset = root.create_dataset(
            'data',
            shape=data.shape,
            chunks=chunks,
            dtype=data.dtype
        )

        # Write data with progress bar
        with ProgressBar():
            da.store(data, dataset)

        logger.info(f"Data saved as Zarr in {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving Zarr: {e}", exc_info=True)
        return False

def download_channels(config: VolumeConfig):
    """Download and save selected channels from Zarr data using config."""
    try:
        selected_channels, channel_indices, chunks = extract_channels_from_zarr(config)
        if selected_channels is None:
            return False

        config.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {config.data_dir}")

        zarr_path = config.data_dir / "selected_channels.zarr"
        channel_names = [f"channel_{i}" for i in config.channels]
        save_as_zarr(selected_channels, zarr_path, channel_names, chunks)

        metadata = {
            "shape": selected_channels.shape,
            "dtype": str(selected_channels.dtype),
            "channel_indices": channel_indices,
            "channels": config.channels,
            "zarr_url": config.zarr_url,
            "zarr_component": config.zarr_component,
            "chunks": chunks,
            "base_sx": config.base_sx,
            "base_sy": config.base_sy,
            "base_sz": config.base_sz,
        }
        metadata_path = config.data_dir / "metadata.npy"
        np.save(metadata_path, metadata)
        logger.info(f"Metadata saved at: {metadata_path}")

        return True

    except Exception as e:
        logger.error(f"Error downloading channels: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    config = default_config()
    logger.info("Starting channel download...")
    success = download_channels(config)
    if success:
        logger.info(" Channel download completed successfully")
    else:
        logger.error(" Channel download failed") 