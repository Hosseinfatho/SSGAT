"""
Pipeline: load preprocessed .npy by microenvironment -> create 16x16x12 subgraphs -> train GAT -> extract positions -> save JSON.
Dimension convention everywhere: (channel, z, y, x) = (C, Z, Y, X). Preprocessed file shape (C, Z, Y, X).
"""

from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Batch, Data
from torch_geometric.nn import GATConv, global_add_pool, global_max_pool, global_mean_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CHANNEL_SET_PATH = BASE_DIR / "data" / "channels" / "channel_set.json"
NORMALIZED_DIR = BASE_DIR / "data" / "NormalizedChannel"
PREPROCESSED_DIR = BASE_DIR / "data" / "preprocessed"
OUTPUT_DIR = BASE_DIR / "output"
SUBGRAPHS_DIR = BASE_DIR / "data" / "subgraphs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Default configuration: 1-4 channel names + microenvironment name
# ---------------------------------------------------------------------------
CHANNEL_NAMES: List[str] = ["SOX10", "MITF", "PMEL", "MART1"]
MICROENVIRONMENT_NAME: str = "Melanocytic tumor identity"

# Subgraph: fixed patch size z=12, x=16, y=16. Each subgraph saved as small .npz (patch + origin).
PATCH_Z = 12
PATCH_Y = 16
PATCH_X = 16

# Training
EPOCHS = 2
BATCH_SIZE = 32
LR = 0.01
HIDDEN = 32
PROJ_DIM = 16
HEADS = 4
DROPOUT = 0.1
TOP_K_POSITIONS = 500


def microenvironment_to_filename(name: str) -> str:
    """Short filename: e.g. 'Melanocytic tumor identity' -> 'Melanocytic'."""
    s = name.strip().split()[0] if name.strip() else "preprocessed"
    return "".join(c for c in s if c.isalnum() or c in "._-") or "preprocessed"


def load_preprocessed(microenvironment_name: str, preprocessed_dir: Path = PREPROCESSED_DIR) -> np.ndarray:
    """
    Load preprocessed .npy. File is (N, 5) with columns [channel, value, z, y, x].
    Rebuild volume (C, Z, Y, X) so that volume[c, z, y, x] = value from row (c, value, z, y, x).
    Returns (C, Z, Y, X) float32 for pipeline.
    """
    fname = microenvironment_to_filename(microenvironment_name) + ".npy"
    path = preprocessed_dir / fname
    if not path.exists():
        raise FileNotFoundError(f"Preprocessed file not found: {path}. Run preprocess first.")
    data = np.load(path).astype(np.float32)
    if data.ndim == 2 and data.shape[1] == 5:
        # Table format: columns [channel, value, z, y, x]
        c_col, v_col, z_col, y_col, x_col = 0, 1, 2, 3, 4
        C = int(data[:, c_col].max()) + 1
        Z = int(data[:, z_col].max()) + 1
        Y = int(data[:, y_col].max()) + 1
        X = int(data[:, x_col].max()) + 1
        volume = np.zeros((C, Z, Y, X), dtype=np.float32)
        volume[data[:, c_col].astype(np.int32), data[:, z_col].astype(np.int32), data[:, y_col].astype(np.int32), data[:, x_col].astype(np.int32)] = data[:, v_col]
        return volume
    if data.ndim == 5:
        return data[:, 0, :, :, :].astype(np.float32)  # legacy (C, 1, Z, Y, X)
    if data.ndim == 4:
        return data.astype(np.float32)  # (C, Z, Y, X)
    raise ValueError(f"Unexpected preprocessed shape: {data.shape}")


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
    """Load normalized .npy for each channel index; return (channel, z, y, x) = (C, Z, Y, X)."""
    channels = []
    for i in channel_indices:
        path = NORMALIZED_DIR / f"{i}.npy"
        if not path.exists():
            raise FileNotFoundError(f"Normalized channel not found: {path}")
        arr = np.load(path)
        channels.append(arr)
    return np.stack(channels, axis=0).astype(np.float32)


