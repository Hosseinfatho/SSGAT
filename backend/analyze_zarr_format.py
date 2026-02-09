


#!/usr/bin/env python3
"""
Analyze the exact format of Zarr files to understand structure for ROI overlay
"""

import zarr
import json
import numpy as np
from pathlib import Path

def analyze_zarr_format(zarr_path, output_file=None):
    """Analyze the exact format of a Zarr file"""
    print(f"\n Analyzing Zarr format: {zarr_path}")
    print("="*60)
    
    try:
        z = zarr.open(str(zarr_path), mode='r')
        
        analysis = {
            "file_path": str(zarr_path),
            "root_attributes": dict(z.attrs) if hasattr(z, 'attrs') else {},
            "structure": {}
        }
        
        def analyze_group(group, path="", level=0):
            indent = "  " * level
            group_info = {
                "type": "group",
                "attributes": dict(group.attrs) if hasattr(group, 'attrs') else {},
                "arrays": {},
                "subgroups": {}
            }
            
            print(f"{indent}📁 {path or 'root'}")
            
            # Print attributes
            if group_info["attributes"]:
                print(f"{indent}  📋 Attributes:")
                for key, value in group_info["attributes"].items():
                    print(f"{indent}    {key}: {value}")
            
            # Analyze arrays and subgroups
            if hasattr(group, 'keys'):
                for key in group.keys():
                    item = group[key]
                    item_path = f"{path}/{key}" if path else key
                    
                    if hasattr(item, 'shape'):  # It's an array
                        array_info = {
                            "shape": item.shape,
                            "dtype": str(item.dtype),
                            "chunks": item.chunks if hasattr(item, 'chunks') else None,
                            "attributes": dict(item.attrs) if hasattr(item, 'attrs') else {},
                            "sample_data": None
                        }
                        
                        # Get sample data
                        if item.size > 0:
                            try:
                                sample = item[:min(5, item.shape[0])]
                                if item.ndim == 1:
                                    array_info["sample_data"] = sample.tolist()
                                else:
                                    array_info["sample_data"] = sample.flatten()[:5].tolist()
                            except Exception as e:
                                array_info["sample_data"] = f"Error: {e}"
                        
                        group_info["arrays"][key] = array_info
                        
                        print(f"{indent}  📊 Array: {key}")
                        print(f"{indent}    Shape: {item.shape}")
                        print(f"{indent}    Dtype: {item.dtype}")
                        print(f"{indent}    Chunks: {item.chunks if hasattr(item, 'chunks') else 'N/A'}")
                        if array_info["sample_data"]:
                            print(f"{indent}    Sample: {array_info['sample_data']}")
                    
                    elif hasattr(item, 'keys'):  # It's a group
                        subgroup_info = analyze_group(item, item_path, level + 1)
                        group_info["subgroups"][key] = subgroup_info
            
            return group_info
        
        analysis["structure"] = analyze_group(z)
        
        # Save analysis to file
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"\n💾 Analysis saved to: {output_file}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing {zarr_path}: {e}")
        return None

def compare_zarr_formats():
    """Compare different Zarr files to understand the format"""
    output_dir = Path(__file__).parent / "output"
    
    # Analyze local Zarr files
    zarr_files = [
        ("test.zarr", "test_zarr_analysis.json"),
        ("roi_shapes.spatialdata.zarr", "roi_shapes_analysis.json")
    ]
    
    analyses = {}
    
    for zarr_file, output_file in zarr_files:
        zarr_path = output_dir / zarr_file
        if zarr_path.exists():
            analysis = analyze_zarr_format(zarr_path, output_file)
            if analysis:
                analyses[zarr_file] = analysis
    
    # Compare structures
    print(f"\n{'='*60}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'='*60}")
    
    for name, analysis in analyses.items():
        print(f"\n📁 {name}:")
        if "structure" in analysis and "subgroups" in analysis["structure"]:
            for group_name, group_info in analysis["structure"]["subgroups"].items():
                print(f"  📂 {group_name}/")
                if "arrays" in group_info:
                    for array_name, array_info in group_info["arrays"].items():
                        print(f"    📊 {array_name}: {array_info['shape']} ({array_info['dtype']})")

