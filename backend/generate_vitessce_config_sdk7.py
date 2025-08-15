import pandas as pd
import json
from pathlib import Path
import logging
# import numpy as np
import glob
import re

# import yaml

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_roi_data_by_interaction(output_dir):
    """Load ROI data grouped by interaction"""
    roi_files = glob.glob(str(output_dir / "top5_roi_*.json"))
    interaction_data = {}
    
    for file_path in roi_files:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Check if data has the old format with interaction_name and top_rois
            if 'interaction_name' in data and 'top_rois' in data:
                interaction_name = data['interaction_name']
                rois = data['top_rois']
            else:
                # Extract interaction name from filename
                filename = Path(file_path).stem
                interaction_name = filename.replace('top5_roi_', '')
                rois = data
            
            interaction_data[interaction_name] = []
            
            # Process each ROI in the data
            if isinstance(rois, list):
                # Old format: list of ROIs
                for roi in rois:
                    if isinstance(roi, dict) and 'position' in roi:
                        roi_info = {
                            'x': roi['position']['x'],
                            'y': roi['position']['y'],
                            'z': roi['position'].get('z', 0),
                            'score': roi['scores']['combined_score'],
                            'roi_id': roi['roi_id'],
                            'intensity_score': roi['scores']['intensity_score'],
                            'attention_score': roi['scores']['attention_score'],
                            'num_nodes': roi['num_nodes'],
                            'num_edges': roi['num_edges']
                        }
                        interaction_data[interaction_name].append(roi_info)
            else:
                # New format: dictionary of ROIs
                for roi_name, roi_data in rois.items():
                    if isinstance(roi_data, dict) and 'position' in roi_data:
                        roi_info = {
                            'x': roi_data['position']['x'],
                            'y': roi_data['position']['y'],
                            'z': roi_data['position'].get('z', 0),
                            'score': roi_data.get('score', 0),
                            'roi_id': roi_data.get('roi_id', 0),
                            'intensity_score': roi_data.get('intensity_score', 0),
                            'attention_score': roi_data.get('attention_score', 0),
                            'num_nodes': roi_data.get('num_nodes', 0),
                            'num_edges': roi_data.get('num_edges', 0)
                        }
                        interaction_data[interaction_name].append(roi_info)
    
    return interaction_data

def create_interaction_coarse_mapping():
    """Create mapping from interaction to coarse category - updated"""
    mapping = {
        'B-cell infiltration': 'B-cell',
        'T-cell maturation': 'T-cell',
        'Inflammatory zone': 'Inflammatory',
        'Oxidative stress regulation': 'Oxidative'
    }
    return mapping

def categorize_score(score):
    """Categorize score into High, Medium, Low"""
    if score >= 0.5:
        return 'High'
    elif score >= 0.3:
        return 'Medium'
    else:
        return 'Low'

def filter_nearby_rois(rois, radius=25):
    """Filter ROIs that are too close to each other, keeping the one with higher score"""
    if not rois:
        return rois
    
    # Sort ROIs by score in descending order (highest first)
    sorted_rois = sorted(rois, key=lambda x: x['score'], reverse=True)
    filtered_rois = []
    
    for current_roi in sorted_rois:
        # Check if current ROI is too close to any already accepted ROI
        too_close = False
        for accepted_roi in filtered_rois:
            distance = calculate_distance(current_roi, accepted_roi)
            if distance < radius:
                too_close = True
                break
        
        # If not too close to any accepted ROI, add it
        if not too_close:
            filtered_rois.append(current_roi)
    
    return filtered_rois

def filter_corner_rois_simple(rois, min_x=50, min_y=50):
    """Filter ROIs that are in corners (x < 50 or y < 50)"""
    if not rois:
        return rois
    
    filtered_rois = []
    for roi in rois:
        x = roi.get('x', 0)
        y = roi.get('y', 0)
        
        # Check if ROI is not in corners (x >= 50 and y >= 50)
        if x >= min_x and y >= min_y:
            filtered_rois.append(roi)
    
    return filtered_rois



def calculate_distance(roi1, roi2):
    """Calculate Euclidean distance between two ROIs"""
    dx = roi1['x'] - roi2['x']
    dy = roi1['y'] - roi2['y']
    dz = roi1['z'] - roi2['z']
    return (dx**2 + dy**2 + dz**2)**0.5

