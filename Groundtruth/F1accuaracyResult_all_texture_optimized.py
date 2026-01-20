"""
OPTIMIZED Multi-Texture Scale Experiment
=========================================
- Fast vectorized operations  
- Step-by-step output per texture
- Table per texture + Final Average Table

Usage: python F1accuaracyResult_all_texture_optimized.py
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, global_mean_pool, global_max_pool, global_add_pool
from torch_geometric.data import Data, Batch
import os
import pandas as pd
from tqdm import tqdm
import pickle
import random

# ============================================================================
# Configuration
# ============================================================================
BASE_DIR = r'D:\VIS2025\BIoVisChallenges\SSGAT\Groundtruth\Scale'
os.makedirs(BASE_DIR, exist_ok=True)

ORIGINAL_X, ORIGINAL_Y, ORIGINAL_Z = 681, 344, 12

SCALES = [
    ('original', 1, 1, 1), ('2x1y1z', 2, 1, 1), ('1x2y1z', 1, 2, 1),
    ('1x1y2z', 1, 1, 2), ('2x2y1z', 2, 2, 1), ('1x2y2z', 1, 2, 2),
    ('2x2y2z', 2, 2, 2), ('3x1y1z', 3, 1, 1), ('3x2y1z', 3, 2, 1),
    ('3x1y2z', 3, 1, 2), ('3x2y2z', 3, 2, 2)
]

TEXTURES = ['sinusoid', 'colonies', 'linear', 'olympic', 'oval']
TOP_K, Z_FIXED, MAX_RADIUS, STEP_SIZE = 100, 5, 10, 5


# ============================================================================
# TEXTURE GENERATION FUNCTIONS (Optimized)
# ============================================================================

def generate_sinusoid_texture(num_channels, num_values, z_dim, y_dim, x_dim):
    """Sinusoidal wave patterns"""
    data = np.zeros((num_channels, num_values, z_dim, y_dim, x_dim), dtype=np.int8)
    y_center, strip_size = 100, 20
    sine_params = [(0, 100, 400), (1, 50, 200), (2, 150, 300)]
    
    x_range = np.arange(x_dim)
    for channel, amplitude, period in sine_params:
        y_sine = y_center + amplitude * np.sin(2 * np.pi * x_range / period)
        for z in range(z_dim):
            for x in range(x_dim):
                y_c = int(round(y_sine[x]))
                y_start, y_end = max(0, y_c - strip_size//2), min(y_dim, y_c + strip_size//2 + 1)
                for y in range(y_start, y_end):
                    data[channel, np.random.randint(0, 11), z, y, x] = 1
    
    # Channel 3: horizontal line
    y_start, y_end = max(0, y_center - strip_size//2), min(y_dim, y_center + strip_size//2 + 1)
    for z in range(z_dim):
        for x in range(x_dim):
            for y in range(y_start, y_end):
                data[3, np.random.randint(0, 11), z, y, x] = 1
    return data


def generate_linear_texture(num_channels, num_values, z_dim, y_dim, x_dim, x_scale, y_scale):
    """Linear strip patterns"""
    data = np.zeros((num_channels, num_values, z_dim, y_dim, x_dim), dtype=np.int8)
    
    for i in range(3):
        for z in range(z_dim):
            # Vertical strips
            x_start, x_end = max(0, int((38+20*i)*x_scale)), min(x_dim, int((43+20*i)*x_scale))
            for y in range(y_dim):
                for x in range(x_start, x_end):
                    data[0, np.random.randint(6, 11), z, y, x] = 1
            # Horizontal strips  
            y_start, y_end = max(0, int((18+20*i)*y_scale)), min(y_dim, int((23+20*i)*y_scale))
            for y in range(y_start, y_end):
                for x in range(x_dim):
                    data[1, np.random.randint(6, 11), z, y, x] = 1
            # Diagonal strips
            strip_w = int(3 * max(x_scale, y_scale))
            for c in [int(-60*x_scale), 0]:
                for y in range(y_dim):
                    for x in range(x_dim):
                        if abs(y - x - c) <= strip_w:
                            data[2, np.random.randint(6, 11), z, y, x] = 1
            for d in [int(60*y_scale), int(120*y_scale)]:
                for y in range(y_dim):
                    for x in range(x_dim):
                        if abs(y + x - d) <= strip_w:
                            data[3, np.random.randint(6, 11), z, y, x] = 1
    return data


def generate_olympic_texture(num_channels, num_values, z_dim, y_dim, x_dim):
    """Olympic rings pattern"""
    data = np.zeros((num_channels, num_values, z_dim, y_dim, x_dim), dtype=np.int8)
    circles = [(0, 200, 150, 120), (1, 420, 150, 120), (2, 300, 250, 120), (3, 350, 330, 200)]
    stripe_width = 30
    
    for channel, cx, cy, radius in circles:
        inner_r, outer_r = radius - stripe_width, radius
        for z in range(z_dim):
            for y in range(y_dim):
                for x in range(x_dim):
                    dist = np.sqrt((x-cx)**2 + (y-cy)**2)
                    if inner_r <= dist <= outer_r:
                        data[channel, np.random.randint(0, 11), z, y, x] = 1
    return data


def generate_oval_texture(num_channels, num_values, z_dim, y_dim, x_dim):
    """Oval/ellipse patterns"""
    data = np.zeros((num_channels, num_values, z_dim, y_dim, x_dim), dtype=np.int8)
    cx, cy = x_dim // 2, y_dim // 2
    x_stretch = 1.5
    
    for z in range(z_dim):
        for y in range(y_dim):
            for x in range(x_dim):
                dx, dy = (x - cx) / x_stretch, y - cy
                dist = np.sqrt(dx**2 + dy**2)
                if 50 <= dist <= 100:
                    data[0, np.random.randint(6, 11), z, y, x] = 1
                if 80 <= dist <= 110:
                    data[1, np.random.randint(6, 11), z, y, x] = 1
    
    # Clouds for channels 2,3
    z_center = z_dim // 2
    for _ in range(5):
        angle = np.random.uniform(0, 2*np.pi)
        r = np.random.uniform(85, 95)
        cloud_cx = int(np.clip(cx + r * x_stretch * np.cos(angle), 20, x_dim-21))
        cloud_cy = int(np.clip(cy + r * np.sin(angle), 20, y_dim-21))
        for _ in range(100):
            rx, ry = np.random.randint(-20, 21), np.random.randint(-20, 21)
            rz = np.random.randint(-5, 6)
            px, py, pz = cloud_cx+rx, cloud_cy+ry, z_center+rz
            if 0 <= px < x_dim and 0 <= py < y_dim and 0 <= pz < z_dim:
                data[2, np.random.randint(6, 11), pz, py, px] = 1
                data[3, np.random.randint(6, 11), pz, py, px] = 1
    return data


def generate_colonies_texture(num_channels, num_values, z_dim, y_dim, x_dim, x_scale, y_scale):
    """Colony cloud patterns"""
    data = np.zeros((num_channels, num_values, z_dim, y_dim, x_dim), dtype=np.int8)
    max_radius = 50
    
    def add_cloud(channel, cx, cy, z, radius):
        for _ in range(50):
            angle = np.random.uniform(0, 2*np.pi)
            r = np.random.uniform(0, radius)
            px = int(np.clip(cx + r*np.cos(angle), 0, x_dim-1))
            py = int(np.clip(cy + r*np.sin(angle), 0, y_dim-1))
            data[channel, np.random.randint(6, 11), z, py, px] = 1
    
    for z in range(z_dim):
        # Arc pattern for channel 0
        for t in np.linspace(0, 1, 24):
            arc_x = int(t * (x_dim - 1))
            arc_y = int(t * (y_dim - 1) + 0.3 * (y_dim - 1) * np.sin(t * np.pi))
            arc_y = np.clip(arc_y, 0, y_dim-1)
            add_cloud(0, arc_x, arc_y, z, np.random.uniform(10, max_radius))
        
        # Sine pattern for channel 1
        for x in range(0, x_dim, 30):
            y = int(100 + 50 * np.sin(2*np.pi*x/400))
            y = np.clip(y, 0, y_dim-1)
            add_cloud(1, x, y, z, np.random.uniform(10, max_radius))
        
        # Diagonal patterns
        for d in [60, 120]:
            for x in range(0, x_dim, 40):
                y = -x + int(d * y_scale)
                if 0 <= y < y_dim:
                    add_cloud(3, x, y, z, np.random.uniform(10, max_radius))
    return data


def create_groundtruth_fast(texture_type, scale_name, x_scale, y_scale, z_scale, output_dir):
    """Create ground truth with specified texture and scale"""
    print(f"  Creating GT: {texture_type} - {scale_name}...", end=" ", flush=True)
    
    num_channels, num_values = 4, 11
    x_dim = ORIGINAL_X * x_scale
    y_dim = ORIGINAL_Y * y_scale  
    z_dim = ORIGINAL_Z * z_scale
    local_x_scale, local_y_scale = x_dim / 172, y_dim / 87
    
    if texture_type == 'sinusoid':
        data = generate_sinusoid_texture(num_channels, num_values, z_dim, y_dim, x_dim)
    elif texture_type == 'linear':
        data = generate_linear_texture(num_channels, num_values, z_dim, y_dim, x_dim, local_x_scale, local_y_scale)
    elif texture_type == 'olympic':
        data = generate_olympic_texture(num_channels, num_values, z_dim, y_dim, x_dim)
    elif texture_type == 'oval':
        data = generate_oval_texture(num_channels, num_values, z_dim, y_dim, x_dim)
    elif texture_type == 'colonies':
        data = generate_colonies_texture(num_channels, num_values, z_dim, y_dim, x_dim, local_x_scale, local_y_scale)
    else:
        raise ValueError(f"Unknown texture: {texture_type}")
    
    filepath = os.path.join(output_dir, f'groundtruth_{texture_type}_{scale_name}.npy')
    np.save(filepath, data)
    print(f"Done ({data.shape})")
    return data, filepath


# ============================================================================
# OPTIMIZED SUBGRAPH CREATION  
# ============================================================================

def create_subgraphs_fast(data, texture_type, scale_name, output_dir):
    """Fast subgraph creation using vectorized operations"""
    print(f"  Creating subgraphs...", end=" ", flush=True)
    
    num_channels, num_values, z_dim, y_dim, x_dim = data.shape
    z_idx = min(Z_FIXED, z_dim - 1)
    
    # Pre-compute mask
    intensity_matrix = np.zeros((y_dim, x_dim, num_channels), dtype=np.float32)
    channel_mask = np.zeros((y_dim, x_dim, num_channels), dtype=bool)
    
    for ch in range(num_channels):
        ch_data = data[ch, :, z_idx, :, :]
        mask = ch_data.sum(axis=0) > 0
        intensity_matrix[:, :, ch] = np.where(mask, np.argmax(ch_data, axis=0), 0)
        channel_mask[:, :, ch] = mask
    
    channel_counts = channel_mask.sum(axis=2)
    
    # Generate centers
    centers = [(x, y, z_idx) for x in range(0, x_dim, STEP_SIZE) for y in range(0, y_dim, STEP_SIZE)]
    
    all_subgraphs = []
    for cx, cy, cz in centers:
        x_min, x_max = max(0, cx - MAX_RADIUS), min(x_dim, cx + MAX_RADIUS + 1)
        y_min, y_max = max(0, cy - MAX_RADIUS), min(y_dim, cy + MAX_RADIUS + 1)
        
        nodes, positions, active_chs = [], [], []
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                if channel_counts[y, x] > 0:
                    dist = np.sqrt((x-cx)**2 + (y-cy)**2)
                    if dist <= MAX_RADIUS:
                        active = np.where(channel_mask[y, x, :])[0].tolist()
                        nodes.append(intensity_matrix[y, x, active])
                        positions.append((x, y, z_idx))
                        active_chs.append(active)
        
        if len(nodes) < 2:
            continue
            
        max_ch = max(len(ch) for ch in active_chs)
        padded = []
        for i, n in enumerate(nodes):
            p = np.zeros(max_ch, dtype=np.float32)
            p[:len(n)] = n
            padded.append(p)
        
        node_features = np.array(padded, dtype=np.float32)
        pos_array = np.array(positions, dtype=np.int32)
        num_nodes = len(node_features)
        
        # Fast edge creation
        diff = pos_array[:, np.newaxis, :] - pos_array[np.newaxis, :, :]
        dist_matrix = np.sqrt(np.sum(diff**2, axis=2))
        edge_mask = (dist_matrix <= MAX_RADIUS) & (dist_matrix > 0)
        edge_i, edge_j = np.where(edge_mask)
        
        if len(edge_i) == 0:
            continue
        
        edge_weights = dist_matrix[edge_i, edge_j].astype(np.float32)
        
        graph = Data(
            x=torch.tensor(node_features, dtype=torch.float32),
            edge_index=torch.tensor([edge_i, edge_j], dtype=torch.long),
            edge_attr=torch.tensor(edge_weights, dtype=torch.float32),
            center=(cx, cy, cz),
            node_positions=[tuple(p) for p in pos_array]
        )
        all_subgraphs.append(graph)
    
    filepath = os.path.join(output_dir, f'Subgraph_{texture_type}_{scale_name}.pt')
    torch.save(all_subgraphs, filepath)
    print(f"Done ({len(all_subgraphs)} graphs)")
    return all_subgraphs, filepath


# ============================================================================
# MODEL & TRAINING (Compact)
# ============================================================================

def prepare_graph_for_batching(graph, target_channels=4):
    x = graph.x.clone()
    if x.shape[1] < target_channels:
        x = torch.cat([x, torch.zeros(x.shape[0], target_channels - x.shape[1])], dim=1)
    elif x.shape[1] > target_channels:
        x = x[:, :target_channels]
    g = Data(x=x, edge_index=graph.edge_index.clone())
    if hasattr(graph, 'edge_attr') and graph.edge_attr is not None:
        g.edge_attr = graph.edge_attr.clone()
    if hasattr(graph, 'gt_score'):
        g.gt_score = graph.gt_score
    return g


def graph_augment(graph, target_channels=4):
    g = prepare_graph_for_batching(graph, target_channels)
    num_nodes = g.x.shape[0]
    mask_n = int(num_nodes * 0.1)
    if mask_n > 0:
        g.x[torch.randperm(num_nodes)[:mask_n]] = 0.0
    return g


class ContrastiveGAT(nn.Module):
    def __init__(self, in_channels=4, hidden=32, proj_dim=16, heads=4, dropout=0.1, edge_dim=None):
        super().__init__()
        self.edge_dim = edge_dim
        kw = dict(dropout=dropout)
        if edge_dim: kw['edge_dim'] = edge_dim
        
        self.gat1 = GATConv(in_channels, hidden, heads=heads, concat=True, **kw)
        self.gat2 = GATConv(hidden*heads, hidden, heads=heads, concat=True, **kw)
        self.gat3 = GATConv(hidden*heads, hidden, heads=1, concat=False, **kw)
        
        self.norm1 = nn.LayerNorm(hidden*heads)
        self.norm2 = nn.LayerNorm(hidden*heads)
        self.dropout = nn.Dropout(dropout)
        
        self.projection = nn.Sequential(
            nn.Linear(hidden*3, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, proj_dim)
        )
        self.interaction_head = nn.Sequential(
            nn.Linear(hidden*3, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden//2), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden//2, 1)
        )
    
    def forward(self, x, edge_index, edge_attr=None, batch=None):
        ea = edge_attr if self.edge_dim and edge_attr is not None else None
        x = F.elu(self.dropout(self.norm1(self.gat1(x, edge_index, ea))))
        x = F.elu(self.dropout(self.norm2(self.gat2(x, edge_index, ea))))
        x = F.elu(self.gat3(x, edge_index, ea))
        
        if batch is None:
            batch = torch.zeros(x.shape[0], dtype=torch.long, device=x.device)
        
        emb = torch.cat([global_mean_pool(x, batch), global_max_pool(x, batch), global_add_pool(x, batch)], dim=1)
        proj = F.normalize(self.projection(emb), dim=1)
        score = self.interaction_head(emb)
        return proj, score


def contrastive_loss(z1, z2, temp=0.1):
    z1, z2 = F.normalize(z1, dim=1), F.normalize(z2, dim=1)
    sim = torch.matmul(z1, z2.T) / temp
    labels = torch.arange(z1.shape[0], device=z1.device)
    return (F.cross_entropy(sim, labels) + F.cross_entropy(sim.T, labels)) / 2


def train_model_fast(model, graphs, device, epochs=1, batch_size=32, lr=0.01):
    """Fast training with minimal overhead"""
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    target_ch = max(g.x.shape[1] for g in graphs) if graphs else 4
    
    print(f"  Training ({len(graphs)} graphs)...", end=" ", flush=True)
    
    for epoch in range(epochs):
        random.shuffle(graphs)
        for i in range(0, len(graphs), batch_size):
            batch_g = graphs[i:i+batch_size]
            aug1 = [graph_augment(g, target_ch) for g in batch_g]
            aug2 = [graph_augment(g, target_ch) for g in batch_g]
            
            for g in aug1 + aug2:
                g.x, g.edge_index = g.x.to(device), g.edge_index.to(device)
                if hasattr(g, 'edge_attr') and g.edge_attr is not None:
                    g.edge_attr = g.edge_attr.to(device)
            
            try:
                b1, b2 = Batch.from_data_list(aug1), Batch.from_data_list(aug2)
            except:
                continue
            
            z1, p1 = model(b1.x, b1.edge_index, getattr(b1, 'edge_attr', None), b1.batch)
            z2, _ = model(b2.x, b2.edge_index, getattr(b2, 'edge_attr', None), b2.batch)
            
            loss = contrastive_loss(z1, z2)
            if hasattr(b1, 'gt_score'):
                gt = b1.gt_score.to(device).float()
                if gt.std() > 0:
                    gt = (gt - gt.mean()) / (gt.std() + 1e-8)
                    pred = (p1.view(-1) - p1.mean()) / (p1.std() + 1e-8)
                    loss = loss + 0.5 * F.mse_loss(pred, gt)
            
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            del z1, z2, b1, b2, aug1, aug2
    
    print("Done")
    return model


# ============================================================================
# COORDINATE EXTRACTION & ACCURACY
# ============================================================================

def attach_gt_scores_fast(data, graphs):
    """Vectorized GT score computation"""
    pattern_mask = (data > 0).any(axis=1).any(axis=0)  # (Z, Y, X)
    z_dim, y_dim, x_dim = pattern_mask.shape
    
    for g in graphs:
        cx, cy, cz = int(g.center[0]), int(g.center[1]), int(g.center[2])
        cz = np.clip(cz, 0, z_dim-1)
        
        x_min, x_max = max(0, cx-MAX_RADIUS), min(x_dim, cx+MAX_RADIUS+1)
        y_min, y_max = max(0, cy-MAX_RADIUS), min(y_dim, cy+MAX_RADIUS+1)
        
        # Vectorized scoring
        yy, xx = np.meshgrid(np.arange(y_min, y_max), np.arange(x_min, x_max), indexing='ij')
        dist_sq = (xx - cx)**2 + (yy - cy)**2
        mask = (dist_sq <= MAX_RADIUS**2) & pattern_mask[cz, y_min:y_max, x_min:x_max]
        g.gt_score = float(mask.sum())
    
    return graphs


def find_top_positions_fast(model, graphs, device, top_k=100):
    """Fast model inference"""
    model.eval()
    target_ch = max(g.x.shape[1] for g in graphs) if graphs else 4
    scores = []
    
    with torch.no_grad():
        for g in graphs:
            x = g.x.clone()
            if x.shape[1] < target_ch:
                x = torch.cat([x, torch.zeros(x.shape[0], target_ch - x.shape[1])], dim=1)
            elif x.shape[1] > target_ch:
                x = x[:, :target_ch]
            
            x = x.to(device)
            edge_index = g.edge_index.to(device)
            ea = g.edge_attr.to(device) if hasattr(g, 'edge_attr') and g.edge_attr is not None else None
            
            _, score = model(x, edge_index, ea, None)
            scores.append({'x': g.center[0], 'y': g.center[1], 'z': g.center[2], 'score': score.item()})
    
    scores.sort(key=lambda s: s['score'], reverse=True)
    return scores[:top_k]


def extract_gt_coords_fast(data, graphs, top_k=100):
    """Fast GT coordinate extraction"""
    pattern_mask = (data > 0).any(axis=1).any(axis=0)
    z_dim, y_dim, x_dim = pattern_mask.shape
    scores = []
    
    for g in graphs:
        cx, cy, cz = int(g.center[0]), int(g.center[1]), int(g.center[2])
        cz = np.clip(cz, 0, z_dim-1)
        
        x_min, x_max = max(0, cx-MAX_RADIUS), min(x_dim, cx+MAX_RADIUS+1)
        y_min, y_max = max(0, cy-MAX_RADIUS), min(y_dim, cy+MAX_RADIUS+1)
        
        yy, xx = np.meshgrid(np.arange(y_min, y_max), np.arange(x_min, x_max), indexing='ij')
        dist_sq = (xx - cx)**2 + (yy - cy)**2
        mask = (dist_sq <= MAX_RADIUS**2) & pattern_mask[cz, y_min:y_max, x_min:x_max]
        scores.append({'x': cx, 'y': cy, 'z': cz, 'score': int(mask.sum())})
    
    scores.sort(key=lambda s: s['score'], reverse=True)
    return scores[:top_k]


def compute_accuracy_fast(model_coords, gt_coords, tol=MAX_RADIUS):
    """Fast accuracy computation"""
    if not model_coords or not gt_coords:
        return {'matches': 0, 'precision': 0, 'recall': 0, 'f1_score': 0, 'accuracy_iou': 0, 
                'model_count': len(model_coords), 'gt_count': len(gt_coords)}
    
    model_pts = np.array([[c['x'], c['y'], c['z']] for c in model_coords])
    gt_pts = np.array([[c['x'], c['y'], c['z']] for c in gt_coords])
    
    # Vectorized distance matrix
    diff = model_pts[:, np.newaxis, :] - gt_pts[np.newaxis, :, :]
    dist = np.sqrt(np.sum(diff**2, axis=2))
    
    # Greedy matching
    matches = 0
    matched_gt = set()
    for i in range(len(model_pts)):
        for j in np.argsort(dist[i]):
            if j not in matched_gt and dist[i, j] <= tol:
                matches += 1
                matched_gt.add(j)
                break
    
    m_count, g_count = len(model_pts), len(gt_pts)
    precision = matches / m_count if m_count else 0
    recall = matches / g_count if g_count else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    iou = matches / (m_count + g_count - matches) if (m_count + g_count - matches) else 0
    
    return {'matches': matches, 'precision': precision, 'recall': recall, 
            'f1_score': f1, 'accuracy_iou': iou, 'model_count': m_count, 'gt_count': g_count}


# ============================================================================
# MAIN EXECUTION - TABLE PER TEXTURE + FINAL AVERAGE
# ============================================================================

def print_texture_table(texture_name, results):
    """Print formatted table for one texture"""
    print(f"\n{'='*100}")
    print(f"RESULTS TABLE: {texture_name.upper()}")
    print(f"{'='*100}")
    print(f"{'Scale Name':>12} {'Scale':>12} {'GT File':>35} {'Matches':>8} {'Model Pts':>10} {'GT Pts':>8} {'Precision':>10} {'Recall':>8} {'F1 Score':>9} {'Accuracy':>9}")
    print("-"*100)
    for r in results:
        print(f"{r['Scale Name']:>12} {r['Scale']:>12} {r['GT File']:>35} {r['Matches']:>8} {r['Model Points']:>10} {r['GT Points']:>8} {r['Precision']:>10.4f} {r['Recall']:>8.4f} {r['F1 Score']:>9.4f} {r['Accuracy']:>9.4f}")
    print("="*100)


def run_texture_experiment(texture_type, device):
    """Run all scales for one texture and return results"""
    print(f"\n{'*'*80}")
    print(f"TEXTURE: {texture_type.upper()}")
    print(f"{'*'*80}")
    
    texture_dir = os.path.join(BASE_DIR, texture_type)
    os.makedirs(texture_dir, exist_ok=True)
    
    results = []
    
    for scale_name, x_s, y_s, z_s in SCALES:
        print(f"\n[{scale_name}] Processing...")
        
        try:
            # 1. Create ground truth
            data, gt_path = create_groundtruth_fast(texture_type, scale_name, x_s, y_s, z_s, texture_dir)
            
            # 2. Create subgraphs
            graphs, _ = create_subgraphs_fast(data, texture_type, scale_name, texture_dir)
            
            # 3. Filter graphs
            filtered = [g for g in graphs if g.x.shape[0] >= 50]
            print(f"  Filtered: {len(filtered)} graphs")
            
            if not filtered:
                print(f"  SKIPPED - no graphs")
                continue
            
            # 4. Attach GT scores
            filtered = attach_gt_scores_fast(data, filtered)
            
            # 5. Train model
            in_ch = max(g.x.shape[1] for g in filtered)
            edge_dim = 1 if any(hasattr(g, 'edge_attr') for g in filtered) else None
            model = ContrastiveGAT(in_ch, 32, 16, 4, 0.1, edge_dim).to(device)
            
            train_graphs = filtered[::2] if len(filtered) > 10000 else filtered
            model = train_model_fast(model, train_graphs, device, epochs=1, batch_size=32, lr=0.01)
            
            # 6. Extract model predictions
            print(f"  Extracting positions...", end=" ", flush=True)
            model_coords = find_top_positions_fast(model, filtered, device, TOP_K)
            print("Done")
            
            # 7. Extract GT coordinates
            gt_coords = extract_gt_coords_fast(data, filtered, TOP_K)
            
            # 8. Compute accuracy
            acc = compute_accuracy_fast(model_coords, gt_coords, MAX_RADIUS)
            
            result = {
                'Scale Name': scale_name,
                'Scale': f'{x_s}x,{y_s}x,{z_s}x',
                'GT File': os.path.basename(gt_path),
                'Matches': acc['matches'],
                'Model Points': acc['model_count'],
                'GT Points': acc['gt_count'],
                'Precision': acc['precision'],
                'Recall': acc['recall'],
                'F1 Score': acc['f1_score'],
                'Accuracy': acc['accuracy_iou']
            }
            results.append(result)
            
            print(f"  Result: Matches={acc['matches']}, F1={acc['f1_score']:.4f}, Acc={acc['accuracy_iou']:.4f}")
            
            # Cleanup
            del data, graphs, filtered, model
            if device.type == 'cuda':
                torch.cuda.empty_cache()
                
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Print texture table
    if results:
        print_texture_table(texture_type, results)
        
        # Save to CSV
        df = pd.DataFrame(results)
        csv_path = os.path.join(texture_dir, f'results_{texture_type}.csv')
        df.to_csv(csv_path, index=False)
        print(f"\n✓ Saved to: {csv_path}")
    
    return results


# ============================================================================
# RUN ALL TEXTURES
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("MULTI-TEXTURE SCALE EXPERIMENT - OPTIMIZED VERSION")
    print("="*80)
    print(f"\nTextures: {TEXTURES}")
    print(f"Scales: {len(SCALES)}")
    print(f"Total: {len(TEXTURES)} × {len(SCALES)} = {len(TEXTURES)*len(SCALES)} experiments")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}\n")
    
    all_results = {}
    
    # Run each texture
    for texture in TEXTURES:
        all_results[texture] = run_texture_experiment(texture, device)
    
    # ============================================================================
    # FINAL AVERAGE TABLE
    # ============================================================================
    print(f"\n\n{'#'*100}")
    print("FINAL AVERAGE TABLE (All Textures × All Scales)")
    print(f"{'#'*100}\n")
    
    # Collect all results
    combined = []
    for tex, res_list in all_results.items():
        for r in res_list:
            r_copy = r.copy()
            r_copy['Texture'] = tex
            combined.append(r_copy)
    
    if combined:
        # Average by texture
        print(f"\n{'='*80}")
        print("AVERAGE BY TEXTURE (across all scales)")
        print(f"{'='*80}")
        print(f"{'Texture':>12} {'Experiments':>12} {'Avg Matches':>12} {'Avg Precision':>14} {'Avg Recall':>12} {'Avg F1':>10} {'Avg Accuracy':>13}")
        print("-"*80)
        
        for tex in TEXTURES:
            tex_data = [r for r in combined if r['Texture'] == tex]
            if tex_data:
                avg_matches = np.mean([r['Matches'] for r in tex_data])
                avg_prec = np.mean([r['Precision'] for r in tex_data])
                avg_rec = np.mean([r['Recall'] for r in tex_data])
                avg_f1 = np.mean([r['F1 Score'] for r in tex_data])
                avg_acc = np.mean([r['Accuracy'] for r in tex_data])
                print(f"{tex:>12} {len(tex_data):>12} {avg_matches:>12.2f} {avg_prec:>14.4f} {avg_rec:>12.4f} {avg_f1:>10.4f} {avg_acc:>13.4f}")
        
        print("="*80)
        
        # Average by scale
        print(f"\n{'='*80}")
        print("AVERAGE BY SCALE (across all textures)")
        print(f"{'='*80}")
        print(f"{'Scale':>12} {'Scale Config':>14} {'Experiments':>12} {'Avg Matches':>12} {'Avg Precision':>14} {'Avg Recall':>12} {'Avg F1':>10} {'Avg Accuracy':>13}")
        print("-"*80)
        
        for scale_name, x_s, y_s, z_s in SCALES:
            scale_data = [r for r in combined if r['Scale Name'] == scale_name]
            if scale_data:
                avg_matches = np.mean([r['Matches'] for r in scale_data])
                avg_prec = np.mean([r['Precision'] for r in scale_data])
                avg_rec = np.mean([r['Recall'] for r in scale_data])
                avg_f1 = np.mean([r['F1 Score'] for r in scale_data])
                avg_acc = np.mean([r['Accuracy'] for r in scale_data])
                print(f"{scale_name:>12} {f'{x_s}x,{y_s}y,{z_s}z':>14} {len(scale_data):>12} {avg_matches:>12.2f} {avg_prec:>14.4f} {avg_rec:>12.4f} {avg_f1:>10.4f} {avg_acc:>13.4f}")
        
        print("="*80)
        
        # Overall average
        print(f"\n{'='*80}")
        print("OVERALL AVERAGE (all experiments)")
        print(f"{'='*80}")
        overall_matches = np.mean([r['Matches'] for r in combined])
        overall_prec = np.mean([r['Precision'] for r in combined])
        overall_rec = np.mean([r['Recall'] for r in combined])
        overall_f1 = np.mean([r['F1 Score'] for r in combined])
        overall_acc = np.mean([r['Accuracy'] for r in combined])
        
        print(f"  Total Experiments: {len(combined)}")
        print(f"  Overall Avg Matches: {overall_matches:.2f}")
        print(f"  Overall Avg Precision: {overall_prec:.4f}")
        print(f"  Overall Avg Recall: {overall_rec:.4f}")
        print(f"  Overall Avg F1 Score: {overall_f1:.4f}")
        print(f"  Overall Avg Accuracy: {overall_acc:.4f}")
        print("="*80)
        
        # Save combined results
        combined_df = pd.DataFrame(combined)
        combined_path = os.path.join(BASE_DIR, 'all_textures_all_scales_results.csv')
        combined_df.to_csv(combined_path, index=False)
        print(f"\n✓ All results saved to: {combined_path}")
        
        # Save average tables
        texture_avg = []
        for tex in TEXTURES:
            tex_data = [r for r in combined if r['Texture'] == tex]
            if tex_data:
                texture_avg.append({
                    'Texture': tex,
                    'Experiments': len(tex_data),
                    'Avg Matches': np.mean([r['Matches'] for r in tex_data]),
                    'Avg Precision': np.mean([r['Precision'] for r in tex_data]),
                    'Avg Recall': np.mean([r['Recall'] for r in tex_data]),
                    'Avg F1 Score': np.mean([r['F1 Score'] for r in tex_data]),
                    'Avg Accuracy': np.mean([r['Accuracy'] for r in tex_data])
                })
        pd.DataFrame(texture_avg).to_csv(os.path.join(BASE_DIR, 'average_by_texture.csv'), index=False)
        
        scale_avg = []
        for scale_name, x_s, y_s, z_s in SCALES:
            scale_data = [r for r in combined if r['Scale Name'] == scale_name]
            if scale_data:
                scale_avg.append({
                    'Scale': scale_name,
                    'Scale Config': f'{x_s}x,{y_s}y,{z_s}z',
                    'Experiments': len(scale_data),
                    'Avg Matches': np.mean([r['Matches'] for r in scale_data]),
                    'Avg Precision': np.mean([r['Precision'] for r in scale_data]),
                    'Avg Recall': np.mean([r['Recall'] for r in scale_data]),
                    'Avg F1 Score': np.mean([r['F1 Score'] for r in scale_data]),
                    'Avg Accuracy': np.mean([r['Accuracy'] for r in scale_data])
                })
        pd.DataFrame(scale_avg).to_csv(os.path.join(BASE_DIR, 'average_by_scale.csv'), index=False)
        
        print(f"✓ Average tables saved")
    
    print(f"\n{'='*80}")
    print("EXPERIMENT COMPLETE!")
    print(f"{'='*80}\n")
