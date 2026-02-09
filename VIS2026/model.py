"""
Pipeline: load preprocessed .npy by microenvironment -> create 16x16x12 subgraphs -> train GAT -> extract positions -> save JSON.
Dimension convention everywhere: (channel, z, y, x) = (C, Z, Y, X). Preprocessed file shape (C, Z, Y, X).
"""

from __future__ import annotations

import json
import logging
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from tqdm import tqdm
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

# Subgraph: composite voxel = n×n×n block. Patch size z=12, x=16, y=16. Each composite voxel = one node.
PATCH_Z = 12
PATCH_Y = 16
PATCH_X = 16
# Interaction radius: connect two composite voxels if ||center_i - center_j||_2 <= r (r = 3 × node size).
INTERACTION_RADIUS = 3 * max(PATCH_Z, PATCH_Y, PATCH_X)  # 48 in grid units; centers spaced by patch size.

# Training
EPOCHS = 10
BATCH_SIZE = 32
LR = 0.01
HIDDEN = 32
PROJ_DIM = 16
HEADS = 4
DROPOUT = 0.1
TOP_K_POSITIONS = 1000
# Node-level score: Score_r^(k)(i) = max{ i_ij^(k) }; optionally take top p% of voxels (paper default 5%).
TOP_PERCENT = 5.0  # top p% by Score_r^(k)(i); used if > 0 to limit output size


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

    patch_coords = [(iz, iy, ix) for iz in range(0, Z, patch_z) for iy in range(0, Y, patch_y) for ix in range(0, X, patch_x)]
    for iz, iy, ix in tqdm(patch_coords, desc="Create subgraphs", unit="patch"):
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


# ---------------------------------------------------------------------------
# Composite-voxel spatial graph (paper: nodes = composite voxels, edges within radius r, w_ij = 1/(||x_i-x_j||+1))
# ---------------------------------------------------------------------------

def build_composite_voxel_graph(
    volume: np.ndarray,
    patch_z: int = PATCH_Z,
    patch_y: int = PATCH_Y,
    patch_x: int = PATCH_X,
    interaction_radius: float = INTERACTION_RADIUS,
) -> Tuple[Data, np.ndarray, np.ndarray]:
    """
    Build spatial graph G=(V,E). Each node i = one composite voxel S_i with:
    - centroid x_i = (iz, iy, ix) in grid coords
    - mean intensity I_i = (mean over patch for each channel) in R^C
    Node feature f_i = (x_i_normalized, I_i) with x_i normalized to [0,1] by volume shape.
    Edge (i,j) in E iff ||x_i - x_j||_2 <= interaction_radius. Edge weight w_ij = 1/(||x_i-x_j||_2+1).
    Returns: (full_graph_Data, centers (M,3), mean_intensities (M,) scalar per node for scoring).
    """
    C, Z, Y, X = volume.shape
    centers = []
    mean_intensities_list = []  # (M, C)
    for iz in range(0, Z, patch_z):
        for iy in range(0, Y, patch_y):
            for ix in range(0, X, patch_x):
                patch = volume[:, iz:iz + patch_z, iy:iy + patch_y, ix:ix + patch_x]
                if patch.size == 0:
                    continue
                # centroid in grid units (use center of patch)
                cz = iz + min(patch_z, patch.shape[1]) // 2
                cy = iy + min(patch_y, patch.shape[2]) // 2
                cx = ix + min(patch_x, patch.shape[3]) // 2
                centers.append([cz, cy, cx])
                mean_i = np.mean(patch, axis=(1, 2, 3)).astype(np.float32)  # (C,)
                mean_intensities_list.append(mean_i)
    centers = np.array(centers, dtype=np.float32)  # (M, 3)
    mean_intensities = np.array(mean_intensities_list, dtype=np.float32)  # (M, C)
    M = centers.shape[0]
    # Normalize centroids to [0,1] for node features
    x_norm = centers.copy()
    x_norm[:, 0] = x_norm[:, 0] / max(Z, 1)
    x_norm[:, 1] = x_norm[:, 1] / max(Y, 1)
    x_norm[:, 2] = x_norm[:, 2] / max(X, 1)
    node_features = np.concatenate([x_norm, mean_intensities], axis=1).astype(np.float32)  # (M, 3+C)
    # Scalar mean per node for pairwise scoring: mean over channels
    mean_scalar = np.mean(mean_intensities, axis=1).astype(np.float32)  # (M,)

    # Edges: (i,j) if ||center_i - center_j||_2 <= r; weight = 1/(dist+1)
    edge_src, edge_dst, edge_w = [], [], []
    for i in tqdm(range(M), desc="Build graph edges", unit="node"):
        for j in range(i + 1, M):
            d = np.sqrt(np.sum((centers[i] - centers[j]) ** 2))
            if d <= interaction_radius:
                w = 1.0 / (float(d) + 1.0)
                edge_src.extend([i, j])
                edge_dst.extend([j, i])
                edge_w.extend([w, w])
    if len(edge_src) == 0:
        # fallback: connect neighbors within radius (both directions)
        for i in range(M):
            for j in range(M):
                if i >= j:
                    continue
                d = np.sqrt(np.sum((centers[i] - centers[j]) ** 2))
                if d <= interaction_radius and d > 0:
                    w = 1.0 / (float(d) + 1.0)
                    edge_src.extend([i, j])
                    edge_dst.extend([j, i])
                    edge_w.extend([w, w])
    edge_index = np.stack([np.array(edge_src), np.array(edge_dst)], axis=0)
    edge_attr = np.array(edge_w, dtype=np.float32)

    full_graph = Data(
        x=torch.tensor(node_features, dtype=torch.float32),
        edge_index=torch.tensor(edge_index, dtype=torch.long),
        edge_attr=torch.tensor(edge_attr, dtype=torch.float32),
    )
    full_graph.centers = centers
    full_graph.mean_intensities = mean_intensities
    full_graph.mean_scalar = mean_scalar
    return full_graph, centers, mean_scalar