def _grid_3d_edges_zyx(nz: int, ny: int, nx: int) -> Tuple[np.ndarray, np.ndarray]:
    """6-neighbor edges for grid with dimension order (z, y, x). Node index = z*ny*nx + y*nx + x."""
    def idx(z: int, y: int, x: int) -> int:
        return z * ny * nx + y * nx + x
    src, dst = [], []
    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                i = idx(z, y, x)
                if z + 1 < nz:
                    src.append(i); dst.append(idx(z + 1, y, x))
                if y + 1 < ny:
                    src.append(i); dst.append(idx(z, y + 1, x))
                if x + 1 < nx:
                    src.append(i); dst.append(idx(z, y, x + 1))
    return np.array(src, dtype=np.int64), np.array(dst, dtype=np.int64)


def create_subgraphs_3d(
    volume: np.ndarray,
    patch_z: int = PATCH_Z,
    patch_y: int = PATCH_Y,
    patch_x: int = PATCH_X,
    save_dir: Optional[Path] = None,
) -> Tuple[List[Data], List[Path]]:
    """
    Build one graph per non-overlapping patch. Volume shape (channel, z, y, x) = (C, Z, Y, X).
    Patch size z=12, y=16, x=16. Each patch has all channel values and local coords (0..11, 0..15, 0..15).
    If save_dir is set, each subgraph is saved as a small .npz with:
      - "patch": (C, PATCH_Z, PATCH_Y, PATCH_X) float32 — values for all channels in that patch
      - "origin": (3,) int (iz, iy, ix) — coordinates of patch in the full volume
    Returns (list of Data for training, list of saved .npz paths).
    """
    C, Z, Y, X = volume.shape
    edge_src, edge_dst = _grid_3d_edges_zyx(patch_z, patch_y, patch_x)
    edge_index = np.stack([np.concatenate([edge_src, edge_dst]), np.concatenate([edge_dst, edge_src])], axis=0)
    edge_attr = np.ones(edge_index.shape[1], dtype=np.float32)

    graphs = []
    saved_paths: List[Path] = []
    index_list: List[Dict[str, Any]] = []
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    for iz in range(0, Z, patch_z):
        for iy in range(0, Y, patch_y):
            for ix in range(0, X, patch_x):
                patch = volume[:, iz:iz + patch_z, iy:iy + patch_y, ix:ix + patch_x].copy()
                if patch.shape[1] < patch_z or patch.shape[2] < patch_y or patch.shape[3] < patch_x:
                    pad = np.zeros((C, patch_z, patch_y, patch_x), dtype=volume.dtype)
                    pad[:, :patch.shape[1], :patch.shape[2], :patch.shape[3]] = patch
                    patch = pad
                origin = np.array([iz, iy, ix], dtype=np.int32)
                if save_dir is not None:
                    npz_path = save_dir / f"subgraph_iz{iz}_iy{iy}_ix{ix}.npz"
                    np.savez_compressed(npz_path, patch=patch.astype(np.float32), origin=origin)
                    saved_paths.append(npz_path)
                    index_list.append({"file": npz_path.name, "origin": [int(iz), int(iy), int(ix)]})
                # (C, PZ, PY, PX) -> (PZ*PY*PX, C) for GAT
                nodes = patch.reshape(C, -1).T
                x_t = torch.tensor(nodes, dtype=torch.float32)
                center = (iz, iy, ix)
                graphs.append(Data(
                    x=x_t,
                    edge_index=torch.tensor(edge_index, dtype=torch.long),
                    edge_attr=torch.tensor(edge_attr, dtype=torch.float32),
                    center=center,
                ))
    if save_dir is not None and index_list:
        with open(save_dir / "index.json", "w") as f:
            json.dump({"patch_shape": [patch_z, patch_y, patch_x], "subgraphs": index_list}, f, indent=2)
    return graphs, saved_paths


def load_subgraph_npz(npz_path: Path) -> Tuple[np.ndarray, Tuple[int, int, int]]:
    """
    Load one subgraph .npz. Returns (patch, origin).
    patch shape (C, PATCH_Z, PATCH_Y, PATCH_X); value at channel c, local (z,y,x) = patch[c,z,y,x].
    origin = (iz, iy, ix); global coords = (iz+z, iy+y, ix+x).
    """
    data = np.load(npz_path)
    patch = data["patch"]
    origin = tuple(int(data["origin"][i]) for i in range(3))
    return patch, origin


