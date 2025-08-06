import React, { useState, useEffect, useRef } from 'react';
import { Vitessce, CoordinationType } from 'vitessce';
import ROISelector from './ROISelector';
import Plot from 'react-plotly.js';
import HeatmapResults from './HeatmapResults';

// Interaction types configuration
const INTERACTION_TYPES = {
  'B-cell_infiltration': 'B-cell infiltration',
  'T-cell_maturation': 'T-cell maturation', 
  'Inflammatory_zone': 'Inflammatory zone',
  'Oxidative_stress_regulation': 'Oxidative stress regulation'
};

// Constants for Image Channels
const IMAGE_CHANNELS = {
  'CD31': { 'id': 'cd31', 'color': [0, 255, 0], 'window': [300, 10000], 'targetC': 19 },      // Green
  'CD20': { 'id': 'cd20', 'color': [255, 255, 0], 'window': [1000, 5000], 'targetC': 27 },    // Yellow
  'CD11b': { 'id': 'cd11b', 'color': [148, 0, 211], 'window': [700, 4000], 'targetC': 37 },   // Violet
  'CD4': { 'id': 'cd4', 'color': [135, 206, 235], 'window': [1638, 5000], 'targetC': 25 },   // Sky Blue
  'CD11c': { 'id': 'cd11c', 'color': [255, 165, 0], 'window': [370, 1000], 'targetC': 42 },   // Orange
  'Catalase': { 'id': 'catalase', 'color': [255, 0, 0], 'window': [1000, 4000], 'targetC': 59 } // Red
};

// Constants for Interaction Type to ROI Mapping - updated
const INTERACTION_TO_ROI = {
  'B-cell infiltration': {
    'file': 'roi_segmentation_B-cell_infiltration.json',
    'obsType': 'ROI_B-cell',
    'color': [255, 180, 180],  // Light Red
    'strokeWidth': 16
  },
  'T-cell maturation': {
    'file': 'roi_segmentation_T-cell_maturation.json',
    'obsType': 'ROI_T-cell',
    'color': [180, 180, 255],  // Light Blue
    'strokeWidth': 16
  },
  'Inflammatory zone': {
    'file': 'roi_segmentation_Inflammatory_zone.json',
    'obsType': 'ROI_Inflammatory',
    'color': [180, 255, 180],  // Light Green
    'strokeWidth': 16
  },
  'Oxidative stress regulation': {
    'file': 'roi_segmentation_Oxidative_stress_regulation.json',
    'obsType': 'ROI_Oxidative',
    'color': [255, 255, 180],  // Light Yellow
    'strokeWidth': 16
  }
};