def extract_ego_subgraphs(
    full_graph: Data,
    centers: np.ndarray,
    interaction_radius: float = INTERACTION_RADIUS,
) -> List[Data]:
    """
    For each node i, extract subgraph: node i + all j with (i,j) in E (neighbors within radius).
    Each training instance = one center node + neighbors. Returns list of Data for training.
    """
    edge_index = full_graph.edge_index.numpy()
    num_nodes = full_graph.x.shape[0]
    adj = defaultdict(set)
    for t in range(edge_index.shape[1]):
        i, j = int(edge_index[0, t]), int(edge_index[1, t])
        adj[i].add(j)
    subgraphs = []
    for center_idx in tqdm(range(num_nodes), desc="Ego subgraphs", unit="node"):
        neighbors = list(adj[center_idx])
        if len(neighbors) == 0:
            continue
        node_set = {center_idx} | set(neighbors)
        node_list = sorted(node_set)
        local_to_global = {g: l for l, g in enumerate(node_list)}
        n_local = len(node_list)
        x_local = full_graph.x[node_list]
        edge_src, edge_dst, edge_w = [], [], []
        for gi in node_list:
            for gj in adj[gi]:
                if gj not in node_set:
                    continue
                li, lj = local_to_global[gi], local_to_global[gj]
                edge_src.append(li)
                edge_dst.append(lj)
                # Look up edge weight from full graph
                ei, ea = full_graph.edge_index, full_graph.edge_attr
                mask = (ei[0] == gi) & (ei[1] == gj)
                w = float(ea[mask][0]) if mask.any() and ea is not None else 1.0
                edge_w.append(w)
        if len(edge_src) < 1:
            continue
        edge_index_local = torch.tensor([edge_src, edge_dst], dtype=torch.long)
        edge_attr_local = torch.tensor(edge_w, dtype=torch.float32)
        g = Data(x=x_local, edge_index=edge_index_local, edge_attr=edge_attr_local, center_idx=center_idx, center=tuple(centers[center_idx]))
        subgraphs.append(g)
    return subgraphs


