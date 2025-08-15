import json
import math
import numpy as np
from pathlib import Path

def create_circle_polygon(center_x, center_y, radius=200, num_points=64):
    """
    Create a circle polygon with specified radius
    Returns a list of coordinate pairs
    """
    polygon = []
    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        polygon.append([round(x), round(y)])
    return polygon

def create_hollow_circle_polygon(center_x, center_y, radius=200, stroke_width=25, num_points=64):
    """
    Create a hollow circle polygon (ring) with specified stroke width
    Returns two polygons: outer and inner circles
    """
    # Outer circle (larger radius)
    outer_radius = radius + stroke_width // 2
    outer_polygon = []
    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        x = center_x + outer_radius * math.cos(angle)
        y = center_y + outer_radius * math.sin(angle)
        outer_polygon.append([round(x), round(y)])
    
    # Inner circle (smaller radius)
    inner_radius = radius - stroke_width // 2
    inner_polygon = []
    for i in range(num_points + 1):
        angle = 2 * math.pi * i / num_points
        x = center_x + inner_radius * math.cos(angle)
        y = center_y + inner_radius * math.sin(angle)
        inner_polygon.append([round(x), round(y)])
    
    # Create hollow circle by combining outer and inner (reverse inner)
    hollow_polygon = outer_polygon + inner_polygon[::-1]
    return hollow_polygon



def create_stem_polygon_with_offset(center_x, center_y, stem_number, total_stems, stem_width=50, stem_height=200, spacing=100):
    """
    Create a stem polygon with proper offset for symmetric positioning
    """
    # Position the stem below the circle center
    stem_y = round(center_y + 400)  # Position below the circle
    
    # Calculate symmetric offset
    # For total_stems stems, we want them centered around the circle center
    # The first stem should be at position -(total_stems-1)/2 * spacing
    # Each subsequent stem moves by spacing
    start_offset = -(total_stems - 1) / 2 * spacing
    offset_x = start_offset + (stem_number - 1) * spacing
    
    stem_x = round(center_x + offset_x)
    
    # Create rectangle coordinates for the stem
    half_width = stem_width // 2
    half_height = stem_height // 2
    
    stem_polygon = [
        [stem_x - half_width, stem_y - half_height],  # Top-left
        [stem_x + half_width, stem_y - half_height],  # Top-right
        [stem_x + half_width, stem_y + half_height],  # Bottom-right
        [stem_x - half_width, stem_y + half_height],  # Bottom-left
        [stem_x - half_width, stem_y - half_height]   # Back to start
    ]
    
    return stem_polygon

def process_roi_file(input_file, output_file, interaction_name):
    """
    Process a single ROI segmentation file and create hollow circles with stem indicators
    """
    print(f"Processing {input_file}...")
    
    # Read the original ROI file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Extract ROI information - the ROIs are directly in the root
    rois = data
    
    # Create new format with circles and stems
    new_format = {}
    
    roi_count = 1
    for roi_id, roi_coords in rois.items():
        # Extract center coordinates from the polygon
        if roi_coords and len(roi_coords) > 0:
            # Calculate centroid from polygon coordinates
            coords = roi_coords
            
            # Handle nested structure: [[[x, y], [x, y], ...]]
            if isinstance(coords[0], list) and len(coords[0]) > 0 and isinstance(coords[0][0], list):
                coords = coords[0]  # Extract the inner list
            
            # Calculate centroid
            x_coords = [coord[0] for coord in coords]
            y_coords = [coord[1] for coord in coords]
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            
            # Create hollow circle polygon
            hollow_circle = create_hollow_circle_polygon(center_x, center_y, radius=200, stroke_width=25)
            
            # Add circle to format
            new_format[f"ROI_{roi_count}"] = hollow_circle
            
            # Create stems based on ROI number
            for stem_num in range(1, roi_count + 1):
                stem_polygon = create_stem_polygon_with_offset(center_x, center_y, stem_num, roi_count, stem_width=50, stem_height=200, spacing=100)
                new_format[f"ROI_{roi_count}{stem_num}"] = stem_polygon
            
            roi_count += 1
    
    # Save the data
    with open(output_file, 'w') as f:
        json.dump(new_format, f, indent=2)
    
    print(f"Created {output_file} with {len(new_format)} entries (circles + stems)")
    
    return roi_count - 1  # Return number of ROIs

def main():
    """
    Main function to process all ROI segmentation files
    """
    # Input and output directories
    input_dir = Path("input")
    output_dir = Path("../data/hollow_circles")
    output_dir.mkdir(exist_ok=True)
    
    # Interaction types to process
    interaction_types = [
        "B-cell_infiltration",
        "T-cell_maturation", 
        "Inflammatory_zone",
        "Oxidative_stress_regulation"
    ]
    
    total_processed = 0
    
    for interaction in interaction_types:
        input_file = input_dir / f"roi_segmentation_{interaction}.json"
        output_file = output_dir / f"hollow_circles_{interaction}.json"
        
        if input_file.exists():
            count = process_roi_file(input_file, output_file, interaction)
            total_processed += count
        else:
            print(f"Warning: {input_file} not found")
    
    print(f"\nProcessing complete! Created {total_processed} ROIs with stem indicators total.")
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    main()
