# Backend server code
import json
import logging
import subprocess
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

import zarr as pyzarr
import s3fs
from pathlib import Path

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Constants for Zarr Access
ZARR_BASE_URL = "s3://lsp-public-data/yapp-2023-3d-melanoma/Dataset1-LSP13626-melanoma-in-situ"
ZARR_IMAGE_GROUP_PATH = "0"
TARGET_RESOLUTION_PATH = "3"

@app.route('/api/channel_names')
def get_channel_names():
    """Reads OME-Zarr metadata to get channel names."""
    logger.info("Request received for /api/channel_names")
<<<<<<< HEAD
    
    # Return default channel mapping for local development
    channel_map = {
        '0': 'CD31',
        '1': 'CD11b', 
        '2': 'Catalase',
        '3': 'CD4',
        '4': 'CD20',
        '5': 'CD11c'
    }
    
    logger.info(f"Returning default channel names: {channel_map}")
    return jsonify(channel_map)
# --- End Channel Names Endpoint ---

def open_target_zarr_array():
    """Opens and returns the target Zarr array from local file. Returns None on failure."""
    target_image_arr = None
    try:
        # Use local Zarr file - open as group first
        zarr_path = LOCAL_ZARR_PATH
        
        logger.info(f"Attempting to open local Zarr group from: {zarr_path}")
        
        # Check if path exists
        if not zarr_path.exists():
            logger.error(f"Zarr path does not exist: {zarr_path}")
            return None
        
        # Open the Zarr group
        zarr_group = zarr.open_group(str(zarr_path), mode='r')
        logger.info(f"Zarr group keys: {list(zarr_group.keys())}")
        
        # Look for the data array - handle nested structure
        if 'data' in zarr_group:
            data_group = zarr_group['data']
            logger.info(f"Found 'data' group. Keys: {list(data_group.keys())}")
            
            # Check if data is directly an array or has nested structure
            if hasattr(data_group, 'shape'):
                # data is directly an array
                target_image_arr = data_group
                logger.info(f"✅ Successfully opened target Zarr array from local file")
                logger.info(f"Array shape: {target_image_arr.shape}")
                logger.info(f"Array dtype: {target_image_arr.dtype}")
                return target_image_arr
            else:
                # data is a group, look for the actual array
                for key in data_group.keys():
                    if hasattr(data_group[key], 'shape'):
                        target_image_arr = data_group[key]
                        logger.info(f"✅ Successfully opened target Zarr array from local file (nested)")
                        logger.info(f"Array shape: {target_image_arr.shape}")
                        logger.info(f"Array dtype: {target_image_arr.dtype}")
                        return target_image_arr
                    elif hasattr(data_group[key], 'keys'):
                        # Check nested groups (like data/c/0)
                        nested_group = data_group[key]
                        logger.info(f"Found nested group '{key}'. Keys: {list(nested_group.keys())}")
                        for nested_key in nested_group.keys():
                            if hasattr(nested_group[nested_key], 'shape'):
                                target_image_arr = nested_group[nested_key]
                                logger.info(f"✅ Successfully opened target Zarr array from nested group '{key}/{nested_key}'")
                                logger.info(f"Array shape: {target_image_arr.shape}")
                                logger.info(f"Array dtype: {target_image_arr.dtype}")
                                return target_image_arr
                            elif hasattr(nested_group[nested_key], 'keys'):
                                # Check deeper nested groups (like data/c/0/0)
                                deep_nested_group = nested_group[nested_key]
                                logger.info(f"Found deep nested group '{key}/{nested_key}'. Keys: {list(deep_nested_group.keys())}")
                                for deep_key in deep_nested_group.keys():
                                    if hasattr(deep_nested_group[deep_key], 'shape'):
                                        target_image_arr = deep_nested_group[deep_key]
                                        logger.info(f"✅ Successfully opened target Zarr array from deep nested group '{key}/{nested_key}/{deep_key}'")
                                        logger.info(f"Array shape: {target_image_arr.shape}")
                                        logger.info(f"Array dtype: {target_image_arr.dtype}")
                                        return target_image_arr
                                    elif hasattr(deep_nested_group[deep_key], 'keys'):
                                        # Check even deeper nested groups (like data/c/0/0/100)
                                        deeper_nested_group = deep_nested_group[deep_key]
                                        logger.info(f"Found deeper nested group '{key}/{nested_key}/{deep_key}'. Keys: {list(deeper_nested_group.keys())}")
                                        # For this level, we'll use the first available key as a sample
                                        if deeper_nested_group.keys():
                                            sample_key = list(deeper_nested_group.keys())[0]
                                            sample_group = deeper_nested_group[sample_key]
                                            if hasattr(sample_group, 'shape'):
                                                target_image_arr = sample_group
                                                logger.info(f"✅ Successfully opened target Zarr array from deeper nested group '{key}/{nested_key}/{deep_key}/{sample_key}'")
                                                logger.info(f"Array shape: {target_image_arr.shape}")
                                                logger.info(f"Array dtype: {target_image_arr.dtype}")
                                                return target_image_arr
                                            elif hasattr(sample_group, 'keys'):
                                                # Check even deeper nested groups (like data/c/0/0/100/0)
                                                even_deeper_nested_group = sample_group
                                                logger.info(f"Found even deeper nested group '{key}/{nested_key}/{deep_key}/{sample_key}'. Keys: {list(even_deeper_nested_group.keys())}")
                                                # For this level, we'll use the first available key as a sample
                                                if even_deeper_nested_group.keys():
                                                    even_sample_key = list(even_deeper_nested_group.keys())[0]
                                                    even_sample_group = even_deeper_nested_group[even_sample_key]
                                                    if hasattr(even_sample_group, 'shape'):
                                                        target_image_arr = even_sample_group
                                                        logger.info(f"✅ Successfully opened target Zarr array from even deeper nested group '{key}/{nested_key}/{deep_key}/{sample_key}/{even_sample_key}'")
                                                        logger.info(f"Array shape: {target_image_arr.shape}")
                                                        logger.info(f"Array dtype: {target_image_arr.dtype}")
                                                        return target_image_arr
                
                logger.error(f"No array found in 'data' group. Available keys: {list(data_group.keys())}")
                return None
        else:
            logger.error(f"No 'data' group found in Zarr group. Available keys: {list(zarr_group.keys())}")
            return None
