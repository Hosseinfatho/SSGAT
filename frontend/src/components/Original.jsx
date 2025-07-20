import React, { useState, useEffect, useRef } from 'react';
import { Vitessce, CoordinationType } from 'vitessce';
import ROISelector from './ROISelector';
import Plot from 'react-plotly.js';
import HeatmapResults from './HeatmapResults';

// Constants for Image Channels
const IMAGE_CHANNELS = {
  'CD31': { 'id': 'cd31', 'color': [0, 255, 0], 'window': [300, 20000], 'targetC': 19 },
  'CD20': { 'id': 'cd20', 'color': [255, 255, 0], 'window': [1000, 7000], 'targetC': 27 },
  'CD11b': { 'id': 'cd11b', 'color': [255, 0, 255], 'window': [700, 6000], 'targetC': 37 },
  'CD4': { 'id': 'cd4', 'color': [0, 255, 255], 'window': [1638, 10000], 'targetC': 25 },
  'CD11c': { 'id': 'cd11c', 'color': [128, 0, 128], 'window': [370, 1432], 'targetC': 42 }
};

// Constants for Interaction Type to ROI Mapping
const INTERACTION_TO_ROI = {
  'B-cell infiltration': {
    'file': 'roi_segmentation_B-cell_infiltration.json',
    'obsType': 'ROI_B-cell',
    'color': [255, 180, 180],  // Light Red
    'strokeWidth': 16
  },
  'Inflammatory zone': {
    'file': 'roi_segmentation_Inflammatory_zone.json',
    'obsType': 'ROI_Inflammatory',
    'color': [180, 255, 180],  // Light Green
    'strokeWidth': 16
  },
  'T-cell entry site': {
    'file': 'roi_segmentation_T-cell_entry_site.json',
    'obsType': 'ROI_T-cell',
    'color': [180, 180, 255],  // Light Blue
    'strokeWidth': 16
  },
  'Oxidative stress niche': {
    'file': 'roi_segmentation_Oxidative_stress_niche.json',
    'obsType': 'ROI_Oxidative',
    'color': [255, 255, 180],  // Light Yellow
    'strokeWidth':16
  }
};

