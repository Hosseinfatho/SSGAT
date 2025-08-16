import React, { useState, useEffect, useRef } from 'react';
import { Vitessce, CoordinationType } from 'vitessce';
import ROISelector from './ROISelector';
import Plot from 'react-plotly.js';
import HeatmapResults from './HeatmapResults';
import InteractionHeatmap from './InteractionHeatmap';

// Interaction types configuration
const INTERACTION_TYPES = {
  'B-cell_infiltration': 'B-cell infiltration',
  'T-cell_maturation': 'T-cell maturation', 
  'Inflammatory_zone': 'Inflammatory zone',
  'Oxidative_stress_regulation': 'Oxidative stress regulation'
};

// Constants for Image Channels
const IMAGE_CHANNELS = {
  'CD31': { 'id': 'cd31', 'color': [228, 26, 28], 'window': [300, 6000], 'targetC': 19 },      // Green
  'CD20': { 'id': 'cd20', 'color': [55, 126, 184], 'window': [1000, 5000], 'targetC': 27 },    // Yellow
  'CD11b': { 'id': 'cd11b', 'color': [77, 175, 74], 'window': [700, 4000], 'targetC': 37 },   // Violet
  'CD4': { 'id': 'cd4', 'color': [152, 78, 163], 'window': [1638, 5000], 'targetC': 25 },   // Sky Blue
  'CD11c': { 'id': 'cd11c', 'color': [255, 127, 0], 'window': [370, 1000], 'targetC': 42 },   // Orange
  'Catalase': { 'id': 'catalase', 'color': [166, 86, 40], 'window': [1000, 4000], 'targetC': 59 } // Red
};

// Constants for Interaction Type to ROI Mapping - updated
const INTERACTION_TO_ROI = {
  'B-cell infiltration': {
    'file': 'roi_segmentation_B-cell_infiltration.json',
    'obsType': 'ROI_B-cell',
    'color': [255, 180, 180],  // Light Red
    'strokeWidth': 16,
    'defaultOpacity': 0.5
  },
  'T-cell maturation': {
    'file': 'roi_segmentation_T-cell_maturation.json',
    'obsType': 'ROI_T-cell',
    'color': [180, 180, 255],  // Light Blue
    'strokeWidth': 16,
    'defaultOpacity': 0.5
  },
  'Inflammatory zone': {
    'file': 'roi_segmentation_Inflammatory_zone.json',
    'obsType': 'ROI_Inflammatory',
    'color': [180, 255, 180],  // Light Green
    'strokeWidth': 16,
    'defaultOpacity': 0.5
  },
  'Oxidative stress regulation': {
    'file': 'roi_segmentation_Oxidative_stress_regulation.json',
    'obsType': 'ROI_Oxidative',
    'color': [255, 255, 180],  // Light Yellow
    'strokeWidth': 16,
    'defaultOpacity': 0.5
  }
};

// Simple config generation function
const generateVitessceConfig = (selectedGroups = [], hasHeatmapResults = false, useSegmentationFiles = false) => { 
  // Build coordination space
  const coordination_space = {
    'dataset': { "A": "bv" },

    'imageLayer': { "image": "image" },
    'imageChannel': {},
    'spatialChannelColor': {"A": [255, 100, 100]},
    'spatialChannelOpacity': {"obsType": .5 },
    'spatialChannelVisible': {},
    'spatialChannelWindow': {},
    'spatialTargetC': {},
    'spatialLayerOpacity': { "obsType":0.5 },
    'spatialLayerVisible': { "image": true },
    'spatialRenderingMode': { "image": "3D" },
    'spatialTargetX': { "A": 5454 },
    'spatialTargetY': { "A": 2600 },
    'spatialTargetZ': { "A": 0 },
    'spatialZoom': { "A": -3.2 },
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
          "spatialChannelOpacity": {"obsType":0.5},
          "spatialChannelWindow": {}
        }
      }
    }
  };

  // Add image channels
  Object.entries(IMAGE_CHANNELS).forEach(([chName, chProps]) => {
    coordination_space['spatialChannelColor'][chName] = chProps['color'];
    coordination_space['spatialChannelOpacity'][chName] = 0.5;
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
        coordination_space['spatialSegmentationFilled'][obs_type] = true; // ROIs are filled for better visibility
        coordination_space['spatialSegmentationStrokeWidth'][obs_type] = roi_info['strokeWidth'];
        coordination_space['spatialLayerOpacity'][obs_type] = roi_info['defaultOpacity']; // Set opacity from ROI config
        coordination_space['spatialLayerVisible'][obs_type] = true; // Make ROIs visible in layer controller
        coordination_space[CoordinationType.TOOLTIPS_VISIBLE][obs_type] = true; // Enable tooltips for ROIs
        
        // Add ROI color to spatialChannelColor with transparency
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
        // Use API for local development with cache-busting
        roiUrl = `http://localhost:5000/api/${roi_info["file"]}?t=${Date.now()}`;
      } else {
        // Use local JSON files for GitHub Pages
                    roiUrl = `./${roi_info["file"]}`;
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
        'x': 3, 'y': 0, 'w': 9, 'h': 12
      },
      {
        'component': 'description',
        'x': 0, 'y': 0, 'w': 3, 'h': 4
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
        'x': 0, 'y': 4, 'w': 3, 'h':8
      }
    ]
  };

  return config;
};