def create_circle_polygon(center_x, center_y, radius, num_points=32):
    """Create a circle polygon with specified number of points"""
    import math
    polygon = []
    for i in range(num_points + 1):  # +1 to close the circle
        angle = 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        polygon.append([round(x), round(y)])
    return polygon

def generate_vitessce_config():
    backend_dir = Path(__file__).parent.resolve()
    output_dir = backend_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data grouped by interaction
    interaction_data = load_roi_data_by_interaction(output_dir)
    interaction_coarse = create_interaction_coarse_mapping()
    
    if not interaction_data:
        logger.error("No ROI data found in JSON files")
        return

    # Process each interaction separately
    for interaction_name, rois in interaction_data.items():
        logger.info(f"Processing interaction: {interaction_name}")
        
        # Skip corner filtering to keep all ROIs
        corner_filtered_rois = rois  # Keep all ROIs
        logger.info(f"Corner filtered: {len(rois)} ROIs to {len(corner_filtered_rois)} ROIs for {interaction_name}")
        
        # Then filter nearby ROIs, keeping the ones with higher scores
        filtered_rois = filter_nearby_rois(corner_filtered_rois, radius=50)
        logger.info(f"Nearby filtered: {len(corner_filtered_rois)} ROIs to {len(filtered_rois)} ROIs for {interaction_name}")
        
        # Sort filtered ROIs by score in descending order (highest score first)
        filtered_rois.sort(key=lambda x: x['score'], reverse=True)
        
        # Limit to top 4 ROIs
        filtered_rois = filtered_rois[:4]
        
        # Create safe filename
        safe_interaction_name = re.sub(r'[^a-zA-Z0-9_-]', '_', interaction_name)
        
        # === Create roi_segmentation_{interaction}.json ===
        segmentations = {}
        y_max = 5508
        radius = 25 * 8  # Convert radius to pixel coordinates (multiply by 8)
        
        for idx, roi in enumerate(filtered_rois):
            x = max(0, round(float(roi['x']) * 8))
            # Use y coordinate without flip
            y = max(0, round(float(roi['y']) * 8))
            
            # Create circle polygon instead of rectangle
            polygon = create_circle_polygon(x, y, radius, num_points=32)
            polygon = [[max(0, round(coord[0])), max(0, round(coord[1]))] for coord in polygon]
            
            # Create ROI name with format: ROI_ID (ID starts from 1)
            roi_id = idx + 1  # Start from 1, not 0
            roi_name = f"ROI_{roi_id}"
            
            # Store polygon data directly (Vitessce format)
            segmentations[roi_name] = [polygon]
        
        roi_seg_path = output_dir / f"roi_segmentation_{safe_interaction_name}.json"
        with open(roi_seg_path, 'w') as f:
            json.dump(segmentations, f, indent=2)
        logger.info(f"Saved roi_segmentation_{safe_interaction_name}.json")
        
        # === Create obsFeatureMatrix_{interaction}.csv ===
        feature_data = []
        for idx, roi in enumerate(filtered_rois):
            roi_id = idx + 1  # Start from 1, not 0
            roi_name = f"ROI_{roi_id}"
            feature_data.append({
                'roi_id': roi_name,
                'score': roi['score'],
                'intensity_score': roi['intensity_score'],
                'attention_score': roi['attention_score'],
                'num_nodes': roi['num_nodes'],
                'num_edges': roi['num_edges'],
                'x': roi['x'],
                'y': roi['y'],
                'z': roi['z']
            })
        
        feature_df = pd.DataFrame(feature_data)
        feature_path = output_dir / f"obsFeatureMatrix_{safe_interaction_name}.csv"
        feature_df.to_csv(feature_path, index=False)
        logger.info(f"Saved obsFeatureMatrix_{safe_interaction_name}.csv")
        
        # === Create obsSets_{interaction}.csv ===
        sets_data = []
        for idx, roi in enumerate(filtered_rois):
            roi_id = idx + 1  # Start from 1, not 0
            roi_name = f"ROI_{roi_id}"
            sets_data.append({
                'roi_id': roi_name,
                'score_category': categorize_score(roi['score']),
                'pred_score': roi['score']
            })
        
        sets_df = pd.DataFrame(sets_data)
        sets_path = output_dir / f"obsSets_{safe_interaction_name}.csv"
        sets_df.to_csv(sets_path, index=False)
        logger.info(f"Saved obsSets_{safe_interaction_name}.csv")
        
        # === Create obsFeatureMatrix_{interaction}.json ===
        feature_matrix = {
            "version": "0.1.0",
            "type": "obsFeatureMatrix",
            "data": {}
        }
        
        for idx, roi in enumerate(filtered_rois):
            roi_id = idx + 1  # Start from 1, not 0
            roi_name = f"ROI_{roi_id}"
            feature_matrix["data"][roi_name] = {
                "score": float(roi['score']),
                "intensity_score": float(roi['intensity_score']),
                "attention_score": float(roi['attention_score']),
                "num_nodes": int(roi['num_nodes']),
                "num_edges": int(roi['num_edges'])
            }
        
        feature_json_path = output_dir / f"obsFeatureMatrix_{safe_interaction_name}.json"
        with open(feature_json_path, 'w') as f:
            json.dump(feature_matrix, f, indent=2)
        logger.info(f"Saved obsFeatureMatrix_{safe_interaction_name}.json")

    # === Create combined files (original functionality) ===
    all_rois = []
    for interaction_name, rois in interaction_data.items():
        # Apply corner filtering first (x < 50 or y < 50)
        corner_filtered_rois = filter_corner_rois_simple(rois, min_x=50, min_y=50)
        # Then apply nearby filtering
        filtered_rois = filter_nearby_rois(corner_filtered_rois, radius=25)
        all_rois.extend(filtered_rois)
    
    roi_df = pd.DataFrame(all_rois)
    
    # === Create combined obsSegmentations.json ===
    segmentations = {}
    y_max = 5508
    radius = 25 * 8  # Convert radius to pixel coordinates
    
    # Create counter for ROI IDs to start from 1
    roi_counter = 0
    
    for idx, row in roi_df.iterrows():
        x = max(0, round(float(row['x']) * 8))
        # Use y coordinate without flip
        y = max(0, round(float(row['y']) * 8))
        
        # Create circle polygon instead of rectangle
        polygon = create_circle_polygon(x, y, radius, num_points=32)
        polygon = [[max(0, round(coord[0])), max(0, round(coord[1]))] for coord in polygon]
        
        # Create ROI name with format: ROI_ID (ID starts from 1)
        roi_counter += 1
        roi_name = f"ROI_{roi_counter}"
        segmentations[roi_name] = [polygon]

    obs_seg_path = output_dir / "roi_rectangles_annotation.json"
    with open(obs_seg_path, 'w') as f:
        json.dump(segmentations, f, indent=2)
    logger.info(f"Saved combined obsSegmentations.json to {obs_seg_path}")

    # === Create combined obsFeatureMatrix.json ===
    feature_matrix = {
        "version": "0.1.0",
        "type": "obsFeatureMatrix",
        "data": {}
    }

    # Create counter for ROI IDs to start from 1
    roi_counter = 0
    
    for idx, row in roi_df.iterrows():
        roi_counter += 1
        roi_name = f"ROI_{roi_counter}"
        feature_matrix["data"][roi_name] = {
            "score": float(row['score']),
            "intensity_score": float(row['intensity_score']),
            "attention_score": float(row['attention_score']),
            "num_nodes": int(row['num_nodes']),
            "num_edges": int(row['num_edges'])
        }

    obs_feat_path = output_dir / "obsFeatureMatrix.json"
    with open(obs_feat_path, 'w') as f:
        json.dump(feature_matrix, f, indent=2)
    logger.info(f"Saved combined obsFeatureMatrix.json to {obs_feat_path}")

    # === Print summary ===
    print("\n" + "="*60)
    print("INTERACTION-SPECIFIC FILES GENERATION SUMMARY")
    print("="*60)
    for interaction_name, rois in interaction_data.items():
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', interaction_name)
        filtered_rois = filter_nearby_rois(rois, radius=25)
        print(f"\n{interaction_name}:")
        print("-" * 40)
        print(f"Original ROIs: {len(rois)}")
        print(f"Filtered ROIs: {len(filtered_rois)}")
        print(f"Score range: {max(r['score'] for r in filtered_rois):.4f} - {min(r['score'] for r in filtered_rois):.4f}")
        print(f"Files created:")
        print(f"  - roi_segmentation_{safe_name}.json")
        print(f"  - obsFeatureMatrix_{safe_name}.csv")
        print(f"  - obsFeatureMatrix_{safe_name}.json")
        print(f"  - obsSets_{safe_name}.csv")
    print("\n" + "="*60)