=======
    channel_map = {}
    root_store = None
    root_group = None
    try:
        logger.info("Attempting to create S3FileSystem...")
        s3_local = s3fs.S3FileSystem(anon=True)
        logger.info("S3FileSystem created successfully.")
        
        logger.info(f"Attempting to create S3Map for root: {ZARR_BASE_URL}")
        root_store = s3fs.S3Map(root=ZARR_BASE_URL, s3=s3_local, check=False)
        logger.info("S3Map created successfully.")

        logger.info("Attempting to open root Zarr group...")
        root_group = pyzarr.open_consolidated(store=root_store) if '.zmetadata' in root_store else pyzarr.open_group(store=root_store, mode='r')
        logger.info(f"Root group opened successfully. Type: {type(root_group)}")

        # Access OME metadata: Look inside the image group (e.g., '0')
        omero_meta = None
        image_group_key = '0'
        logger.info(f"Checking for image group '{image_group_key}'...")
        if root_group and image_group_key in root_group:
            image_group = root_group[image_group_key]
            logger.info(f"Image group '{image_group_key}' found. Checking for 'omero' in its attributes...")
            if hasattr(image_group, 'attrs') and 'omero' in image_group.attrs:
                omero_meta = image_group.attrs['omero']
                logger.info(f"Found 'omero' metadata in image group '{image_group_key}' attributes.")
            else:
                 logger.warning(f"Could not find 'omero' metadata in image group '{image_group_key}' attributes.")
        else:
             logger.warning(f"Image group '{image_group_key}' not found in root group.")

        # Now check the extracted omero_meta for channels
        if omero_meta and 'channels' in omero_meta:
            logger.info(f"Found {len(omero_meta['channels'])} channels in metadata.")
            for i, channel_info in enumerate(omero_meta['channels']): 
                channel_map[str(i)] = channel_info.get('label', f'Channel {i}') 
            logger.info(f" Successfully extracted channel names: {channel_map}")
            return jsonify(channel_map)
        else:
            logger.warning("Could not find valid 'omero' metadata with 'channels'. Returning 404.")
            return jsonify({"error": "Channel metadata ('omero' with 'channels') not found in Zarr store"}), 404

    except Exception as e:
        logger.error(f" Failed during channel name retrieval: {e}", exc_info=True)
        logger.error(f"State at error: s3_local={'Exists' if s3_local else 'None'}, root_store={'Exists' if root_store else 'None'}, root_group={'Exists' if root_group else 'None'}")
        return jsonify({"error": f"Failed to read channel names: {e}"}), 500

# === STANDARD VITESSCE CONFIG GENERATOR ===
>>>>>>> parent of 4025829 (cleaner code)