// Simple config generation function
const generateVitessceConfig = (selectedGroups = []) => { 
  // Build coordination space
  const coordination_space = {
    'dataset': { "A": "bv" },

    'imageLayer': { "image": "image" },
    'imageChannel': {},
    'spatialChannelColor': {"A": [255, 100, 100]},
    'spatialChannelOpacity': {"image": 1 },
    'spatialChannelVisible': {},
    'spatialChannelWindow': {},
    'spatialTargetC': {},
    'spatialLayerOpacity': { "image":1.0 },
    'spatialLayerVisible': { "image": true },
    'spatialRenderingMode': { "image": "3D" },
    'spatialTargetX': { "A": 5454 },
    'spatialTargetY': { "A": 1600 },
    'spatialTargetZ': { "A": 0 },
    'spatialZoom': { "A": -3.0 },
    'spatialTargetResolution': { "image": 3 },
    'spatialTargetT': { "image": 0 },
    'photometricInterpretation': { "image": "BlackIsZero" },
    'spatialSegmentationFilled': {},
    'spatialSegmentationStrokeWidth': {},
    [CoordinationType.TOOLTIPS_VISIBLE]: {},
    'metaCoordinationScopes': {
      "metaA": {
        "imageLayer": ["image"],
        "spatialChannelVisible": ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
        "spatialChannelOpacity": ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
        "spatialChannelColor": [],
        "spatialLayerOpacity": ["image"],
        "spatialLayerVisible": ["image"],
        "spatialSegmentationFilled": [],
        "spatialSegmentationStrokeWidth": [],
        [CoordinationType.TOOLTIPS_VISIBLE]: []
      }
    },
    'metaCoordinationScopesBy': {
      "metaA": {
        "imageLayer": {
          "imageChannel": { "image": ["CD31", "CD20", "CD11b", "CD4", "CD11c"] },
          "spatialLayerVisible": { "image": "image" },
          "spatialLayerOpacity": { "image": "image" },
          "spatialRenderingMode": { "image": "3D" },
          "spatialTargetResolution": { "image": "image" },
          "spatialTargetT": { "image": "image" },
          "photometricInterpretation": { "image": "image" }
        },
        "imageChannel": {
          "spatialTargetC": {},

          "spatialChannelColor": {},
          "spatialChannelVisible": {},
          "spatialChannelOpacity": {},
          "spatialChannelWindow": {}
        }
      }
    }
  };

  // Add image channels
  Object.entries(IMAGE_CHANNELS).forEach(([chName, chProps]) => {
    coordination_space['imageChannel'][chName] = "__dummy__";
    coordination_space['spatialChannelColor'][chName] = chProps['color'];
    coordination_space['spatialChannelOpacity'][chName] = 1.0;
    coordination_space['spatialChannelVisible'][chName] = true;
    coordination_space['spatialChannelWindow'][chName] = chProps['window'];
    coordination_space['spatialTargetC'][chName] = chProps['targetC'];
    
    // Add to meta coordination scopes
    coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel']['spatialTargetC'][chName] = chName;
    coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel']['spatialChannelColor'][chName] = chName;
    coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel']['spatialChannelVisible'][chName] = chName;
    coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel']['spatialChannelOpacity'][chName] = chName;
    coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel']['spatialChannelWindow'][chName] = chName;
    
    // Add to meta coordination scopes arrays
    coordination_space['metaCoordinationScopes']['metaA']['spatialChannelColor'].push(chName);
  });

  // Build files array - start with image file
  const files = [
    {
      'fileType': 'image.ome-zarr',
      'url': 'https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0',
    }
  ];

  // Add ROI segmentation files for selected groups (simplified)
  selectedGroups.forEach(group => {
    if (INTERACTION_TO_ROI[group]) {
      const roi_info = INTERACTION_TO_ROI[group];
      const obs_type = roi_info['obsType'];
      
              // Simple coordination settings
        coordination_space['spatialSegmentationFilled'][obs_type] = false; // ROIs are hollow
        coordination_space['spatialSegmentationStrokeWidth'][obs_type] = roi_info['strokeWidth'];
        coordination_space['spatialLayerOpacity'][obs_type] = 0.5; // Set opacity to 0.5 for ROIs
        coordination_space['spatialLayerVisible'][obs_type] = true; // Make ROIs visible in layer controller
        coordination_space[CoordinationType.TOOLTIPS_VISIBLE][obs_type] = true; // Enable tooltips for ROIs
        
        // Add ROI color to spatialChannelColor
        coordination_space['spatialChannelColor'][obs_type] = roi_info['color'];
      
              // Add to meta coordination scopes (simplified)
        coordination_space['metaCoordinationScopes']['metaA']['spatialSegmentationFilled'].push(obs_type);
        coordination_space['metaCoordinationScopes']['metaA']['spatialSegmentationStrokeWidth'].push(obs_type);
        coordination_space['metaCoordinationScopes']['metaA']['spatialLayerOpacity'].push(obs_type);
        coordination_space['metaCoordinationScopes']['metaA']['spatialLayerVisible'].push(obs_type);
        coordination_space['metaCoordinationScopes']['metaA'][CoordinationType.TOOLTIPS_VISIBLE].push(obs_type);
        coordination_space['metaCoordinationScopes']['metaA']['spatialChannelColor'].push(obs_type);
      
      files.push({
        'fileType': 'obsSegmentations.json',
        'url': `http://localhost:5000/api/${roi_info["file"]}`,
        'coordinationValues': {
          'obsType': roi_info['obsType']
        }
      });
    }
  });

  const config = {
    'version': '1.0.16',
    'name': `BioMedVis Challenge - ${selectedGroups.length > 0 ? selectedGroups.join(", ") : "Image Only"}`,
    'description': `Dynamic config with selected interaction types: ${selectedGroups.length > 0 ? selectedGroups.join(", ") : "None"}`,
    'datasets': [{
      'uid': 'bv',
      'name': 'Blood Vessel',
      'files': files
    }],
    'initStrategy': 'auto',
    'coordinationSpace': coordination_space,
    'layout': [
      {
        'component': 'spatialBeta',
        'coordinationScopes': {
          'metaCoordinationScopes': ["metaA"],
          'metaCoordinationScopesBy': ["metaA"],
          'spatialTargetX': "A",
          'spatialTargetY': "A",
          'spatialTargetZ': "A",
          'spatialZoom': "A",
          'spatialTargetResolution': "image",
          'spatialTargetT': "image",
          'spatialRenderingMode': "image",
          'spatialChannelVisible': ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
          'spatialChannelOpacity': Object.keys(coordination_space['spatialChannelOpacity']),
          'spatialChannelColor': ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
          'spatialLayerOpacity': Object.keys(coordination_space['spatialLayerOpacity']),
          'spatialLayerVisible': Object.keys(coordination_space['spatialLayerVisible']),
          'spatialSegmentationFilled': Object.keys(coordination_space['spatialSegmentationFilled']),
          'spatialSegmentationStrokeWidth': Object.keys(coordination_space['spatialSegmentationStrokeWidth']),
          [CoordinationType.TOOLTIPS_VISIBLE]: Object.keys(coordination_space[CoordinationType.TOOLTIPS_VISIBLE])
        },
        'x': 2, 'y': 0, 'w': 10, 'h': 12
      },
      {
        'component': 'layerControllerBeta',
        'coordinationScopes': {
          'metaCoordinationScopes': ["metaA"],
          'metaCoordinationScopesBy': ["metaA"],
          'spatialTargetX': "A",
          'spatialTargetY': "A",
          'spatialTargetZ': "A",
          'spatialZoom': "A",
          'spatialTargetResolution': "image",
          'spatialTargetT': "image",
          'spatialRenderingMode': "image",
          'spatialChannelVisible': ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
          'spatialChannelOpacity': Object.keys(coordination_space['spatialChannelOpacity']),
          'spatialChannelColor': ["CD31", "CD20", "CD11b", "CD4", "CD11c"],
          'spatialLayerOpacity': Object.keys(coordination_space['spatialLayerOpacity']),
          'spatialLayerVisible': Object.keys(coordination_space['spatialLayerVisible']),
          'spatialSegmentationFilled': Object.keys(coordination_space['spatialSegmentationFilled']),
          'spatialSegmentationStrokeWidth': Object.keys(coordination_space['spatialSegmentationStrokeWidth']),
          [CoordinationType.TOOLTIPS_VISIBLE]: Object.keys(coordination_space[CoordinationType.TOOLTIPS_VISIBLE])
        },
        'x': 0, 'y': 0, 'w': 2, 'h': 8
      }
    ]
  };

  return config;
};

