import json
import math
from pathlib import Path

def generate_circle_points(center_x, center_y, radius, num_points=32, counterclockwise=False):
    """
    Generate polygon points for a circle.
    
    Args:
        center_x: X coordinate of circle center
        center_y: Y coordinate of circle center
        radius: Radius of the circle
        num_points: Number of points to generate (default 32)
        counterclockwise: If True, generate points in counterclockwise direction (for holes)
    
    Returns:
        List of [x, y] coordinate pairs
    """
    points = []
    direction = -1 if counterclockwise else 1
    for i in range(num_points):
        angle = direction * 2 * math.pi * i / num_points
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        points.append([int(round(x)), int(round(y))])
    # Close the circle by adding the first point at the end
    points.append(points[0])
    return points

def process_roi_file(input_file_path, output_file_path):
    """
    Read ROI scores file and generate circle overlay JSON.
    
    Args:
        input_file_path: Path to input JSON file (top5_roi_scores_*.json)
        output_file_path: Path to output JSON file (roi_segmentation_*.json)
    """
    # Read input file
    with open(input_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract interaction name and create output structure
    output_data = {}
    
    # Process each ROI in top_rois
    for idx, roi in enumerate(data['top_rois'], start=1):
        x = roi['position']['x']
        y = roi['position']['y']
        
        # Calculate circle center (x*8, y*8)
        center_x = x * 8
        center_y = y * 8
        
        # Outer circle radius: 240
        # Thickness: 10
        # Inner hole radius: outer_radius - thickness = 230
        outer_radius = 240
        thickness = 10
        inner_radius = outer_radius - thickness
        
        # Generate outer circle (exterior ring) - clockwise
        outer_circle = generate_circle_points(center_x, center_y, outer_radius, counterclockwise=False)
        
        # Generate inner circle (interior ring/hole) - counterclockwise for hole
        inner_circle = generate_circle_points(center_x, center_y, inner_radius, counterclockwise=True)
        
        # Create main ring structure: [outer_ring, inner_ring]
        roi_key = f"ROI_{idx}"
        output_data[roi_key] = [outer_circle, inner_circle]
        
        # Add filled counting circles above based on position (idx = rank 1 to 5)
        # Rank 1 = 1 counting circle, Rank 5 = 5 counting circles
        num_counting_circles = idx
        counting_circle_radius = 25
        distance_above = 200  # 300 pixels above center
        spacing = 75  # Distance between centers of counting circles
        
        # Calculate starting position to center the circles
        total_width = (num_counting_circles - 1) * spacing
        start_x = center_x - (total_width / 2)
        counting_y = center_y - distance_above
        
        # Generate filled circles as separate ROI entries (ROI_11, ROI_12, etc.)
        for i in range(num_counting_circles):
            counting_center_x = start_x + (i * spacing)
            counting_circle = generate_circle_points(
                counting_center_x, 
                counting_y, 
                counting_circle_radius, 
                counterclockwise=False
            )
            # Create separate ROI entry for counting circle: ROI_{idx}{counting_idx}
            counting_roi_key = f"ROI_{idx}{i + 1}"
            # Filled circle (only outer ring, no inner hole)
            output_data[counting_roi_key] = [counting_circle]
    
    # Write output file
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Generated {len(output_data)} circles in {output_file_path}")

def main():
    # Base directory
    base_dir = Path(r"D:\VIS2025\BIoVisChallenges\SSGAT\backend\output")
    
    # Input files and their corresponding output names
    file_mappings = [
        {
            'input': 'top5_roi_scores_B-cell infiltration.json',
            'output': 'roi_segmentation_B-cell_infiltration.json'
        },
        {
            'input': 'top5_roi_scores_Inflammatory zone.json',
            'output': 'roi_segmentation_Inflammatory_zone.json'
        },
        {
            'input': 'top5_roi_scores_Oxidative stress regulation.json',
            'output': 'roi_segmentation_Oxidative_stress_regulation.json'
        },
        {
            'input': 'top5_roi_scores_T-cell maturation.json',
            'output': 'roi_segmentation_T-cell_maturation.json'
        }
    ]
    
    # Process each file
    for mapping in file_mappings:
        input_path = base_dir / mapping['input']
        output_path = base_dir / mapping['output']
        
        if input_path.exists():
            process_roi_file(input_path, output_path)
        else:
            print(f"Warning: Input file not found: {input_path}")

if __name__ == "__main__":
    main()