def prepare_graph(g: Data, target_channels: int) -> Data:
    """Pad or trim node features to target_channels."""
    x = g.x.clone()
    if x.shape[1] < target_channels:
        x = torch.cat([x, torch.zeros(x.shape[0], target_channels - x.shape[1])], dim=1)
    elif x.shape[1] > target_channels:
        x = x[:, :target_channels]
    return Data(x=x, edge_index=g.edge_index.clone(), edge_attr=g.edge_attr.clone() if g.edge_attr is not None else None, center=g.center)


def augment_graph(g: Data, target_channels: int, mask_ratio: float = 0.1) -> Data:
    """Random node mask for contrastive learning."""
    g = prepare_graph(g, target_channels)
    n = g.x.shape[0]
    k = max(1, int(n * mask_ratio))
    idx = torch.randperm(n)[:k]
    g.x[idx] = 0.0
    return g


class ContrastiveGAT(nn.Module):
    def __init__(self, in_channels: int, hidden: int = 32, proj_dim: int = 16, heads: int = 4, dropout: float = 0.1, edge_dim: Optional[int] = 1):
        super().__init__()
        self.edge_dim = edge_dim
        kw = dict(dropout=dropout)
        if edge_dim is not None:
            kw["edge_dim"] = edge_dim
        self.gat1 = GATConv(in_channels, hidden, heads=heads, concat=True, **kw)
        self.gat2 = GATConv(hidden * heads, hidden, heads=heads, concat=True, **kw)
        self.gat3 = GATConv(hidden * heads, hidden, heads=1, concat=False, **kw)
        self.norm1 = nn.LayerNorm(hidden * heads)
        self.norm2 = nn.LayerNorm(hidden * heads)
        self.dropout = nn.Dropout(dropout)
        self.projection = nn.Sequential(
            nn.Linear(hidden * 3, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, proj_dim)
        )
        self.score_head = nn.Sequential(
            nn.Linear(hidden * 3, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden // 2, 1)
        )

    def forward(self, x, edge_index, edge_attr=None, batch=None):
        ea = edge_attr if self.edge_dim and edge_attr is not None else None
        x = F.elu(self.dropout(self.norm1(self.gat1(x, edge_index, ea))))
        x = F.elu(self.dropout(self.norm2(self.gat2(x, edge_index, ea))))
        x = F.elu(self.gat3(x, edge_index, ea))
        if batch is None:
            batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)
        emb = torch.cat([global_mean_pool(x, batch), global_max_pool(x, batch), global_add_pool(x, batch)], dim=1)
        proj = F.normalize(self.projection(emb), dim=1)
        score = self.score_head(emb)
        return proj, score


def contrastive_loss(z1: torch.Tensor, z2: torch.Tensor, temperature: float = 0.1) -> torch.Tensor:
    z1, z2 = F.normalize(z1, dim=1), F.normalize(z2, dim=1)
    sim = torch.matmul(z1, z2.T) / temperature
    n = z1.size(0)
    labels = torch.arange(n, device=z1.device)
    return (F.cross_entropy(sim, labels) + F.cross_entropy(sim.T, labels)) / 2.0


def train_model(
    model: ContrastiveGAT,
    graphs: List[Data],
    device: torch.device,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    lr: float = LR,
) -> ContrastiveGAT:
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    target_ch = max(g.x.shape[1] for g in graphs)
    for epoch in range(epochs):
        random.shuffle(graphs)
        total_loss = 0.0
        n_batches = 0
        for i in range(0, len(graphs), batch_size):
            batch_g = graphs[i : i + batch_size]
            aug1 = [augment_graph(g, target_ch) for g in batch_g]
            aug2 = [augment_graph(g, target_ch) for g in batch_g]
            for g in aug1 + aug2:
                g.x = g.x.to(device)
                g.edge_index = g.edge_index.to(device)
                if g.edge_attr is not None:
                    g.edge_attr = g.edge_attr.to(device)
            try:
                b1 = Batch.from_data_list(aug1)
                b2 = Batch.from_data_list(aug2)
            except Exception:
                continue
            z1, _ = model(b1.x, b1.edge_index, getattr(b1, "edge_attr", None), b1.batch)
            z2, _ = model(b2.x, b2.edge_index, getattr(b2, "edge_attr", None), b2.batch)
            loss = contrastive_loss(z1, z2)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        avg = total_loss / n_batches if n_batches else 0.0
        logger.info("Epoch %d/%d loss: %.4f", epoch + 1, epochs, avg)
    return model


