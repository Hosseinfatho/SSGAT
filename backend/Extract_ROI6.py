import torch
import torch.nn as nn
from torch_geometric.data import Data
import numpy as np
import json
import os
from pathlib import Path
import logging
from train_gat4 import MarkerGAT, INTERACTIONS, MARKERS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_graphs(marker):
    """Load ROI graphs for a specific marker from main graphs"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try to load ROI graphs first
    roi_graph_file = os.path.join(script_dir, "output", f"roi_graphs_{marker}.pt")
    if os.path.exists(roi_graph_file):
        try:
            graphs = torch.load(roi_graph_file)
            logger.info(f"Loaded {len(graphs)} ROI graphs for {marker}")
            return graphs
        except Exception as e:
            logger.error(f"Error loading ROI graphs for {marker}: {str(e)}")
    
    # Fallback: extract subgraphs from main graph
    main_graph_file = os.path.join(script_dir, "output", "main_marker_graphs", f"{marker}_main_graph.pt")
    if not os.path.exists(main_graph_file):
        logger.error(f"Main graph file not found: {main_graph_file}")
        return []
    
    try:
        main_graph = torch.load(main_graph_file)
        logger.info(f"Loaded main graph for {marker}: {main_graph.metadata['num_nodes']} nodes, {main_graph.metadata['num_edges']} edges")
        
        # Extract subgraphs as ROIs
        subgraphs = []
        if 'subgraphs' in main_graph.metadata:
            for i, subgraph_info in enumerate(main_graph.metadata['subgraphs']):
                start_node = subgraph_info['start_node']
                end_node = subgraph_info['end_node']
                
                # Extract node features for this subgraph
                subgraph_x = main_graph.x[start_node:end_node + 1]
                
                # Extract edges that are within this subgraph
                edge_mask = ((main_graph.edge_index[0] >= start_node) & 
                            (main_graph.edge_index[0] <= end_node) &
                            (main_graph.edge_index[1] >= start_node) & 
                            (main_graph.edge_index[1] <= end_node))
                
                subgraph_edge_index = main_graph.edge_index[:, edge_mask]
                subgraph_edge_attr = main_graph.edge_attr[edge_mask] if hasattr(main_graph, 'edge_attr') else None
                
                # Adjust edge indices to be local to this subgraph
                subgraph_edge_index = subgraph_edge_index - start_node
                
                # Create subgraph Data object
                from torch_geometric.data import Data
                subgraph = Data(
                    x=subgraph_x,
                    edge_index=subgraph_edge_index,
                    edge_attr=subgraph_edge_attr,
                    roi_id=i,
                    center=subgraph_info.get('center', torch.tensor([0.0, 0.0])),
                    pos=subgraph_info.get('center', torch.tensor([0.0, 0.0]))  # Use center as position
                )
                
                subgraphs.append(subgraph)
            
            logger.info(f"Extracted {len(subgraphs)} subgraphs as ROIs for {marker}")
            return subgraphs
        else:
            logger.warning(f"No subgraphs found in main graph for {marker}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading main graph for {marker}: {str(e)}")
        return []

def compute_intensity_score(graph, interaction_name):
    """Compute intensity score based on marker intensities for the interaction"""
    try:
        # Get marker indices for this interaction
        interaction_markers = INTERACTIONS[interaction_name]
        marker_indices = []
        
        for marker in interaction_markers:
            if marker in MARKERS:
                marker_idx = MARKERS.index(marker)
                if marker_idx < graph.x.shape[1]:  # Ensure index is within bounds
                    marker_indices.append(marker_idx)
        
        if not marker_indices:
            logger.warning(f"No valid marker indices found for interaction {interaction_name}")
            return 0.0
        
        # Calculate mean intensity for interaction markers
        marker_intensities = graph.x[:, marker_indices]
        intensity_score = marker_intensities.mean().item()
        
        return intensity_score
        
    except Exception as e:
        logger.error(f"Error computing intensity score: {str(e)}")
        return 0.0

def compute_attention_score(model, graph, device):
    """Compute attention score based on GAT attention weights or MLP output"""
    try:
        model.eval()
        with torch.no_grad():
            # Move graph to device
            graph = graph.to(device)
            
            # Check if model is MLP (CD11c) or GAT
            if hasattr(model, 'fc1'):  # MLP model
                # For MLP, use the output as attention score
                x = graph.x
                out = model(x)
                # Use mean of output as attention score
                attention_score = out.mean().item()
            else:  # GAT model
                # Get attention weights from first GAT layer
                x = graph.x
                edge_index = graph.edge_index
                edge_attr = graph.edge_attr if hasattr(graph, 'edge_attr') else None
                
                # Forward pass through first GAT layer with attention weights
                if edge_attr is not None:
                    out, (edge_index_attn, attn_weights) = model.gat1(
                        x, edge_index, edge_attr, return_attention_weights=True
                    )
                else:
                    out, (edge_index_attn, attn_weights) = model.gat1(
                        x, edge_index, return_attention_weights=True
                    )
                
                # attn_weights shape: [num_edges, num_heads]
                # Calculate mean attention across all heads and edges
                if attn_weights.numel() > 0:
                    attention_score = attn_weights.mean().item()
                else:
                    attention_score = 0.0
            
            return attention_score
            
    except Exception as e:
        logger.error(f"Error computing attention score: {str(e)}")
        return 0.0

def compute_roi_score(model, graph, interaction_name, device, 
                     intensity_weight=0.5, attention_weight=0.5):
    """Compute combined ROI score based on intensity and attention"""
    try:
        # Compute individual scores
        intensity_score = compute_intensity_score(graph, interaction_name)
        attention_score = compute_attention_score(model, graph, device)
        
        # Combine scores with weights
        combined_score = (intensity_weight * intensity_score + 
                         attention_weight * attention_score)
        
        return {
            'combined_score': combined_score,
            'intensity_score': intensity_score,
            'attention_score': attention_score
        }
        
    except Exception as e:
        logger.error(f"Error computing ROI score: {str(e)}")
        return {
            'combined_score': 0.0,
            'intensity_score': 0.0,
            'attention_score': 0.0
        }

def extract_roi_positions(graph):
    """Extract position information from ROI graph"""
    try:
        # First try to get position from graph attributes
        if hasattr(graph, 'center'):
            center = graph.center
            # Convert to tensor if it's a list
            if isinstance(center, list):
                center = torch.tensor(center, dtype=torch.float32)
            pos = center
        elif hasattr(graph, 'pos'):
            pos = graph.pos
        elif hasattr(graph, 'metadata') and 'center' in graph.metadata:
            center = graph.metadata['center']
            if isinstance(center, list):
                center = torch.tensor(center, dtype=torch.float32)
            pos = center
        else:
            # Try to get position from node features if available
            pos = torch.tensor([0.0, 0.0])  # Default position
        
        # Handle different tensor shapes
        if len(pos.shape) == 1:
            x, y = pos[0].item(), pos[1].item()
        else:
            x, y = pos[0, 0].item(), pos[0, 1].item()
        
        # Add z coordinate if available
        z = None
        if len(pos.shape) == 1 and pos.size(0) > 2:
            z = pos[2].item()
        elif len(pos.shape) > 1 and pos.size(1) > 2:
            z = pos[0, 2].item()
        
        return {
            'x': float(x),
            'y': float(y),
            'z': float(z) if z is not None else None
        }
            
    except Exception as e:
        logger.error(f"Error extracting ROI position: {str(e)}")
        return {'x': 0.0, 'y': 0.0, 'z': None}

def process_interaction_rois(interaction_name, device):
    """Process all ROIs for a specific interaction and compute scores"""
    logger.info(f"\nProcessing interaction: {interaction_name}")
    
    # Get required markers for this interaction
    required_markers = INTERACTIONS[interaction_name]
    logger.info(f"Required markers: {required_markers}")
    
    # Load all graphs for required markers
    all_graphs = []
    for marker in required_markers:
        marker_graphs = load_graphs(marker)
        if marker_graphs:
            all_graphs.extend(marker_graphs)
    
    if not all_graphs:
        logger.error(f"No graphs found for {interaction_name}")
        return []
    
    logger.info(f"Total graphs loaded: {len(all_graphs)}")
    
    # Load appropriate model for the first marker
    script_dir = os.path.dirname(os.path.abspath(__file__))
    checkpoint_path = os.path.join(script_dir, "output", f"best_model_{required_markers[0]}.pt")
    
    if not os.path.exists(checkpoint_path):
        logger.error(f"Model checkpoint not found: {checkpoint_path}")
        return []
    
    # Load checkpoint to check model type
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Determine model type based on checkpoint structure
    if 'model_type' in checkpoint and checkpoint['model_type'] == 'MLP':
        # CD11c uses MLP model
        from train_gat4 import CD11cMLP
        model = CD11cMLP(in_channels=len(MARKERS)).to(device)
        logger.info(f"Loading MLP model for {required_markers[0]}")
    else:
        # Other markers use GAT model
        model = MarkerGAT(
            in_channels=len(MARKERS),
            hidden_channels=64,
            out_channels=32
        ).to(device)
        logger.info(f"Loading GAT model for {required_markers[0]}")
    
    # Load model weights
    try:
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded model from {checkpoint_path}")
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return []
    
    # Compute scores for all ROIs
    roi_scores = []
    for i, graph in enumerate(all_graphs):
        logger.info(f"Processing ROI {i+1}/{len(all_graphs)}")
        
        # Compute scores
        scores = compute_roi_score(model, graph, interaction_name, device)
        
        # Extract position
        position = extract_roi_positions(graph)
        
        # Create ROI data
        roi_data = {
            'roi_id': i,
            'interaction': interaction_name,
            'position': position,
            'scores': scores,
            'num_nodes': graph.x.shape[0] if hasattr(graph, 'x') else 0,
            'num_edges': graph.edge_index.shape[1] if hasattr(graph, 'edge_index') else 0
        }
        
        roi_scores.append(roi_data)
    
    # Sort ROIs by combined score in descending order
    roi_scores_sorted = sorted(roi_scores, 
                              key=lambda x: x['scores']['combined_score'], 
                              reverse=True)
    
    logger.info(f"\nTop 5 ROIs for {interaction_name}:")
    for i, roi in enumerate(roi_scores_sorted[:5]):
        logger.info(f"ROI {i+1}: Combined Score = {roi['scores']['combined_score']:.4f}, "
                   f"Intensity = {roi['scores']['intensity_score']:.4f}, "
                   f"Attention = {roi['scores']['attention_score']:.4f}")
    
    return roi_scores_sorted

def save_interaction_results(interaction_name, roi_scores, output_dir):
    """Save results for a specific interaction"""
    if not roi_scores:
        logger.error(f"No ROI scores to save for {interaction_name}")
        return
    
    # Prepare data for JSON serialization
    serializable_rois = []
    for roi in roi_scores:
        serializable_roi = {
            'roi_id': roi['roi_id'],
            'interaction': roi['interaction'],
            'position': roi['position'],
            'scores': {
                'combined_score': float(roi['scores']['combined_score']),
                'intensity_score': float(roi['scores']['intensity_score']),
                'attention_score': float(roi['scores']['attention_score'])
            },
            'num_nodes': roi['num_nodes'],
            'num_edges': roi['num_edges']
        }
        serializable_rois.append(serializable_roi)
    
    # Calculate statistics
    combined_scores = [roi['scores']['combined_score'] for roi in roi_scores]
    intensity_scores = [roi['scores']['intensity_score'] for roi in roi_scores]
    attention_scores = [roi['scores']['attention_score'] for roi in roi_scores]
    
    stats = {
        'total_rois': len(roi_scores),
        'score_ranges': {
            'combined': {'min': float(min(combined_scores)), 'max': float(max(combined_scores))},
            'intensity': {'min': float(min(intensity_scores)), 'max': float(max(intensity_scores))},
            'attention': {'min': float(min(attention_scores)), 'max': float(max(attention_scores))}
        },
        'score_means': {
            'combined': float(np.mean(combined_scores)),
            'intensity': float(np.mean(intensity_scores)),
            'attention': float(np.mean(attention_scores))
        }
    }
    
    # Save all ROIs
    output_file = os.path.join(output_dir, f"all_roi_scores_{interaction_name}.json")
    with open(output_file, 'w') as f:
        json.dump({
            'interaction_name': interaction_name,
            'rois': serializable_rois,
            'statistics': stats,
            'method': 'intensity_attention_combined'
        }, f, indent=2)
    
    logger.info(f"Saved {len(serializable_rois)} ROIs for {interaction_name} to {output_file}")
    
    # Save top ROIs (top 7)
    top_count = min(7, len(serializable_rois))
    top_rois = serializable_rois[:top_count]
    
    top_output_file = os.path.join(output_dir, f"top5_roi_scores_{interaction_name}.json")
    with open(top_output_file, 'w') as f:
        json.dump({
            'interaction_name': interaction_name,
            'top_rois': top_rois,
            'total_rois': len(serializable_rois),
            'top_count': top_count,
            'statistics': stats,
            'method': 'intensity_attention_combined'
        }, f, indent=2)
    
    logger.info(f"Saved top {top_count} ROIs for {interaction_name} to {top_output_file}")

def compute_intensity_score_cd11c(graph):
    """Compute intensity score for CD11c: num_nodes * mean_intensity"""
    try:
        # Get CD11c marker index
        cd11c_idx = MARKERS.index("CD11c")
        if cd11c_idx >= graph.x.shape[1]:
            return 0.0
        
        # Get CD11c intensities
        cd11c_intensities = graph.x[:, cd11c_idx]
        mean_intensity = cd11c_intensities.mean().item()
        num_nodes = graph.x.shape[0]
        
        # Calculate score: num_nodes * mean_intensity
        intensity_score = num_nodes * mean_intensity
        
        return intensity_score
        
    except Exception as e:
        logger.error(f"Error computing CD11c intensity score: {str(e)}")
        return 0.0

def process_cd11c_rois(device):
    """Process CD11c ROIs as part of Inflammatory zone interaction"""
    logger.info(f"\nProcessing CD11c as part of Inflammatory zone interaction")
    
    # Load CD11c graphs
    cd11c_graphs = load_graphs("CD11c")
    
    if not cd11c_graphs:
        logger.error(f"No CD11c graphs found")
        return []
    
    logger.info(f"Total CD11c graphs loaded: {len(cd11c_graphs)}")
    
    # Compute scores for all ROIs using Inflammatory zone interaction
    roi_scores = []
    for i, graph in enumerate(cd11c_graphs):
        logger.info(f"Processing CD11c ROI {i+1}/{len(cd11c_graphs)}")
        
        # Compute intensity score for Inflammatory zone interaction (CD11b + CD11c)
        intensity_score = compute_intensity_score(graph, "Inflammatory zone")
        
        # Extract position
        position = extract_roi_positions(graph)
        
        # Create ROI data
        roi_data = {
            'roi_id': i,
            'interaction': 'Inflammatory zone',  # Updated interaction name
            'position': position,
            'scores': {
                'intensity_score': intensity_score,
                'num_nodes': graph.x.shape[0] if hasattr(graph, 'x') else 0,
                'mean_intensity': graph.x[:, MARKERS.index("CD11c")].mean().item() if hasattr(graph, 'x') else 0
            },
            'num_nodes': graph.x.shape[0] if hasattr(graph, 'x') else 0,
            'num_edges': graph.edge_index.shape[1] if hasattr(graph, 'edge_index') else 0
        }
        
        roi_scores.append(roi_data)
    
    # Sort ROIs by intensity score in descending order
    roi_scores_sorted = sorted(roi_scores, 
                              key=lambda x: x['scores']['intensity_score'], 
                              reverse=True)
    
    # Take only top 7
    top_5_rois = roi_scores_sorted[:7]
    
    logger.info(f"\nTop 5 CD11c ROIs (Inflammatory zone):")
    for i, roi in enumerate(top_5_rois):
        logger.info(f"ROI {i+1}: Intensity Score = {roi['scores']['intensity_score']:.4f}, "
                   f"Num Nodes = {roi['scores']['num_nodes']}, "
                   f"Mean Intensity = {roi['scores']['mean_intensity']:.4f}")
    
    return top_5_rois

def save_cd11c_results(roi_scores, output_dir):
    """Save CD11c results as part of Inflammatory zone"""
    if not roi_scores:
        logger.error(f"No CD11c ROI scores to save")
        return
    
    # Prepare data for JSON serialization
    serializable_rois = []
    for roi in roi_scores:
        serializable_roi = {
            'roi_id': roi['roi_id'],
            'interaction': roi['interaction'],
            'position': roi['position'],
            'scores': {
                'intensity_score': float(roi['scores']['intensity_score']),
                'num_nodes': roi['scores']['num_nodes'],
                'mean_intensity': float(roi['scores']['mean_intensity'])
            },
            'num_nodes': roi['num_nodes'],
            'num_edges': roi['num_edges']
        }
        serializable_rois.append(serializable_roi)
    
    # Calculate statistics
    intensity_scores = [roi['scores']['intensity_score'] for roi in roi_scores]
    
    stats = {
        'total_rois': len(roi_scores),
        'score_ranges': {
            'intensity': {'min': float(min(intensity_scores)), 'max': float(max(intensity_scores))}
        },
        'score_means': {
            'intensity': float(np.mean(intensity_scores))
        }
    }
    
    # Save top 5 ROIs
    output_file = os.path.join(output_dir, f"top_5_cd11c_rois.json")
    with open(output_file, 'w') as f:
        json.dump({
            'interaction_name': 'Inflammatory zone',  # Updated interaction name
            'top_5_rois': serializable_rois,
            'total_rois': len(roi_scores),
            'statistics': stats,
            'method': 'cd11c_inflammatory_zone_intensity'
        }, f, indent=2)
    
    logger.info(f"Saved top 5 CD11c ROIs to {output_file}")

def main():
    """Main function to extract and score ROIs using intensity and attention"""
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Create output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each interaction
    for interaction_name in INTERACTIONS.keys():
        try:
            # Process ROIs for this interaction
            roi_scores = process_interaction_rois(interaction_name, device)
            
            # Save results
            if roi_scores:
                save_interaction_results(interaction_name, roi_scores, output_dir)
            else:
                logger.warning(f"No ROI scores computed for {interaction_name}")
                
        except Exception as e:
            logger.error(f"Error processing interaction {interaction_name}: {str(e)}")
            continue
        
    # Process CD11c ROIs
    try:
        # Process CD11c ROIs
        cd11c_rois = process_cd11c_rois(device)
        
        # Save CD11c results
        if cd11c_rois:
            save_cd11c_results(cd11c_rois, output_dir)
        else:
            logger.warning(f"No CD11c ROI scores computed")
        
    except Exception as e:
        logger.error(f"Error processing CD11c ROIs: {str(e)}")
        
    logger.info("\nROI extraction and scoring completed!")

if __name__ == "__main__":
    main() 