def prepare_graph(g: Data, target_channels: int) -> Data:
    """Pad or trim node features to target_channels."""
    x = g.x.clone()
    if x.shape[1] < target_channels:
        x = torch.cat([x, torch.zeros(x.shape[0], target_channels - x.shape[1])], dim=1)
    elif x.shape[1] > target_channels:
        x = x[:, :target_channels]
    return Data(x=x, edge_index=g.edge_index.clone(), edge_attr=g.edge_attr.clone() if g.edge_attr is not None else None, center=g.center)


def augment_graph(g: Data, target_channels: int, mask_ratio: float = 0.1, edge_drop: float = 0.1) -> Data:
    """Node feature masking and optional edge dropping for contrastive learning (paper: Augment)."""
    g = prepare_graph(g, target_channels)
    n = g.x.shape[0]
    k = max(1, int(n * mask_ratio))
    idx = torch.randperm(n)[:k]
    g.x[idx] = 0.0
    if edge_drop > 0 and g.edge_index.numel() > 0:
        e = g.edge_index.shape[1]
        keep = torch.rand(e, device=g.edge_index.device) > edge_drop
        g.edge_index = g.edge_index[:, keep]
        if g.edge_attr is not None:
            g.edge_attr = g.edge_attr[keep]
    return g


class ConGAT(nn.Module):
    """
    Graph attention over composite-voxel spatial graph. Node feature f_i = (x_i_norm, I_i) in R^(3+C).
    Initial edge weight w_ij = 1/(||x_i-x_j||+1); incorporated in attention in a learnable manner (paper:
    learnable bias / data-driven). Updated edge weight is used in GAT and in scoring.
    Output: node embeddings z_i and saliency s_i = sigmoid(w_k^T z_i).
    """
    def __init__(self, in_channels: int, hidden: int = 32, proj_dim: int = 16, heads: int = 4, dropout: float = 0.1, edge_dim: Optional[int] = 1):
        super().__init__()
        self.edge_dim = edge_dim
        kw = dict(dropout=dropout)
        if edge_dim is not None:
            kw["edge_dim"] = edge_dim
        # Learnable edge weight update: raw w_ij -> updated w_ij (paper: "learnable manner" / "learnable bias term")
        self.edge_refine = nn.Sequential(nn.Linear(1, 1))
        self.gat1 = GATConv(in_channels, hidden, heads=heads, concat=True, **kw)
        self.gat2 = GATConv(hidden * heads, hidden, heads=heads, concat=True, **kw)
        self.gat3 = GATConv(hidden * heads, hidden, heads=1, concat=False, **kw)
        self.norm1 = nn.LayerNorm(hidden * heads)
        self.norm2 = nn.LayerNorm(hidden * heads)
        self.dropout = nn.Dropout(dropout)
        # Graph-level projection for contrastive (pool then project)
        self.projection = nn.Sequential(
            nn.Linear(hidden * 3, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, proj_dim)
        )
        # Per-node saliency for category k: s_i = sigmoid(w_k^T z_i)
        self.saliency_head = nn.Linear(hidden, 1)

    def _updated_edge_attr(self, edge_attr: Optional[torch.Tensor]) -> Optional[torch.Tensor]:
        """Transform raw w_ij into updated (learnable) edge weight; kept positive via softplus."""
        if edge_attr is None:
            return None
        out = self.edge_refine(edge_attr.unsqueeze(-1)).squeeze(-1)
        return F.softplus(out)

    def forward(self, x, edge_index, edge_attr=None, batch=None, return_node_emb: bool = False):
        ea = self._updated_edge_attr(edge_attr) if self.edge_dim and edge_attr is not None else None
        x = F.elu(self.dropout(self.norm1(self.gat1(x, edge_index, ea))))
        x = F.elu(self.dropout(self.norm2(self.gat2(x, edge_index, ea))))
        z = F.elu(self.gat3(x, edge_index, ea))  # (N, hidden) node embeddings
        if batch is None:
            batch = torch.zeros(z.size(0), dtype=torch.long, device=z.device)
        emb = torch.cat([global_mean_pool(z, batch), global_max_pool(z, batch), global_add_pool(z, batch)], dim=1)
        proj = F.normalize(self.projection(emb), dim=1)
        saliency = torch.sigmoid(self.saliency_head(z))  # (N, 1) per-node saliency
        if return_node_emb:
            return proj, saliency, z
        return proj, saliency


