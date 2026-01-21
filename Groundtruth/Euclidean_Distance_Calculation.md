# Euclidean Distance Calculation

## 📍 Cell: Cell 7 (Coordinate Extraction & Accuracy)

## 🔧 Configuration Parameters (Cell 3)

```python
Z_SCALE_FACTOR = 2.0  # Scale factor for Z axis
EUCLIDEAN_STEP = 1    # Normalization (all distances divided by this value)
MATCH_TOLERANCE = max(MAX_RADIUS, 4)  # Tolerance threshold for matching
```

**Explanation:**
- `Z_SCALE_FACTOR = 2.0`: Since Z resolution is half of X,Y, we multiply Z difference by 2
- `EUCLIDEAN_STEP = 1`: Currently no normalization (division by 1)

---

## 📐 Euclidean Distance Formula

### Main Formula:

```
distance = sqrt( (x_diff)² + (y_diff)² + (z_diff × Z_SCALE_FACTOR)² )
```

### Mathematical Form:

```
distance = √[(x_model - x_gt)² + (y_model - y_gt)² + (z_model - z_gt)² × (Z_SCALE_FACTOR)²]
```

Or equivalently:

```
distance = √[(x_model - x_gt)² + (y_model - y_gt)² + ((z_model - z_gt) × Z_SCALE_FACTOR)²]
```

---

## 💻 Calculation Code (Cell 7 - `compute_accuracy` function)

### Main Distance Calculation Section:

```python
# Lines 823-827: Calculate distance for each batch of model predictions

for i in range(0, n_model, batch_size):
    batch_model = model_pts[i:i+batch_size]
    
    # Calculate coordinate differences
    diff = batch_model[:, np.newaxis, :] - gt_pts[np.newaxis, :, :]
    # diff shape: (batch_size, n_gt, 3)
    # diff[:, :, 0] = x difference
    # diff[:, :, 1] = y difference  
    # diff[:, :, 2] = z difference
    
    # Apply Z_SCALE_FACTOR to Z axis
    diff[:, :, 2] = diff[:, :, 2] * Z_SCALE_FACTOR  # Scale z dimension
    
    # Calculate Euclidean distance
    dist = np.sqrt(np.sum(diff**2, axis=2))  # (batch_size, n_gt)
    # dist[i, j] = distance between model_point[i] and gt_point[j]
```

### Step-by-Step Explanation:

1. **Coordinate Differences:**
   ```python
   diff = batch_model[:, np.newaxis, :] - gt_pts[np.newaxis, :, :]
   ```
   - `diff[:, :, 0]` = x_model - x_gt
   - `diff[:, :, 1]` = y_model - y_gt
   - `diff[:, :, 2]` = z_model - z_gt

2. **Z-axis Scaling:**
   ```python
   diff[:, :, 2] = diff[:, :, 2] * Z_SCALE_FACTOR
   ```
   - Z difference is multiplied by 2.0

3. **Distance Calculation:**
   ```python
   dist = np.sqrt(np.sum(diff**2, axis=2))
   ```
   - `diff**2` = squared differences
   - `np.sum(..., axis=2)` = sum over axis 2 (x, y, z)
   - `np.sqrt(...)` = square root for Euclidean distance

---

## 📊 Normalization (`normalize_euclidean` function)

```python
def normalize_euclidean(distances):
    """Normalize Euclidean distances by dividing by EUCLIDEAN_STEP."""
    distances = np.array(distances)
    distances = distances / EUCLIDEAN_STEP
    return distances
```

**Usage:**
- Only used for non-matching distances (FP)
- Currently `EUCLIDEAN_STEP = 1` so no change

---

## 🎯 Manual Calculation Example

Assume:
- Model point: `(x_m=10, y_m=20, z_m=5)`
- GT point: `(x_g=12, y_g=22, z_g=6)`
- `Z_SCALE_FACTOR = 2.0`

**Calculation:**

1. Differences:
   - `dx = 10 - 12 = -2`
   - `dy = 20 - 22 = -2`
   - `dz = 5 - 6 = -1`

2. Z Scaling:
   - `dz_scaled = -1 × 2.0 = -2`

3. Euclidean Distance:
   ```
   distance = √[(-2)² + (-2)² + (-2)²]
            = √[4 + 4 + 4]
            = √12
            = 3.464 voxels
   ```

---

## 📝 Summary

| Parameter | Value | Description |
|-----------|-------|-------------|
| `Z_SCALE_FACTOR` | 2.0 | Scale factor for Z axis |
| `EUCLIDEAN_STEP` | 1 | Normalization (currently no effect) |
| `MATCH_TOLERANCE` | max(MAX_RADIUS, 4) | Tolerance threshold for matching |

**Final Formula:**
```
distance = √[(Δx)² + (Δy)² + (Δz × 2.0)²]
```

**Cell:** Cell 7 (lines 780-879)  
**Function:** `compute_accuracy()`  
**Key Lines:** 823-827
