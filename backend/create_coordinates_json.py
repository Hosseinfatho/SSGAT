import json
from pathlib import Path

def create_coordinates_json():
    """
    Create a JSON file with 50x50 pixel squares on a grid.
    Each square is centered at coordinates that are 200 pixels apart.
    Format: "x,y": [[x-25, y-25], [x+25, y-25], [x+25, y+25], [x-25, y+25], [x-25, y-25]]
    """
    # Image dimensions (based on the codebase)
    IMAGE_WIDTH = 10908
    IMAGE_HEIGHT = 5508
    
    # Grid spacing (400 pixels between centers)
    SPACING = 400
    
    # Square size (200x200 pixels, so 100 pixels on each side of center)
    SQUARE_HALF_SIZE = 100
    
    coordinates = {}
    
    # Generate grid points
    # Start from (100, 100) to avoid negative coordinates for 50x50 squares
    x = 100
    while x < IMAGE_WIDTH:
        y = 100
        while y < IMAGE_HEIGHT:
            # Create a square with thickness (outline/unfilled) similar to ROI format
            # Outer square (200x200)
            outer_half = SQUARE_HALF_SIZE
            # Inner square (for thickness of 5, inner square is 190x190)
            thickness = 5
            inner_half = SQUARE_HALF_SIZE - thickness
            
            # Clamp coordinates to image bounds
            outer_top_left_x = max(0, x - outer_half)
            outer_top_left_y = max(0, y - outer_half)
            outer_bottom_right_x = min(IMAGE_WIDTH - 1, x + outer_half)
            outer_bottom_right_y = min(IMAGE_HEIGHT - 1, y + outer_half)
            
            inner_top_left_x = max(0, x - inner_half)
            inner_top_left_y = max(0, y - inner_half)
            inner_bottom_right_x = min(IMAGE_WIDTH - 1, x + inner_half)
            inner_bottom_right_y = min(IMAGE_HEIGHT - 1, y + inner_half)
            
            # Create outline: outer square (clockwise) + inner square (counter-clockwise)
            # Outer square: top-left -> top-right -> bottom-right -> bottom-left -> back to top-left
            square = [
                [outer_top_left_x, outer_top_left_y],           # Outer top-left
                [outer_bottom_right_x, outer_top_left_y],       # Outer top-right
                [outer_bottom_right_x, outer_bottom_right_y],   # Outer bottom-right
                [outer_top_left_x, outer_bottom_right_y],       # Outer bottom-left
                [outer_top_left_x, outer_top_left_y],           # Back to outer top-left
                # Inner square (counter-clockwise to create hole)
                [inner_top_left_x, inner_top_left_y],           # Inner top-left
                [inner_top_left_x, inner_bottom_right_y],       # Inner bottom-left
                [inner_bottom_right_x, inner_bottom_right_y],   # Inner bottom-right
                [inner_bottom_right_x, inner_top_left_y],       # Inner top-right
                [inner_top_left_x, inner_top_left_y]            # Back to inner top-left
            ]
            
            # Use center coordinates as key (format: "x,y")
            key = f"{x},{y}"
            coordinates[key] = square
            
            y += SPACING
        x += SPACING
    
    # Save to output directory
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'roi_segmentation_coordinates.json'
    
    with open(output_file, 'w') as f:
        json.dump(coordinates, f, indent=2)
    
    print(f"Created coordinates JSON file: {output_file}")
    print(f"Total squares: {len(coordinates)}")
    print(f"Grid spacing: {SPACING} pixels")
    print(f"Square size: 50x50 pixels")
    print(f"Image dimensions: {IMAGE_WIDTH} x {IMAGE_HEIGHT}")
    
    # Print a sample
    sample_key = list(coordinates.keys())[0]
    print(f"\nSample entry:")
    print(f'  "{sample_key}": {coordinates[sample_key]}')

if __name__ == '__main__':
    create_coordinates_json()