def generate_vitessce_config():
    """Generate Vitessce configuration in Python"""
    
    # Channel configuration
    channels = [
        {'id': 0, 'name': "CD31", 'color': [0, 255, 0], 'window': [300, 20000], 'targetC': 19},      # Green
        {'id': 1, 'name': "CD20", 'color': [255, 255, 0], 'window': [1000, 7000], 'targetC': 27},    # Yellow
        {'id': 2, 'name': "CD11b", 'color': [255, 0, 255], 'window': [700, 6000], 'targetC': 37},    # Magenta
        {'id': 3, 'name': "CD4", 'color': [0, 255, 255], 'window': [1638, 10000], 'targetC': 25},    # Cyan
        {'id': 4, 'name': "CD11c", 'color': [128, 0, 128], 'window': [370, 1432], 'targetC': 42}     # Purple
    ]

    # Build coordination space
    coordination_space = {
        'dataset': {"A": "bv"},
        'imageChannel': {},
        'imageLayer': {"init_bv_image_0": "__dummy__"},
        'metaCoordinationScopes': {
            "A": {'obsType': "A"},
            "init_bv_image_0": {
                'imageLayer': ["init_bv_image_0"],
                'spatialRenderingMode': "init_bv_image_0",
                'spatialTargetT': "init_bv_image_0",
                'spatialTargetX': "init_bv_image_0",
                'spatialTargetY': "init_bv_image_0",
                'spatialTargetZ': "init_bv_image_0",
                'spatialZoom': "init_bv_image_0"
            }
<<<<<<< HEAD
            
        except Exception as read_error:
            logger.error(f"[Heatmap] Error reading data slice: {str(read_error)}")
            return {'error': f'Error reading data slice: {str(read_error)}'}
            
    except Exception as e:
        logger.error(f"[Heatmap] Unexpected Error: {e}", exc_info=True)
        return {'error': f'Unexpected error during heatmap calculation: {e}'}

# Helper function for normalization
def normalize_array(arr):
    """Normalizes a numpy array to the range [0, 1]."""
    min_val = np.min(arr)
    max_val = np.max(arr)
    if max_val == min_val:
        # Handle constant array case (avoid division by zero)
        # Return array of zeros or maybe scaled based on the constant value?
        # Returning zeros is common for visualization range mapping.
        return np.zeros_like(arr, dtype=np.float32)
    else:
        return (arr - min_val) / (max_val - min_val)

def calculate_rgb_interaction_heatmap_py(zarr_array, roi_z, roi_y, roi_x, projection_type='sum'):
    if zarr_array is None:
        return {'error': 'Zarr array is None.'}
    valid_projection_types = ['sum', 'mean', 'max']
    if projection_type not in valid_projection_types:
        return {'error': f"Invalid projection_type '{projection_type}'. Must be one of {valid_projection_types}"}
    try:
        if zarr_array.ndim != 5:
            logger.warning(f"[Interaction Heatmap] Expected 5D array (t,c,z,y,x), but got {zarr_array.ndim}D. Proceeding cautiously.")
        
        # Define channel groups and their ranges - updated for new interactions
        channel_groups = {
            1: [4, 0],       # group 1: CD20 + CD31 (B-cell infiltration)
            2: [3, 0],       # group 2: CD4 + CD31 (T-cell maturation)
            3: [1, 5],       # group 3: CD11b + CD11c (Inflammatory zone)
            4: [1, 2]        # group 4: CD11b + Catalase (Oxidative stress regulation)
        }
        
        # Define channel ranges
        channel_ranges = {
            0: [300, 20000],     # CD31
            4: [1000, 7000],     # CD20
            1: [700, 6000],      # CD11b
            3: [1638, 10000],    # CD4
            2: [1638, 7000],     # Catalase
            5: [370, 1432]       # CD11c
        }
        
        logger.info(f"Processing channel groups: {channel_groups}")
        
        channel_axis = 1
        for group_val, channels in channel_groups.items():
            for ch_idx in channels:
                if not (0 <= ch_idx < zarr_array.shape[channel_axis]):
                    return {'error': f'Invalid channel_index {ch_idx} in group {group_val}. Must be between 0 and {zarr_array.shape[channel_axis] - 1}.'}
        
        max_z_arr, max_y_arr, max_x_arr = zarr_array.shape[2:]
        if not (0 <= roi_z[0] < roi_z[1] <= max_z_arr and 0 <= roi_y[0] < roi_y[1] <= max_y_arr and 0 <= roi_x[0] < roi_x[1] <= max_x_arr):
            return {'error': f'ROI Z{roi_z}, Y{roi_y}, X{roi_x} is out of bounds for array shape Z{max_z_arr}, Y{max_y_arr}, X{max_x_arr}.'}
        
        total_y_height_in_zarr = zarr_array.shape[3]
        zarr_slice_y_start = total_y_height_in_zarr - roi_y[1]
        zarr_slice_y_end = total_y_height_in_zarr - roi_y[0]
        zarr_slice_y_start = max(0, zarr_slice_y_start)
        zarr_slice_y_end = min(total_y_height_in_zarr, zarr_slice_y_end)
        
        if zarr_slice_y_start >= zarr_slice_y_end and not (roi_y[0] == 0 and roi_y[1] == total_y_height_in_zarr):
            return {'error': f'Transformed Y ROI resulted in invalid slice: [{zarr_slice_y_start}, {zarr_slice_y_end}). Original roi_y: {roi_y}, Zarr Y height: {total_y_height_in_zarr}'}
        
        group_maps = {}
        for group_val, channels in channel_groups.items():
            logger.info(f"\nProcessing group {group_val} with channels {channels}")
            channel_heatmaps = []
            channel_stats = []
            
            for ch_idx in channels:
                logger.info(f"\n  Processing channel {ch_idx}")
                
                # Step 1: Get the maximum value for this channel from the ROI only
                roi_channel_slice = (
                    slice(0, 1),
                    slice(ch_idx, ch_idx + 1),
                    slice(roi_z[0], roi_z[1]),  # Use ROI Z range
                    slice(zarr_slice_y_start, zarr_slice_y_end),
                    slice(roi_x[0], roi_x[1])
                )
                roi_channel_data = zarr_array[roi_channel_slice]
                
                # Apply channel-specific range filtering to ROI data
                if ch_idx in channel_ranges:
                    min_range, max_range = channel_ranges[ch_idx]
                    roi_channel_data = np.clip(roi_channel_data, min_range, max_range)
                
                # Get the maximum value from the ROI for this channel
                roi_max_val = np.max(roi_channel_data)
                logger.info(f"  Channel {ch_idx} ROI max value: {roi_max_val:.3f}")
                
                # Use the same ROI data for processing
                data_roi = roi_channel_data
                
                # Step 2: Normalize ROI data using the ROI maximum for this channel
                data_roi = data_roi / roi_max_val
                
                # Step 3: Calculate summation over Z for each x,y position
                if projection_type == 'sum':
                    heatmap_2d = np.sum(data_roi, axis=2)
                elif projection_type == 'mean':
                    heatmap_2d = np.mean(data_roi, axis=2)
                elif projection_type == 'max':
                    heatmap_2d = np.max(data_roi, axis=2)
                heatmap_2d = np.squeeze(heatmap_2d, axis=(0, 1))
                
                # Apply threshold - set values below 0.1 to 0
                min_threshold = 0.1
                heatmap_2d[heatmap_2d < min_threshold] = 0
                
                # Log stats after processing
                logger.info(f"  After processing:")
                logger.info(f"    Range: [{np.min(heatmap_2d):.3f}, {np.max(heatmap_2d):.3f}]")
                logger.info(f"    Mean: {np.mean(heatmap_2d):.3f}")
                logger.info(f"    Values near 1 (>0.9): {np.sum(heatmap_2d > 0.9)}")
                logger.info(f"    Non-zero values: {np.sum(heatmap_2d > 0)}")
                
                channel_heatmaps.append(heatmap_2d)
                channel_stats.append({
                    'max': np.max(heatmap_2d),
                    'mean': np.mean(heatmap_2d),
                    'non_zero': np.sum(heatmap_2d > 0)
                })
            
            # Step 4: Calculate interaction as summation of normalized channels for each x,y
            # Stack all channel heatmaps
            stacked_heatmaps = np.stack(channel_heatmaps)
            
            # Calculate summation along channel axis (axis=0) for each x,y position
            interaction = np.sum(stacked_heatmaps, axis=0)
            
            # Step 5: Final normalization of interaction values to [0, 1] range
            min_val = np.min(interaction)
            max_val = np.max(interaction)
            logger.info(f"\nGroup {group_val} interaction before normalization:")
            logger.info(f"  Min value: {min_val:.6f}")
            logger.info(f"  Max value: {max_val:.6f}")
            logger.info(f"  Range: {max_val - min_val:.6f}")
            
            if max_val > min_val:
                # Simple min-max normalization to scale values between 0 and 1
                # This ensures the minimum value becomes 0 and maximum value becomes 1
                interaction = (interaction - min_val) / (max_val - min_val)
                
                logger.info(f"  After min-max normalization:")
                logger.info(f"    Min value: {np.min(interaction):.6f} (was {min_val:.8f})")
                logger.info(f"    Max value: {np.max(interaction):.6f} (was {max_val:.8f})")
                logger.info(f"    Mean value: {np.mean(interaction):.6f}")
            else:
                interaction = np.zeros_like(interaction)
                logger.info(f"  All values are the same, setting to zero")
            
            # Log statistics about the interaction values
            non_zero_mask = interaction > 0
            if np.any(non_zero_mask):
                non_zero_values = interaction[non_zero_mask]
                logger.info(f"\nGroup {group_val} interaction statistics:")
                logger.info(f"  Channel stats:")
                for i, stats in enumerate(channel_stats):
                    logger.info(f"    Channel {channels[i]}:")
                    logger.info(f"      Max: {stats['max']:.6f}")
                    logger.info(f"      Mean: {stats['mean']:.6f}")
                    logger.info(f"      Non-zero: {stats['non_zero']}")
                logger.info(f"  Interaction stats:")
                logger.info(f"    Total pixels: {interaction.size}")
                logger.info(f"    Non-zero pixels: {np.sum(non_zero_mask)}")
                logger.info(f"    Values near 1 (>0.9): {np.sum(non_zero_values > 0.9)}")
                logger.info(f"    Values near 0 (<0.1): {np.sum(non_zero_values < 0.1)}")
                logger.info(f"    Mean value: {np.mean(non_zero_values):.6f}")
                logger.info(f"    Median value: {np.median(non_zero_values):.6f}")
                logger.info(f"    Max value: {np.max(non_zero_values):.6f}")
                logger.info(f"    Min value: {np.min(non_zero_values):.6f}")
                
                # Print to terminal for debugging
                print(f"\n=== INTERACTION GROUP {group_val} DEBUG ===")
                print(f"Max value: {np.max(interaction):.8f}")
                print(f"Min value: {np.min(interaction):.8f}")
                print(f"Mean value: {np.mean(interaction):.8f}")
                print(f"95th percentile: {np.percentile(interaction, 95):.8f}")
                print(f"99th percentile: {np.percentile(interaction, 99):.8f}")
                print(f"Non-zero pixels: {np.sum(non_zero_mask)} / {interaction.size}")
                print(f"==========================================\n")
            
            group_maps[f'group_{group_val}'] = interaction.tolist()
        
        height, width = next(iter(group_maps.values())).__len__(), next(iter(group_maps.values()))[0].__len__()
        logger.info(f"\nAll groups processed. Final heatmap dimensions: {height}x{width}")
        
        return {
            'heatmaps': group_maps,
            'shape': [height, width]
        }
    except Exception as e:
        logger.error(f"[Interaction Heatmap] Error: {e}", exc_info=True)
        return {'error': f'Error calculating interaction heatmap: {e}'}

@app.route('/api/top_roi_scores_<interaction_type>', methods=['GET'])
def serve_top_roi_scores(interaction_type):
    """Serve top ROI scores for a specific interaction type"""
    logger.info(f"Request received for top ROI scores with interaction_type: '{interaction_type}'")
    try:
        # Decode the interaction type and convert to filename format
        from urllib.parse import unquote
        decoded_interaction_type = unquote(interaction_type)
        filename = f"all_roi_scores_{decoded_interaction_type}.json"
        logger.info(f"Looking for file: {filename}")
        roi_path = Path(__file__).parent / "output" / filename
        
        if not roi_path.exists():
            logger.warning(f"Top ROI scores file not found: {filename}")
            return jsonify({"error": f"Top ROI scores file not found: {filename}"}), 404

        with open(roi_path, 'r') as f:
            roi_data = json.load(f)
            
        return jsonify(roi_data)
    except Exception as e:
        logger.error(f"Error serving top ROI scores for {interaction_type}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve top ROI scores for {interaction_type}: {e}"}), 500

@app.route('/api/analyze_heatmaps', methods=['POST'])
def analyze_heatmaps():
    """API endpoint to analyze heatmaps for specific channels in a given ROI."""
    data = request.get_json()
    if not data:
        logger.error("No data provided in request")
        return jsonify({'error': 'No data provided'}), 400
    
    roi = data.get('roi')
    if not roi or not all(k in roi for k in ['xMin', 'xMax', 'yMin', 'yMax', 'zMin', 'zMax']):
        logger.error(f"Invalid ROI format: {roi}")
        return jsonify({'error': 'Invalid ROI format'}), 400

        channels = data.get('channels', ['CD31', 'CD11b', 'Catalase', 'CD4', 'CD20', 'CD11c'])
        if not channels:
            logger.error("No channels specified")
            return jsonify({'error': 'No channels specified'}), 400
        
        roi_info = data.get('roiInfo', {})
        
        # Get the Zarr array
        zarr_array = open_target_zarr_array()
        if zarr_array is None:
            logger.error("Failed to open Zarr array")
            return jsonify({'error': 'Failed to open Zarr array'}), 500
        
        logger.info(f"Processing ROI: {roi}")
        logger.info(f"Processing channels: {channels}")
        logger.info(f"Zarr array shape: {zarr_array.shape}")
        
        # Validate ROI values
        try:
            roi_values = {
                'zMin': int(roi['zMin']),
                'zMax': int(roi['zMax']),
                'yMin': int(roi['yMin']),
                'yMax': int(roi['yMax']),
                'xMin': int(roi['xMin']),
                'xMax': int(roi['xMax'])
=======
        },
        'metaCoordinationScopesBy': {
            "A": {},
            "init_bv_image_0": {
                'imageChannel': {
                    'spatialChannelColor': {},
                    'spatialChannelOpacity': {},
                    'spatialChannelVisible': {},
                    'spatialChannelWindow': {},
                    'spatialTargetC': {}
                },
                'imageLayer': {
                    'imageChannel': {"init_bv_image_0": []},
                    'photometricInterpretation': {"init_bv_image_0": "init_bv_image_0"},
                    'spatialLayerOpacity': {"init_bv_image_0": "init_bv_image_0"},
                    'spatialLayerVisible': {"init_bv_image_0": "init_bv_image_0"},
                    'spatialTargetResolution': {"init_bv_image_0": "init_bv_image_0"}
                }
            }
        },
        'obsType': {
            "A": "ROI_B-cell",
            "B": "ROI_Inflammatory", 
            "C": "ROI_T-cell",
            "D": "ROI_Oxidative"
        },
        'obsColorEncoding': {
            "A": "cellSetSelection",
            "B": "cellSetSelection",
            "C": "cellSetSelection",
            "D": "cellSetSelection"
        },
        'photometricInterpretation': {"init_bv_image_0": "BlackIsZero"},
        'spatialChannelColor': {},
        'spatialChannelOpacity': {},
        'spatialChannelVisible': {},
        'spatialChannelWindow': {},
        'spatialLayerOpacity': {"init_bv_image_0": 1.0},
        'spatialLayerVisible': {"init_bv_image_0": True},
        'spatialRenderingMode': {"init_bv_image_0": "3D"},
        'spatialTargetC': {},
        'spatialTargetResolution': {"init_bv_image_0": 3},
        'spatialTargetT': {"init_bv_image_0": 0},
        'spatialTargetX': {"init_bv_image_0": 5454},
        'spatialTargetY': {"init_bv_image_0": 2754},
        'spatialTargetZ': {"init_bv_image_0": 0},
        'spatialZoom': {"init_bv_image_0": -3.5},
        'spatialSegmentationLayer': {
            "A": {
                "radius": 200,
                "stroked": True,
                "visible": True,
                "opacity": 0.2,
                "color": [255, 100, 100]  # Red for B-cell infiltration
            },
            "B": {
                "radius": 200,
                "stroked": True,
                "visible": True,
                "opacity": 0.2,
                "color": [0, 255, 0]  # Green for Inflammatory zone
            },
            "C": {
                "radius": 200,
                "stroked": True,
                "visible": True,
                "opacity": 0.2,
                "color": [0, 0, 255]  # Blue for T-cell entry site
            },
            "D": {
                "radius": 200,
                "stroked": True,
                "visible": True,
                "opacity": 0.2,
                "color": [255, 255, 0]  # Yellow for Oxidative stress niche
>>>>>>> parent of 4025829 (cleaner code)
            }
        }
    }

    # Add channel-specific coordination values
    for i, channel in enumerate(channels):
        ch_id = f'init_bv_image_{i}'
        coordination_space['imageChannel'][ch_id] = "__dummy__"
        coordination_space['spatialChannelColor'][ch_id] = channel['color']
        coordination_space['spatialChannelOpacity'][ch_id] = 1.0
        coordination_space['spatialChannelVisible'][ch_id] = True
        coordination_space['spatialChannelWindow'][ch_id] = channel['window']
        coordination_space['spatialTargetC'][ch_id] = channel['targetC']
        
        # Add to meta coordination scopes
        for key in ['spatialChannelColor', 'spatialChannelOpacity', 'spatialChannelVisible', 'spatialChannelWindow', 'spatialTargetC']:
            coordination_space['metaCoordinationScopesBy']['init_bv_image_0']['imageChannel'][key][ch_id] = ch_id

    config = {
        'version': '1.0.16',
        'name': 'BioMedVis Challenge',
        'description': 'ROI annotations for the BioMedVis Challenge',
        'datasets': [{
            'uid': 'bv',
            'name': 'Blood Vessel',
            'files': [
                {
                    'fileType': 'image.ome-zarr',
                    'url': 'https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0',
                },
                {
                    'fileType': 'obsSegmentations.json',
                    'url': 'http://localhost:5000/api/roi_segmentation_B-cell_infiltration.json',
                    'coordinationValues': {
                        'obsType': 'ROI_B-cell',
                    },
                },
                {
                    'fileType': 'obsSegmentations.json',
                    'url': 'http://localhost:5000/api/roi_segmentation_Inflammatory_zone.json',
                    'coordinationValues': {
                        'obsType': 'ROI_Inflammatory',
                    },
                },
                {
                    'fileType': 'obsSegmentations.json',
                    'url': 'http://localhost:5000/api/roi_segmentation_T-cell_entry_site.json',
                    'coordinationValues': {
                        'obsType': 'ROI_T-cell',
                    },
                },
                {
                    'fileType': 'obsSegmentations.json',
                    'url': 'http://localhost:5000/api/roi_segmentation_Oxidative_stress_niche.json',
                    'coordinationValues': {
                        'obsType': 'ROI_Oxidative',
                    },
                }
            ]
        }],
        'initStrategy': 'auto',
        'coordinationSpace': coordination_space,
        'layout': [
            {
                'component': 'spatialBeta',
                'coordinationScopes': {
                    'dataset': "A",
                    'metaCoordinationScopes': ["init_bv_image_0", "A"],
                    'metaCoordinationScopesBy': ["init_bv_image_0", "A"],
                    'spatialSegmentationLayer': ["A", "B", "C", "D"],
                    'obsType': ["A", "B", "C", "D"],
                    'obsColorEncoding': ["A", "B", "C", "D"]
                },
                'x': 0, 'y': 0, 'w': 6, 'h': 12
            },
            {
                'component': 'layerControllerBeta',
                'coordinationScopes': {
                    'dataset': "A",
                    'metaCoordinationScopes': ["init_bv_image_0", "A"],
                    'metaCoordinationScopesBy': ["init_bv_image_0", "A"],
                    'spatialSegmentationLayer': ["A", "B", "C", "D"],
                    'obsType': ["A", "B", "C", "D"]
                },
                'x': 6, 'y': 0, 'w': 6, 'h': 12
            }
        ]
    }

    return config

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get the standard Vitessce config using Python generator"""
    logger.info("Request received for /api/config [GET]")
    
    try:
        config = generate_vitessce_config()
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Error generating config: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate config: {e}"}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update the Vitessce config based on selected interaction types"""
    logger.info("Request received for /api/config [POST]")
    
    try:
        data = request.get_json()
        selected_groups = data.get('selectedGroups', [])
        
        logger.info(f"Updating config with selected groups: {selected_groups}")
        
        # Generate config based on selected groups
        config = generate_vitessce_config()
        return jsonify(config)
        
    except Exception as e:
        logger.error(f"Error updating config: {e}", exc_info=True)
        return jsonify({"error": f"Failed to update config: {e}"}), 500

