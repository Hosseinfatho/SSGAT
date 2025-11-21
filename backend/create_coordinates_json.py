import json
from pathlib import Path

def create_coordinates_json():
    """
    Create a JSON file with filled 20x20 pixel squares only on x=0 and y=0 axes.
    Each square is centered at coordinates that are 50 pixels apart.
    Format: "x,y": [[x-10, y-10], [x+10, y-10], [x+10, y+10], [x-10, y+10], [x-10, y-10]]
    """
    # Image dimensions (based on the codebase)
    IMAGE_WIDTH = 10908
    IMAGE_HEIGHT = 5508
    
    # Grid spacing (100 pixels between centers)
    SPACING = 100
    
    # Square size (100x100 pixels, so 50 pixels on each side of center)
    SQUARE_HALF_SIZE = 50
    
    coordinates = {}
    
    # Generate squares only on x=0 axis (vertical line)
    # For y-axis (x=0), use only y coordinate as key (e.g., "1000" instead of "0,1000")
    y = 0
    while y < IMAGE_HEIGHT:
        x = 0
        # Clamp coordinates to image bounds
        top_left_x = max(0, x - SQUARE_HALF_SIZE)
        top_left_y = max(0, y - SQUARE_HALF_SIZE)
        bottom_right_x = min(IMAGE_WIDTH - 1, x + SQUARE_HALF_SIZE)
        bottom_right_y = min(IMAGE_HEIGHT - 1, y + SQUARE_HALF_SIZE)
        
        # Create filled square (closed polygon)
        square = [
            [top_left_x, top_left_y],           # Top-left
            [bottom_right_x, top_left_y],       # Top-right
            [bottom_right_x, bottom_right_y],   # Bottom-right
            [top_left_x, bottom_right_y],       # Bottom-left
            [top_left_x, top_left_y]            # Close the polygon
        ]
        
        # Use only y coordinate as key for y-axis (x=0)
        # Add a space before the number to distinguish from x-axis
        # For (0,0), use "0", for others use " y" (e.g., " 1000")
        if y == 0:
            key = "0"
        else:
            key = f" {y}"  # Add space before y coordinate
        coordinates[key] = square
        
        y += SPACING
    
    # Generate squares only on y=0 axis (horizontal line), but skip (0,0) since we already added it
    # For x-axis (y=0), use only x coordinate as key (e.g., "1000" instead of "1000,0")
    x = SPACING
    while x < IMAGE_WIDTH:
        y = 0
        # Clamp coordinates to image bounds
        top_left_x = max(0, x - SQUARE_HALF_SIZE)
        top_left_y = max(0, y - SQUARE_HALF_SIZE)
        bottom_right_x = min(IMAGE_WIDTH - 1, x + SQUARE_HALF_SIZE)
        bottom_right_y = min(IMAGE_HEIGHT - 1, y + SQUARE_HALF_SIZE)
        
        # Create filled square (closed polygon)
        square = [
            [top_left_x, top_left_y],           # Top-left
            [bottom_right_x, top_left_y],       # Top-right
            [bottom_right_x, bottom_right_y],   # Bottom-right
            [top_left_x, bottom_right_y],       # Bottom-left
            [top_left_x, top_left_y]            # Close the polygon
        ]
        
        # Use only x coordinate as key for x-axis (y=0)
        key = str(x)
        coordinates[key] = square
        
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
    print(f"Square size: 100x100 pixels (filled)")
    print(f"Location: Only on x=0 and y=0 axes")
    print(f"Image dimensions: {IMAGE_WIDTH} x {IMAGE_HEIGHT}")
    
    # Print a sample
    sample_key = list(coordinates.keys())[0]
    print(f"\nSample entry:")
    print(f'  "{sample_key}": {coordinates[sample_key]}')

if __name__ == '__main__':
    create_coordinates_json()

