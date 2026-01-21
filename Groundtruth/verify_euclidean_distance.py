"""
Verification script for Euclidean distance calculation
"""

import numpy as np

# Configuration parameters (from Cell 3)
Z_SCALE_FACTOR = 2.0
EUCLIDEAN_STEP = 1

def calculate_euclidean_distance(model_point, gt_point, z_scale_factor=2.0):
    """
    Calculate Euclidean distance between two points with Z_SCALE_FACTOR applied
    
    Args:
        model_point: (x, y, z) - model prediction point
        gt_point: (x, y, z) - ground truth point
        z_scale_factor: scale factor for Z axis (default: 2.0)
    
    Returns:
        Euclidean distance (voxels)
    """
    # Coordinate differences
    dx = model_point[0] - gt_point[0]  # x difference
    dy = model_point[1] - gt_point[1]  # y difference
    dz = model_point[2] - gt_point[2]  # z difference
    
    # Apply Z_SCALE_FACTOR to Z axis
    dz_scaled = dz * z_scale_factor
    
    # Calculate Euclidean distance
    distance = np.sqrt(dx**2 + dy**2 + dz_scaled**2)
    
    return distance


def calculate_euclidean_batch(model_points, gt_points, z_scale_factor=2.0):
    """
    Calculate Euclidean distance in batch mode (like original code)
    
    Args:
        model_points: array of shape (n_model, 3) - model prediction points
        gt_points: array of shape (n_gt, 3) - ground truth points
        z_scale_factor: scale factor for Z axis
    
    Returns:
        array of shape (n_model, n_gt) - distance between each pair of points
    """
    # Convert to numpy array
    model_pts = np.array(model_points, dtype=np.float32)
    gt_pts = np.array(gt_points, dtype=np.float32)
    
    # Calculate differences (broadcasting)
    diff = model_pts[:, np.newaxis, :] - gt_pts[np.newaxis, :, :]
    # diff shape: (n_model, n_gt, 3)
    
    # Apply Z_SCALE_FACTOR to Z axis
    diff[:, :, 2] = diff[:, :, 2] * z_scale_factor
    
    # Calculate Euclidean distance
    dist = np.sqrt(np.sum(diff**2, axis=2))
    # dist shape: (n_model, n_gt)
    
    return dist


def normalize_euclidean(distances, euclidean_step=1):
    """
    Normalize Euclidean distances
    
    Args:
        distances: array or list of distances
        euclidean_step: normalization value (default: 1)
    
    Returns:
        Normalized distances
    """
    distances = np.array(distances)
    distances = distances / euclidean_step
    return distances


# ============================================================
# Test Examples
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Euclidean Distance Calculation Verification")
    print("=" * 60)
    
    # Example 1: Single point calculation
    print("\n📌 Example 1: Single point calculation")
    print("-" * 60)
    model_point = (10, 20, 5)
    gt_point = (12, 22, 6)
    
    distance = calculate_euclidean_distance(model_point, gt_point, Z_SCALE_FACTOR)
    print(f"Model point: {model_point}")
    print(f"GT point:    {gt_point}")
    print(f"Z_SCALE_FACTOR: {Z_SCALE_FACTOR}")
    print(f"\nDifferences:")
    print(f"  dx = {model_point[0] - gt_point[0]}")
    print(f"  dy = {model_point[1] - gt_point[1]}")
    print(f"  dz = {model_point[2] - gt_point[2]}")
    print(f"  dz_scaled = {model_point[2] - gt_point[2]} × {Z_SCALE_FACTOR} = {(model_point[2] - gt_point[2]) * Z_SCALE_FACTOR}")
    print(f"\nEuclidean distance: {distance:.4f} voxels")
    
    # Manual calculation for verification
    dx = model_point[0] - gt_point[0]
    dy = model_point[1] - gt_point[1]
    dz_scaled = (model_point[2] - gt_point[2]) * Z_SCALE_FACTOR
    manual_calc = np.sqrt(dx**2 + dy**2 + dz_scaled**2)
    print(f"Manual calculation: √[({dx})² + ({dy})² + ({dz_scaled})²] = {manual_calc:.4f}")
    
    # Example 2: Batch calculation
    print("\n📌 Example 2: Batch calculation (like original code)")
    print("-" * 60)
    model_points = [
        [10, 20, 5],
        [15, 25, 7],
        [8, 18, 4]
    ]
    gt_points = [
        [12, 22, 6],
        [14, 24, 8],
        [9, 19, 5]
    ]
    
    dist_matrix = calculate_euclidean_batch(model_points, gt_points, Z_SCALE_FACTOR)
    print(f"Model points ({len(model_points)} points):")
    for i, pt in enumerate(model_points):
        print(f"  M{i}: {pt}")
    print(f"\nGT points ({len(gt_points)} points):")
    for i, pt in enumerate(gt_points):
        print(f"  G{i}: {pt}")
    print(f"\nDistance matrix (shape: {dist_matrix.shape}):")
    print("      ", end="")
    for j in range(len(gt_points)):
        print(f"  G{j}  ", end="")
    print()
    for i in range(len(model_points)):
        print(f"M{i}  ", end="")
        for j in range(len(gt_points)):
            print(f"{dist_matrix[i, j]:6.2f}", end="")
        print()
    
    # Example 3: Find closest GT for each model
    print("\n📌 Example 3: Find closest GT")
    print("-" * 60)
    min_distances = dist_matrix.min(axis=1)
    closest_gt_indices = dist_matrix.argmin(axis=1)
    
    for i in range(len(model_points)):
        print(f"Model M{i} {model_points[i]}:")
        print(f"  Closest GT: G{closest_gt_indices[i]} {gt_points[closest_gt_indices[i]]}")
        print(f"  Distance: {min_distances[i]:.4f} voxels")
    
    # Example 4: Normalization
    print("\n📌 Example 4: Normalization")
    print("-" * 60)
    distances = [3.464, 5.0, 7.211]
    normalized = normalize_euclidean(distances, EUCLIDEAN_STEP)
    print(f"Original distances: {distances}")
    print(f"EUCLIDEAN_STEP: {EUCLIDEAN_STEP}")
    print(f"Normalized distances: {normalized}")
    print("(Since EUCLIDEAN_STEP=1, no change)")
    
    print("\n" + "=" * 60)
    print("✅ Verification complete!")
    print("=" * 60)