@app.route('/api/roi_segmentation_B-cell_infiltration.json', methods=['GET'])
def get_roi_segmentation_b_cell():
    """Serve the B-cell infiltration ROI segmentation JSON file"""
    logger.info("Request received for /api/roi_segmentation_B-cell_infiltration.json [GET]")
    
    try:
        roi_file_path = Path(__file__).parent / 'output' / 'roi_segmentation_B-cell_infiltration.json'
        
        if not roi_file_path.exists():
            logger.error(f"B-cell infiltration ROI segmentation file not found: {roi_file_path}")
            return jsonify({"error": "B-cell infiltration ROI segmentation file not found"}), 404
        
        with open(roi_file_path, 'r') as f:
            roi_data = json.load(f)
        
        return jsonify(roi_data)
        
    except Exception as e:
        logger.error(f"Error serving B-cell infiltration ROI segmentation: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve B-cell infiltration ROI segmentation: {e}"}), 500

@app.route('/api/roi_segmentation_T-cell_entry_site.json', methods=['GET'])
def get_roi_segmentation_t_cell():
    """Serve the T-cell entry site ROI segmentation JSON file"""
    logger.info("Request received for /api/roi_segmentation_T-cell_entry_site.json [GET]")
    
    try:
        roi_file_path = Path(__file__).parent / 'output' / 'roi_segmentation_T-cell_entry_site.json'
        
        if not roi_file_path.exists():
            logger.error(f"T-cell entry site ROI segmentation file not found: {roi_file_path}")
            return jsonify({"error": "T-cell entry site ROI segmentation file not found"}), 404
        
        with open(roi_file_path, 'r') as f:
            roi_data = json.load(f)
        
        return jsonify(roi_data)
        
    except Exception as e:
        logger.error(f"Error serving T-cell entry site ROI segmentation: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve T-cell entry site ROI segmentation: {e}"}), 500