// Simple config generation function
const generateVitessceConfig = (selectedGroups = [], hasHeatmapResults = false) => { 
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
    'spatialTargetY': { "A": 2600 },
    'spatialTargetZ': { "A": 0 },
    'spatialZoom': { "A": -2.7 },
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
          "imageChannel": { "image": ["CD31", "CD20", "CD11b", "CD4", "CD11c", "Catalase"] },
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
        coordination_space['spatialLayerOpacity'][obs_type] = 1; // Set opacity to 0.5 for ROIs
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
      
      // Use local JSON files for GitHub Pages, API for local development
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      let roiUrl;
      if (isLocalhost) {
        // Use API for local development
        roiUrl = `http://localhost:5000/api/${roi_info["file"]}`;
      } else {
        // Use local JSON files for GitHub Pages
        roiUrl = `/data/${roi_info["file"]}`;
      }
      
      files.push({
        'fileType': 'obsSegmentations.json',
        'url': roiUrl,
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
        'x': 2, 'y': 0, 'w': 10, 'h': 8
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
    1: '#d7191c',  // Dark Red - B-cell infiltration
    2: '#fdae61',  // Orange - T-cell maturation
    3: '#abdda4',  // Light Green - Inflammatory zone
    4: '#2b83ba'   // Blue - Oxidative stress regulation
  };

  const groupNames = {
    1: 'B-cell infiltration',
    2: 'T-cell maturation',
    3: 'Inflammatory zone',
    4: 'Oxidative stress regulation'
  };

  // Helper function to preserve current view coordinates
  const preserveViewAndGenerateConfig = (groups = [], hasHeatmapResults = false) => {
    // Store current view coordinates before regenerating config
    const currentConfig = config;
    let currentView = null;
    
    if (currentConfig && currentConfig.coordinationSpace) {
      currentView = {
        spatialTargetX: currentConfig.coordinationSpace.spatialTargetX?.A,
        spatialTargetY: currentConfig.coordinationSpace.spatialTargetY?.A,
        spatialZoom: currentConfig.coordinationSpace.spatialZoom?.A
      };
    }
    
    // Generate new config
    const newConfig = generateVitessceConfig(groups, hasHeatmapResults);
    
    // Restore current view if it exists
    if (currentView && currentView.spatialTargetX !== undefined) {
      newConfig.coordinationSpace.spatialTargetX.A = currentView.spatialTargetX;
      newConfig.coordinationSpace.spatialTargetY.A = currentView.spatialTargetY;
      newConfig.coordinationSpace.spatialZoom.A = currentView.spatialZoom;
      console.log('Restored view coordinates:', currentView);
    }
    
    setConfig(newConfig);
    setConfigKey(prev => prev + 1); // Force re-render
    
    // Store config globally for debugging
    window.lastConfig = newConfig;
    console.log('Generated config and stored in window.lastConfig:', newConfig);
    
    // Note: Config is NOT sent to backend here - only sent when Set View is pressed
  };

  // Generate config locally (legacy function - now uses preserveViewAndGenerateConfig)
  const generateConfig = (groups = [], hasHeatmapResults = false) => {
    preserveViewAndGenerateConfig(groups, hasHeatmapResults);
  };

  // Generate initial config on component mount
  useEffect(() => {
    const initialConfig = generateVitessceConfig([], Object.keys(heatmapResults).length > 0 || interactionHeatmapResult);
    setConfig(initialConfig);
    setConfigKey(prev => prev + 1);
    
    // Store config globally for debugging
    window.lastConfig = initialConfig;
    console.log('Generated initial config:', initialConfig);
  }, []);

  // Regenerate config when selectedGroups changes - but preserve current view
  useEffect(() => {
    console.log('selectedGroups changed, regenerating config:', selectedGroups);
    preserveViewAndGenerateConfig(selectedGroups, Object.keys(heatmapResults).length > 0 || interactionHeatmapResult);
  }, [selectedGroups]);

  // Regenerate config when heatmap results change - but preserve current view
  useEffect(() => {
    console.log('Heatmap results changed, regenerating config');
    preserveViewAndGenerateConfig(selectedGroups, Object.keys(heatmapResults).length > 0 || interactionHeatmapResult);
  }, [heatmapResults, interactionHeatmapResult]);

  // Handle group selection updates from ROISelector


  useEffect(() => {
    if (config) {
      console.log("Vitessce config:", config);
    }
  }, [config]);

  useEffect(() => {
    // Only fetch ROI shapes for local development
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocalhost) {
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
                tooltip_name: feature.properties.tooltip_name || `${feature.properties.interaction || 'Unknown'}_${feature.properties.id || index}_Score:${(feature.properties.score || 0).toFixed(3)}`,
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
    } else {
      console.log('Skipping ROI shapes fetch on GitHub Pages');
      setRois([]);
    }
  }, []);

  const handleSetView = (roiView) => {
    console.log('Mainview handleSetView:', roiView);
    console.log('roiView.currentROIGroup:', roiView.currentROIGroup);
    console.log('roiView.selectedGroups:', roiView.selectedGroups);
    console.log('roiView.refreshConfig:', roiView.refreshConfig);
    console.log('roiView.spatialTargetX:', roiView.spatialTargetX);
    console.log('roiView.spatialTargetY:', roiView.spatialTargetY);
    console.log('roiView.spatialZoom:', roiView.spatialZoom);
    console.log('current selectedGroups:', selectedGroups);
    
    if (roiView.refreshConfig) {
      // Use roiView.currentROIGroup if available (from Set View), otherwise use selectedGroups
      let groupsToUse;
      if (roiView.currentROIGroup) {
        // When Set View is pressed, use the current ROI's group
        groupsToUse = [roiView.currentROIGroup];
        console.log('Using currentROIGroup for config generation:', groupsToUse);
      } else {
        // Otherwise use selectedGroups
        groupsToUse = roiView.selectedGroups || selectedGroups;
        console.log('Using selectedGroups for config generation:', groupsToUse);
      }
      // Generate new config with selected groups to show ROI overlays
      const newConfig = generateVitessceConfig(groupsToUse, Object.keys(heatmapResults).length > 0 || interactionHeatmapResult);
      
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
      console.log('Generated new config for Set View with ROI overlays:', newConfig);
      console.log('Config files:', newConfig.datasets[0].files);
      console.log('New view coordinates:', {
        spatialTargetX: newConfig.coordinationSpace.spatialTargetX.A,
        spatialTargetY: newConfig.coordinationSpace.spatialTargetY.A,
        spatialZoom: newConfig.coordinationSpace.spatialZoom.A
      });
      
             // Send config to backend only for local development
       const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
       if (isLocalhost) {
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
       } else {
         console.log('Skipping backend config update on GitHub Pages');
       }
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
          imageChannels={IMAGE_CHANNELS}
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