class ContrastiveGAT(nn.Module):
    """Legacy: voxel-level GAT. Kept for compatibility; prefer ConGAT for composite-voxel graph."""
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
    model: nn.Module,
    graphs: List[Data],
    device: torch.device,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    lr: float = LR,
) -> nn.Module:
    """Train ConGAT (or ContrastiveGAT) with contrastive loss on graph-level projections."""
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    target_ch = max(g.x.shape[1] for g in graphs)
    for epoch in tqdm(range(epochs), desc="Training", unit="epoch"):
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
            out1 = model(b1.x, b1.edge_index, getattr(b1, "edge_attr", None), b1.batch)
            out2 = model(b2.x, b2.edge_index, getattr(b2, "edge_attr", None), b2.batch)
            z1 = out1[0]
            z2 = out2[0]
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


def compute_interaction_scores(
    model: ConGAT,
    full_graph: Data,
    centers: np.ndarray,
    mean_scalar: np.ndarray,
    device: torch.device,
    top_k: Optional[int] = None,
    top_p_percent: float = TOP_PERCENT,
) -> List[Dict[str, Any]]:
    """
    Pairwise interaction (paper Eq. radscore):
      i_ij^(k) = s_i^(k) * s_j^(k) * bar_i_i^(k) * bar_i_j^(k) * w_ij,  j in N_r(i).
    Node-level interaction score (paper Eq. roi_score):
      Score_r^(k)(i) = max { i_ij^(k) : j in N_r(i), j != i }.
    Returns list of composite voxels sorted descending by Score_r^(k)(i). Optionally take top p% (default 5%).
    """
    model.eval()
    x = full_graph.x.to(device)
    edge_index = full_graph.edge_index.to(device)
    edge_attr = full_graph.edge_attr.to(device) if full_graph.edge_attr is not None else None
    batch = torch.zeros(x.size(0), dtype=torch.long, device=device)
    with torch.no_grad():
        _, saliency, _ = model(x, edge_index, edge_attr, batch=batch, return_node_emb=True)
        # Paper: "w_ij is the updated edge weight" in pairwise interaction; use model's learned refinement
        ew_t = model._updated_edge_attr(edge_attr)
        ew = ew_t.cpu().numpy() if ew_t is not None else np.ones(full_graph.edge_index.shape[1])
    s = saliency.squeeze(1).cpu().numpy()  # s_i^(k) saliency for category k
    ei = full_graph.edge_index.cpu().numpy()
    neighbors = defaultdict(list)
    for t in range(ei.shape[1]):
        i, j = int(ei[0, t]), int(ei[1, t])
        if i != j:
            neighbors[i].append((j, ew[t]))
    M = centers.shape[0]
    # Score_r^(k)(i) = max over j in N_r(i) of i_ij^(k)
    node_scores = np.zeros(M)
    for i in tqdm(range(M), desc="Interaction scores", unit="node"):
        best = 0.0
        for j, w_ij in neighbors[i]:
            # i_ij^(k) = s_i * s_j * bar_i_i * bar_i_j * w_ij
            i_ij = s[i] * s[j] * mean_scalar[i] * mean_scalar[j] * w_ij
            if i_ij > best:
                best = i_ij
        node_scores[i] = best
    order = np.argsort(-node_scores)
    n_take = len(order)
    if top_p_percent > 0:
        n_take = max(1, int(np.ceil(M * top_p_percent / 100.0)))
    if top_k is not None and top_k > 0:
        n_take = min(n_take, top_k)
    order = order[:n_take]
    results = []
    for idx in order:
        iz, iy, ix = int(centers[idx, 0]), int(centers[idx, 1]), int(centers[idx, 2])
        results.append({
            "x": int(ix), "y": int(iy), "z": int(iz),
            "score": round(float(node_scores[idx]), 6),  # Score_r^(k)(i)
            "saliency": round(float(s[idx]), 6),         # s_i^(k)
        })
    return results