const MainView = ({ onSetView }) => {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [prevCellSetSelection, setPrevCellSetSelection] = useState(null);

  const [heatmapResults, setHeatmapResults] = useState({});
  const [interactionHeatmapResult, setInteractionHeatmapResult] = useState(null);
  const [activeGroups, setActiveGroups] = useState({
    1: true,
    2: true,
    3: true,
    4: true
  });
  const [configKey, setConfigKey] = useState(0);
  const [rois, setRois] = useState([]);
  const [selectedCircle, setSelectedCircle] = useState(null);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const vitessceRef = useRef(null);

  const groupColors = {
    1: '#e41a1c',  // Red
    2: '#377eb8',  // Blue
    3: '#4daf4a',  // Green
    4: '#984ea3'   // Purple
  };

  const groupNames = {
    1: 'Endothelial-immune interface',
    2: 'ROS detox, immune stress',
    3: 'T/B cell recruitment',
    4: 'T-B collaboration'
  };

  // Generate config locally
  const generateConfig = (groups = []) => {
    const newConfig = generateVitessceConfig(groups);
    setConfig(newConfig);
    setConfigKey(prev => prev + 1); // Force re-render
    
    // Store config globally for debugging
    window.lastConfig = newConfig;
    console.log('Generated config and stored in window.lastConfig:', newConfig);
    
    // Send config to backend
    fetch('http://localhost:5000/api/updateconfig', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newConfig)
    })
    .then(response => response.json())
    .then(data => {
      console.log('Config sent to backend:', data);
    })
    .catch(error => {
      console.error('Error sending config to backend:', error);
    });
  };

  // Generate initial config on component mount
  useEffect(() => {
    generateConfig([]);
  }, []);

  // Regenerate config when selectedGroups changes
  useEffect(() => {
    console.log('selectedGroups changed, regenerating config:', selectedGroups);
    generateConfig(selectedGroups);
  }, [selectedGroups]);

  // Handle group selection updates from ROISelector


  useEffect(() => {
    if (config) {
      console.log("Vitessce config:", config);
    }
  }, [config]);

  useEffect(() => {
    fetch("http://localhost:5000/api/roi_shapes")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (data.features && Array.isArray(data.features)) {
          const extracted = data.features.map((feature, index) => {
            const geometry = feature.geometry;
            if (!geometry || !geometry.coordinates) {
              return null;
            }

            let allCoords = [];
            if (geometry.type === "Polygon") {
              allCoords = geometry.coordinates;
            } else if (geometry.type === "MultiPolygon") {
              allCoords = geometry.coordinates.flat();
            } else {
              return null;
            }

            const [cx, cy] = allCoords.flat().reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
            const count = allCoords.flat().length;
            const centroid = [cx / count, 688 - (cy / count)]; // Flip Y coordinate

            return {
              id: feature.properties.name || `ROI_${index}`,
              x: centroid[0],
              y: centroid[1],
              score: feature.properties.score || 0,
              interactions: feature.properties.interactions || [],
              raw: feature.properties
            };
          }).filter(Boolean);
          setRois(extracted);
        }
      })
      .catch((err) => {
        console.error("Failed to load ROI shapes:", err);
        setRois([]);
      });
  }, []);

  const handleSetView = (roiView) => {
    console.log('Mainview handleSetView:', roiView);
    

    
    if (roiView.refreshConfig) {
      // Generate new config with NO segmentation files - only image
      const newConfig = generateVitessceConfig([]); // Empty array = no segmentation files
      
      // Update spatial coordinates if provided
      if (roiView.spatialTargetX !== undefined) {
        newConfig.coordinationSpace.spatialTargetX.A = roiView.spatialTargetX;
      }
      if (roiView.spatialTargetY !== undefined) {
        newConfig.coordinationSpace.spatialTargetY.A = roiView.spatialTargetY;
      }
      if (roiView.spatialZoom !== undefined) {
        newConfig.coordinationSpace.spatialZoom.A = roiView.spatialZoom;
      }
      
      setConfig(newConfig);
      setConfigKey(prev => prev + 1);
      
      // Store config globally for debugging
      window.lastConfig = newConfig;
      console.log('Generated new config for Set View - NO segmentation files:', newConfig);
      console.log('Config files:', newConfig.datasets[0].files);
      
      // Send config to backend
      fetch('http://localhost:5000/api/updateconfig', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newConfig)
      })
      .then(response => response.json())
      .then(data => {
        console.log('Config sent to backend:', data);
      })
      .catch(error => {
        console.error('Error sending config to backend:', error);
      });
    }

    if (roiView.selectedGroups && JSON.stringify(roiView.selectedGroups) !== JSON.stringify(selectedGroups)) {
      console.log('Updating selectedGroups:', roiView.selectedGroups);
      setSelectedGroups(roiView.selectedGroups);
    }

    // Pass the roiView to parent component
    if (onSetView) {
      onSetView(roiView);
    }
  };

  const handleHeatmapResults = (results) => {
    console.log('Received heatmap results:', results);
    setHeatmapResults(results);
  };

  const handleInteractionResults = (results) => {
    console.log('Received interaction results:', results);
    setInteractionHeatmapResult(results);
  };

  const handleCircleClick = (circleId) => {
    console.log('Circle clicked:', circleId);
    setSelectedCircle(circleId);
  };

  const changeHandler = (newConfig) => {
    console.log('Config changed:', newConfig);
    setConfig(newConfig);
  };

  // Tooltip event handlers
  const handleTooltipShow = (event) => {
    console.log('🖱️ Tooltip Show Event:', event);
  };

  const handleTooltipHide = (event) => {
    console.log('🖱️ Tooltip Hide Event:', event);
  };

  const handleMouseOver = (event) => {
    console.log('🖱️ Mouse Over Event:', event);
  };

  const handleMouseOut = (event) => {
    console.log('🖱️ Mouse Out Event:', event);
  };

  const handleGroupToggle = (groupId) => {
    setActiveGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };



  if (error) {
    return <p style={{ color: 'red', padding: '10px' }}>Error generating Mainview: {error}</p>;
  }
  if (!config) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Loading Vitessce configuration...</p>
        <p style={{ fontSize: '12px', color: '#666' }}>Please wait while the 3D viewer is being prepared</p>
      </div>
    );
  }

  return (
    <div className="left-panel">
      {/* HeatmapResults component will be rendered separately - only when there are results */}
      {(Object.keys(heatmapResults).length > 0 || interactionHeatmapResult) && (
        <HeatmapResults
          heatmapResults={heatmapResults}
          interactionHeatmapResult={interactionHeatmapResult}
          activeGroups={activeGroups}
          groupColors={groupColors}
          groupNames={groupNames}
          onClose={() => {
            setHeatmapResults({});
            setInteractionHeatmapResult(null);
          }}
          onHeatmapClick={() => {}}
          onGroupToggle={handleGroupToggle}
        />
      )}

      <div className="fullscreen-vitessce" style={{ position: 'relative', width: '100%', height: '100vh' }}>

        
        <Vitessce
          ref={vitessceRef}
          key={`${configKey}-${JSON.stringify(config?.datasets?.[0]?.files?.map(f => f.url))}`}
          config={config}
          onConfigChange={changeHandler}
          onTooltipShow={handleTooltipShow}
          onTooltipHide={handleTooltipHide}
          onMouseOver={handleMouseOver}
          onMouseOut={handleMouseOut}
          theme="light"
          height={null}
          width={null}
          style={{
            '--vitessce-layer-control-transform': 'scale(0.8)',
            '--vitessce-layer-control-transform-origin': 'top left'
          }}
        />
        

        
        <div className="roi-selector-container">
          <ROISelector 
            onSetView={handleSetView} 
            onHeatmapResults={handleHeatmapResults}
            onInteractionResults={handleInteractionResults}
            onGroupSelection={(groups) => {
              console.log('ROISelector onGroupSelection called with:', groups);
              setSelectedGroups(groups);
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default MainView; 