def extract_positions(
    model: ContrastiveGAT,
    graphs: List[Data],
    device: torch.device,
    top_k: int = TOP_K_POSITIONS,
) -> List[Dict[str, Any]]:
    """Run model on each graph; return list of {x, y, z, score, ...} sorted by score descending."""
    model.eval()
    target_ch = max(g.x.shape[1] for g in graphs)
    results = []
    with torch.no_grad():
        for g in graphs:
            g_prep = prepare_graph(g, target_ch)
            x = g_prep.x.to(device)
            edge_index = g_prep.edge_index.to(device)
            edge_attr = g_prep.edge_attr.to(device) if g_prep.edge_attr is not None else None
            _, score = model(x, edge_index, edge_attr, batch=None)
            sc = score.item()
            iz, iy, ix = g.center  # patch origin (z, y, x)
            results.append({
                "x": int(ix), "y": int(iy), "z": int(iz),
                "score": round(float(sc), 6),
                "num_nodes": int(g.x.shape[0]),
                "num_edges": int(g.edge_index.shape[1]),
            })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def run_pipeline(
    channel_names: Optional[List[str]] = None,
    microenvironment_name: Optional[str] = None,
    output_dir: Path = OUTPUT_DIR,
    preprocessed_dir: Path = PREPROCESSED_DIR,
) -> str:
    """
    Full pipeline: load preprocessed .npy -> create 16x16x12 subgraphs (42*22*1) -> train -> extract positions -> save JSON.
    Returns path to saved JSON.
    """
    microenvironment_name = microenvironment_name or MICROENVIRONMENT_NAME
    channel_names = channel_names or CHANNEL_NAMES

    logger.info("Microenvironment: %s", microenvironment_name)
    logger.info("Channels (from config): %s", channel_names)

    volume = load_preprocessed(microenvironment_name, preprocessed_dir)
    logger.info("Preprocessed volume shape (C, Z, Y, X): %s", volume.shape)

    C, Z, Y, X = volume.shape
    nz = (Z + PATCH_Z - 1) // PATCH_Z
    ny = (Y + PATCH_Y - 1) // PATCH_Y
    nx = (X + PATCH_X - 1) // PATCH_X
    logger.info("Subgraph grid: %d x %d x %d = %d subgraphs (patch Z*Y*X = %d*%d*%d)", nz, ny, nx, nz * ny * nx, PATCH_Z, PATCH_Y, PATCH_X)

    subgraphs_save_dir = SUBGRAPHS_DIR / microenvironment_to_filename(microenvironment_name)
    graphs, subgraph_paths = create_subgraphs_3d(
        volume, patch_z=PATCH_Z, patch_y=PATCH_Y, patch_x=PATCH_X, save_dir=subgraphs_save_dir
    )
    logger.info("Created %d subgraphs and saved to %s", len(graphs), subgraphs_save_dir)

    if len(graphs) < 2:
        raise RuntimeError("Too few subgraphs for training.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    in_ch = volume.shape[0]
    model = ContrastiveGAT(
        in_channels=in_ch,
        hidden=HIDDEN,
        proj_dim=PROJ_DIM,
        heads=HEADS,
        dropout=DROPOUT,
        edge_dim=1,
    ).to(device)

    train_model(model, graphs, device, epochs=EPOCHS, batch_size=BATCH_SIZE, lr=LR)

    positions = extract_positions(model, graphs, device, top_k=TOP_K_POSITIONS)

    out_data = {
        "microenvironment": microenvironment_name,
        "channel_names": channel_names,
        "volume_shape": [int(C), int(Z), int(Y), int(X)],
        "patch_shape": [PATCH_Z, PATCH_Y, PATCH_X],
        "subgraphs_dir": str(subgraphs_save_dir),
        "num_graphs": len(graphs),
        "positions": positions,
    }
    safe_name = microenvironment_name.replace(" ", "_").replace("/", "_")[:64]
    out_path = output_dir / f"positions_{safe_name}.json"
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    logger.info("Saved %d positions to %s", len(positions), out_path)
    return str(out_path)


if __name__ == "__main__":
    run_pipeline(microenvironment_name=MICROENVIRONMENT_NAME)