def run_pipeline(
    channel_names: Optional[List[str]] = None,
    microenvironment_name: Optional[str] = None,
    output_dir: Path = OUTPUT_DIR,
    preprocessed_dir: Path = PREPROCESSED_DIR,
) -> str:
    """
    Full pipeline (paper ConGAT): load preprocessed -> composite-voxel spatial graph (nodes = composite voxels,
    edges within radius r, w_ij=1/(dist+1)) -> train ConGAT on ego subgraphs -> interaction scoring -> save JSON.
    """
    microenvironment_name = microenvironment_name or MICROENVIRONMENT_NAME
    channel_names = channel_names or CHANNEL_NAMES

    logger.info("Microenvironment: %s", microenvironment_name)
    steps = ["Load volume", "Create subgraphs", "Build graph", "Ego subgraphs", "Training", "Scoring", "Save JSON"]
    with tqdm(total=len(steps), desc="Pipeline", unit="step", position=0) as pbar:
        pbar.set_description("1/7 Load volume")
        volume = load_preprocessed(microenvironment_name, preprocessed_dir)
        logger.info("Preprocessed volume shape (C, Z, Y, X): %s", volume.shape)
        pbar.update(1)

        pbar.set_description("2/7 Create subgraphs")
        C, Z, Y, X = volume.shape
        subgraphs_save_dir = SUBGRAPHS_DIR / microenvironment_to_filename(microenvironment_name)
        _, _ = create_subgraphs_3d(
            volume, patch_z=PATCH_Z, patch_y=PATCH_Y, patch_x=PATCH_X, save_dir=subgraphs_save_dir
        )
        pbar.update(1)

        pbar.set_description("3/7 Build graph")
        full_graph, centers, mean_scalar = build_composite_voxel_graph(
            volume, interaction_radius=INTERACTION_RADIUS
        )
        M = full_graph.x.shape[0]
        logger.info("Composite-voxel graph: %d nodes, %d edges (radius r=%.0f)", M, full_graph.edge_index.shape[1], INTERACTION_RADIUS)
        pbar.update(1)

        pbar.set_description("4/7 Ego subgraphs")
        ego_subgraphs = extract_ego_subgraphs(full_graph, centers, INTERACTION_RADIUS)
        logger.info("Ego subgraphs for training: %d", len(ego_subgraphs))
        if len(ego_subgraphs) < 2:
            raise RuntimeError("Too few ego subgraphs for training.")
        pbar.update(1)

        pbar.set_description("5/7 Training")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        in_ch = 3 + C  # centroid (3) + mean intensities (C)
        model = ConGAT(
            in_channels=in_ch,
            hidden=HIDDEN,
            proj_dim=PROJ_DIM,
            heads=HEADS,
            dropout=DROPOUT,
            edge_dim=1,
        ).to(device)
        train_model(model, ego_subgraphs, device, epochs=EPOCHS, batch_size=BATCH_SIZE, lr=LR)
        pbar.update(1)

        pbar.set_description("6/7 Scoring")
        positions = compute_interaction_scores(
            model, full_graph, centers, mean_scalar, device,
            top_k=TOP_K_POSITIONS, top_p_percent=TOP_PERCENT,
        )
        pbar.update(1)

        pbar.set_description("7/7 Save JSON")
    out_data = {
        "microenvironment": microenvironment_name,
        "channel_names": channel_names,
        "volume_shape": [int(C), int(Z), int(Y), int(X)],
        "patch_shape": [PATCH_Z, PATCH_Y, PATCH_X],
        "interaction_radius": float(INTERACTION_RADIUS),
        "subgraphs_dir": str(subgraphs_save_dir),
        "num_composite_voxels": M,
        "score_definition": "Score_r^(k)(i) = max{ i_ij^(k) : j in N_r(i), j!=i }; i_ij^(k) = s_i*s_j*Ibar_i*Ibar_j*w_ij",
        "top_p_percent": TOP_PERCENT,
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