@app.route('/api/roi_segmentation_Inflammatory_zone.json', methods=['GET'])
def get_roi_segmentation_inflammatory():
    """Serve the Inflammatory zone ROI segmentation JSON file"""
    logger.info("Request received for /api/roi_segmentation_Inflammatory_zone.json [GET]")
    
    try:
        roi_file_path = Path(__file__).parent / 'output' / 'roi_segmentation_Inflammatory_zone.json'
        
        if not roi_file_path.exists():
            logger.error(f"Inflammatory zone ROI segmentation file not found: {roi_file_path}")
            return jsonify({"error": "Inflammatory zone ROI segmentation file not found"}), 404
        
        with open(roi_file_path, 'r') as f:
            roi_data = json.load(f)
        
        return jsonify(roi_data)
        
    except Exception as e:
        logger.error(f"Error serving Inflammatory zone ROI segmentation: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve Inflammatory zone ROI segmentation: {e}"}), 500

@app.route('/api/roi_segmentation_Oxidative_stress_niche.json', methods=['GET'])
def get_roi_segmentation_oxidative():
    """Serve the Oxidative stress niche ROI segmentation JSON file"""
    logger.info("Request received for /api/roi_segmentation_Oxidative_stress_niche.json [GET]")
    
    try:
        roi_file_path = Path(__file__).parent / 'output' / 'roi_segmentation_Oxidative_stress_niche.json'
        
        if not roi_file_path.exists():
            logger.error(f"Oxidative stress niche ROI segmentation file not found: {roi_file_path}")
            return jsonify({"error": "Oxidative stress niche ROI segmentation file not found"}), 404
        
        with open(roi_file_path, 'r') as f:
            roi_data = json.load(f)
        
        return jsonify(roi_data)
        
    except Exception as e:
        logger.error(f"Error serving Oxidative stress niche ROI segmentation: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve Oxidative stress niche ROI segmentation: {e}"}), 500