const MainView = ({ onSetView }) => {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [prevCellSetSelection, setPrevCellSetSelection] = useState(null);
  const [showInstructions, setShowInstructions] = useState(false);



  const [heatmapResults, setHeatmapResults] = useState({});
  const [interactionHeatmapResult, setInteractionHeatmapResult] = useState(null);
  const [channelHeatmapResults, setChannelHeatmapResults] = useState(null);
  const [activeGroups, setActiveGroups] = useState({
    1: true,
    2: true,
    3: true,
    4: true
  });
  const [configKey, setConfigKey] = useState(0);
  const [rois, setRois] = useState([]);
  const [selectedCircle, setSelectedCircle] = useState(null);
  const [selectedGroups, setSelectedGroups] = useState(['B-cell infiltration']);
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
    
    // Show instructions popup on first visit
    const hasSeenInstructions = localStorage.getItem('hasSeenInstructions');
    if (!hasSeenInstructions) {
      setShowInstructions(true);
    }
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
              const centroid = [cx / count,  (cy / count)]; // Flip Y coordinate

              return {
                id: feature.properties.name || `ROI_${index}`,
                x: centroid[0],
                y: centroid[1],
                score: feature.properties.score || 0,
                interactions: feature.properties.interactions || [],
                tooltip_name: feature.properties.tooltip_name || `ROI_${index + 1} Score: ${(feature.properties.score || 0).toFixed(3)}`,
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
      
      // Check if we should use top5_roi files (when Set View is pressed)
      const useTop5RoiFiles = roiView.useTop5RoiFile || false;
      console.log('Using top5_roi files:', useTop5RoiFiles);
      
      // Generate new config with selected groups to show ROI overlays
      const newConfig = generateVitessceConfig(groupsToUse, Object.keys(heatmapResults).length > 0 || interactionHeatmapResult, useTop5RoiFiles);
      
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
    
    // Don't reset interaction heatmap state - allow both to be visible
    
    // Check if results contain channel_heatmaps
    if (results.channel_heatmaps) {
      // Set channel heatmaps for the Heatmaps button
      setChannelHeatmapResults({ channel_heatmaps: results.channel_heatmaps });
    } else {
      // Fallback: check if results contain interaction heatmaps
      const hasInteractionHeatmaps = results.heatmaps && 
        Object.keys(results.heatmaps).some(key => key.startsWith('group_'));
      
      if (hasInteractionHeatmaps) {
        const interactionHeatmaps = {};
        const channelHeatmaps = {};
        
        Object.entries(results.heatmaps).forEach(([key, value]) => {
          if (key.startsWith('group_')) {
            interactionHeatmaps[key] = value;
          } else {
            channelHeatmaps[key] = value;
          }
        });
        
        setChannelHeatmapResults(Object.keys(channelHeatmaps).length > 0 ? { channel_heatmaps: channelHeatmaps } : null);
      } else {
        // Only channel heatmaps
        setChannelHeatmapResults(results);
      }
    }
  };

  const handleInteractionResults = (results) => {
    console.log('Received interaction results:', results);
    // Don't reset channel heatmaps - allow both to be visible
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

  const handleCloseInstructions = () => {
    setShowInstructions(false);
    localStorage.setItem('hasSeenInstructions', 'true');
  };

  const handleShowInstructions = () => {
    setShowInstructions(true);
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
    <>
      {/* Instructions Popup */}
      {showInstructions && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif'
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '30px',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)',
            position: 'relative'
          }}>
            <button
              onClick={handleCloseInstructions}
              style={{
                position: 'absolute',
                top: '15px',
                right: '20px',
                background: 'none',
                border: 'none',
                fontSize: '24px',
                cursor: 'pointer',
                color: '#666',
                fontWeight: 'bold'
              }}
            >
              ×
            </button>
            
            <h2 style={{ 
              color: '#333', 
              marginBottom: '20px', 
              fontSize: '24px',
              fontWeight: '600'
            }}>
              Welcome to SSGAT Viewer!
            </h2>
            
                         <div style={{ fontSize: '16px', lineHeight: '1.6', color: '#555' }}>
               <p style={{ marginBottom: '20px' }}>
                 To view and explore all automatically detected ROIs, please first select an interaction type in the ROI Navigator panel.
               </p>
               
               <p style={{ marginBottom: '20px' }}>
               To inspect a specific ROI, refer to the bars above the rings to identify ROI order. In the volume image, hover over a marker to display its ID, then use the arrows in the ROI Navigator panel to select it, zoom in, and click Set View.               </p>
               
               <div style={{ 
                 backgroundColor: '#f8f9fa', 
                 padding: '15px', 
                 borderRadius: '8px', 
                 borderLeft: '4px solid #2b83ba',
                 marginBottom: '20px'
               }}>
                 <strong> Available Interactions:</strong>
                 <ul style={{ margin: '10px 0 0 20px', padding: 0 }}>
                   <li>B-cell infiltration</li>
                   <li>T-cell maturation</li>
                   <li>Inflammatory zone</li>
                   <li>Oxidative stress regulation</li>
                 </ul>
               </div>
             </div>
            
            <button
              onClick={handleCloseInstructions}
              style={{
                backgroundColor: '#2b83ba',
                color: 'white',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '6px',
                fontSize: '16px',
                cursor: 'pointer',
                fontWeight: '500',
                marginTop: '10px'
              }}
            >
              Got it! Let's start exploring
            </button>
          </div>
        </div>
      )}
             
      
      <div className="main-container" style={{ display: 'flex', height: '100vh', width: '100%', margin: '0', padding: '0', border: '0', background: '#000' }}>
      {/* Main Vitessce Viewer - Takes most of the space */}
      <div className="vitessce-container" style={{ flex: '1 1 auto', position: 'relative', margin: '0', padding: '0', border: '0', background: '#000' }}>

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
        />
      </div>

             {/* Instruction Button */}
       <button
         onClick={handleShowInstructions}
         style={{
           position: 'fixed',
           top: '10px',
           right: '55px',
           zIndex: 1000,
           backgroundColor: 'white',
           color: 'black',
           border: '1px solid #ccc',
           padding: '6px 12px',
           borderRadius: '4px',
           fontSize: '14px',
           cursor: 'pointer',
           fontWeight: '400',
           boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
         }}
       >
         Instructions
       </button>

       <div style={{ 
           position: 'fixed', 
           top: '15px', 
           left: '10px', 
           zIndex: 10,
           width: '24%',
           height: '30%'
         }}>
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

                                                                                                                                                                                                                                           {/* Channel Heatmap Results - Only show when there are results */}
            {channelHeatmapResults && channelHeatmapResults.channel_heatmaps && Object.keys(channelHeatmapResults.channel_heatmaps).length > 0 && (
                <div style={{ 
                  position: 'fixed', 
                  bottom: '1px', 
                  left: '150px',
                  zIndex: 1,
                  transform: 'scale(0.6)',
                  transformOrigin: 'bottom left'
                }}>
                  <HeatmapResults
                    heatmapResults={channelHeatmapResults}
                    interactionHeatmapResult={null}
                    activeGroups={activeGroups}
                    groupColors={groupColors}
                    groupNames={groupNames}
                    imageChannels={IMAGE_CHANNELS}
                    onClose={() => {
                      setChannelHeatmapResults(null);
                    }}
                    onHeatmapClick={() => {}}
                    onGroupToggle={handleGroupToggle}
                  />
                </div>
            )}

            {/* Interaction Heatmap Results - Only show when there are results */}
            {interactionHeatmapResult && interactionHeatmapResult !== null && Object.keys(interactionHeatmapResult).length > 0 && (
              <div className="heatmap-results-fixed" style={{ 
                position: 'fixed', 
                bottom: '10px', 
                right: '25px',
                zIndex: 1,
                transform: 'scale(0.6)',
                transformOrigin: 'bottom right'
              }}>
                <InteractionHeatmap
                  interactionHeatmapResult={interactionHeatmapResult}
                  activeGroups={activeGroups}
                  groupColors={groupColors}
                  groupNames={groupNames}
                  onClose={() => {
                    setInteractionHeatmapResult(null);
                  }}
                  onGroupToggle={handleGroupToggle}
                />
              </div>
            )}
      </div>
    </>
  );
};

export default MainView; 