def create_template_from_analysis():
    """Create a template based on the analysis"""
    print(f"\n{'='*60}")
    print("📝 TEMPLATE FOR ROI OVERLAY")
    print(f"{'='*60}")
    
    template = {
        "description": "Template for creating ROI overlay Zarr file",
        "structure": {
            "root": {
                "attributes": {
                    "spatialdata_attrs": {
                        "spatialdata_software_version": "0.4.0",
                        "version": "0.1"
                    }
                },
                "groups": {
                    "shapes": {
                        "groups": {
                            "roi_circles": {
                                "attributes": {
                                    "axes": ["x", "y"],
                                    "coordinateTransformations": [
                                        {
                                            "input": {
                                                "axes": [
                                                    {"name": "x", "type": "space", "unit": "unit"},
                                                    {"name": "y", "type": "space", "unit": "unit"}
                                                ],
                                                "name": "xy"
                                            },
                                            "output": {
                                                "axes": [
                                                    {"name": "x", "type": "space", "unit": "unit"},
                                                    {"name": "y", "type": "space", "unit": "unit"}
                                                ],
                                                "name": "global"
                                            },
                                            "type": "identity"
                                        }
                                    ],
                                    "encoding-type": "ngff:shapes",
                                    "spatialdata_attrs": {"version": "0.2"}
                                },
                                "arrays": {
                                    "x": {"shape": "(N,)", "dtype": "int64", "description": "X coordinates"},
                                    "y": {"shape": "(N,)", "dtype": "int64", "description": "Y coordinates"},
                                    "radius": {"shape": "(N,)", "dtype": "int32", "description": "Circle radius"},
                                    "roi_id": {"shape": "(N,)", "dtype": "object", "description": "ROI identifier"},
                                    "interaction": {"shape": "(N,)", "dtype": "object", "description": "ROI type"},
                                    "attention_score": {"shape": "(N,)", "dtype": "float64", "description": "Attention score"},
                                    "intensity_score": {"shape": "(N,)", "dtype": "float64", "description": "Intensity score"},
                                    "combined_score": {"shape": "(N,)", "dtype": "float64", "description": "Combined score"}
                                }
                            }
                        }
                    },
                    "table": {
                        "groups": {
                            "table": {
                                "arrays": {
                                    "x": {"shape": "(N,)", "dtype": "int64", "description": "X coordinates"},
                                    "y": {"shape": "(N,)", "dtype": "int64", "description": "Y coordinates"},
                                    "roi_id": {"shape": "(N,)", "dtype": "object", "description": "ROI identifier"},
                                    "interaction": {"shape": "(N,)", "dtype": "object", "description": "ROI type"},
                                    "attention_score": {"shape": "(N,)", "dtype": "float64", "description": "Attention score"},
                                    "intensity_score": {"shape": "(N,)", "dtype": "float64", "description": "Intensity score"},
                                    "combined_score": {"shape": "(N,)", "dtype": "float64", "description": "Combined score"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Save template
    template_file = Path(__file__).parent / "zarr_template.json"
    with open(template_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"💾 Template saved to: {template_file}")
    print("\n📋 Key points for ROI overlay:")
    print("1. Use 'shapes/roi_circles' for spatial data")
    print("2. Use 'table/table' for tabular data")
    print("3. Required arrays: x, y, radius, roi_id, interaction")
    print("4. Optional arrays: attention_score, intensity_score, combined_score")
    print("5. All arrays must have the same length (N = number of ROIs)")

if __name__ == "__main__":
    compare_zarr_formats()
    create_template_from_analysis() 