@app.route('/api/roi_shapes', methods=['GET'])
def serve_roi_shapes():
    try:
        roi_path = Path(__file__).parent / "output" / "roi_rectangles.geojson"
        if not roi_path.exists():
            logger.warning("ROI shapes file not found.")
            return jsonify({"error": "ROI shapes not found"}), 404

        with open(roi_path, 'r') as f:
            roi_data = json.load(f)
        
        # Transform the data to match frontend expectations
        if 'features' in roi_data:
            for feature in roi_data['features']:
                if 'properties' in feature:
                    # Convert 'interaction' string to 'interactions' array
                    if 'interaction' in feature['properties']:
                        feature['properties']['interactions'] = [feature['properties']['interaction']]
                        # Keep the original 'interaction' field for backward compatibility
                    
                    # Ensure 'name' field exists
                    if 'name' not in feature['properties'] and 'id' in feature['properties']:
                        feature['properties']['name'] = feature['properties']['id']
            
        return jsonify(roi_data)
    except Exception as e:
        logger.error(f"Error serving ROI shapes: {e}", exc_info=True)
        return jsonify({"error": f"Failed to serve ROI shapes: {e}"}), 500

@app.route('/api/roi_rectangles_annotation', methods=['GET'])
def serve_roi_rectangles_annotation():
    try:
        roi_path = Path(__file__).parent / "output" / "roi_rectangles_annotation.json"
        if not roi_path.exists():
            logger.warning("ROI rectangles annotation file not found.")
            return jsonify({"error": "ROI rectangles annotation not found"}), 404

        with open(roi_path, 'r') as f:
            roi_data = json.load(f)

        return jsonify(roi_data)
    except Exception as e:
        logger.error(f"Error serving ROI rectangles annotation: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 