def update_roi_json_format():
    """Update existing JSON files to remove interaction names and change ROI naming format"""
    
    output_dir = Path(__file__).parent / 'output'
    
    # Update top_roi_scores files
    top_roi_files = glob.glob(str(output_dir / "top_roi_scores_*.json"))
    
    for file_path in top_roi_files:
        logger.info(f"Processing: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Remove interaction_name from root level
        if 'interaction_name' in data:
            del data['interaction_name']
        
        # Update each ROI
        for roi in data.get('top_rois', []):
            # Remove interaction field
            if 'interaction' in roi:
                del roi['interaction']
            
            # Update tooltip_name to new format
            if 'tooltip_name' in roi:
                roi_id = roi.get('roi_id', 0)
                roi['tooltip_name'] = f"ROI_{roi_id}"
        
        # Write updated file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Updated: {file_path}")
    
    # Update obsFeatureMatrix.json
    obs_feat_file = output_dir / "obsFeatureMatrix.json"
    if obs_feat_file.exists():
        logger.info(f"Processing: {obs_feat_file}")
        
        with open(obs_feat_file, 'r') as f:
            data = json.load(f)
        
        # Create new data structure with updated ROI names
        new_data = {
            "version": data.get("version", "0.1.0"),
            "type": data.get("type", "obsFeatureMatrix"),
            "data": {}
        }
        
        roi_counter = 0
        for old_name, roi_data in data.get("data", {}).items():
            roi_counter += 1
            new_name = f"ROI_{roi_counter}"
            
            # Remove interaction field
            new_roi_data = {k: v for k, v in roi_data.items() if k != "interaction"}
            new_data["data"][new_name] = new_roi_data
        
        # Write updated file
        with open(obs_feat_file, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        logger.info(f"Updated: {obs_feat_file}")
    
    # Update individual obsFeatureMatrix files
    individual_files = glob.glob(str(output_dir / "obsFeatureMatrix_*.json"))
    
    for file_path in individual_files:
        if "obsFeatureMatrix.json" in file_path:  # Skip the main file
            continue
            
        logger.info(f"Processing: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Create new data structure with updated ROI names
        new_data = {
            "version": data.get("version", "0.1.0"),
            "type": data.get("type", "obsFeatureMatrix"),
            "data": {}
        }
        
        roi_counter = 0
        for old_name, roi_data in data.get("data", {}).items():
            roi_counter += 1
            new_name = f"ROI_{roi_counter}"
            
            # Remove interaction field
            new_roi_data = {k: v for k, v in roi_data.items() if k != "interaction"}
            new_data["data"][new_name] = new_roi_data
        
        # Write updated file
        with open(file_path, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        logger.info(f"Updated: {file_path}")
    
    # Update roi_segmentation files to limit to top 5 ROIs
    roi_seg_files = glob.glob(str(output_dir / "roi_segmentation_*.json"))
    
    for file_path in roi_seg_files:
        logger.info(f"Processing roi_segmentation: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Get all ROI names and sort by score (extract score from name)
        roi_items = list(data.items())
        
        # Safe sorting with error handling
        def extract_score(roi_item):
            try:
                roi_name = roi_item[0]
                if 'Score:' in roi_name:
                    score_str = roi_name.split('Score:')[1]
                    return float(score_str)
                else:
                    return 0.0  # Default score if no score found
            except (IndexError, ValueError):
                return 0.0  # Default score if parsing fails
        
        roi_items.sort(key=extract_score, reverse=True)
        
        # Keep only top 4 ROIs
        top_4_rois = roi_items[:4]
        
        # Create new data with sequential IDs
        new_data = {}
        for idx, (old_name, roi_data) in enumerate(top_4_rois):
            # Safe score extraction
            try:
                if 'Score:' in old_name:
                    score = float(old_name.split('Score:')[1])
                else:
                    score = 0.0
            except (IndexError, ValueError):
                score = 0.0
            
            new_name = f"ROI_{idx + 1}"
            
            # Keep the polygon data in Vitessce format
            if isinstance(roi_data, list):
                new_data[new_name] = roi_data
            elif isinstance(roi_data, dict) and "polygon" in roi_data:
                new_data[new_name] = roi_data["polygon"]
            else:
                new_data[new_name] = roi_data
        
        # Write updated file
        with open(file_path, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        logger.info(f"Updated roi_segmentation: {file_path} - kept top 4 ROIs")
    
    logger.info("All JSON files updated successfully!")

if __name__ == "__main__":
    # Update ROI JSON format first
    update_roi_json_format()
    
    # Generate vitessce config files
    generate_vitessce_config()
