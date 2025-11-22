import React, { useState, useEffect, useRef } from 'react';
import { Vitessce, CoordinationType } from 'vitessce';
import ROISelector from './ROISelector';
import HeatmapResults from './HeatmapResults';
import InteractionHeatmap from './InteractionHeatmap';

// Channel list from 0 to 69
const CHANNEL_LIST = [
  "Hoechst", "5'hmC", "MX1", "MART1", "Hoechst", "CD3E (do not use)", "MHC-I", "SOX10", "Hoechst", "S100B",
  "MITF", "GranzymeB (do not use)", "Hoechst", "pan-cytokeratin", "lamin-ABC", "PDL1", "Hoechst", "PD1 (do not use)",
  "S100A", "CD31", "Hoechst", "CD206", "pMLC2", "CD11b (do not use)", "Hoechst", "CD4", "LAG3", "CD20",
  "Hoechst", "PRAME", "CD163", "IRF1", "Hoechst", "B-catenin", "CD3E", "CD8a", "Hoechst", "CD11b",
  "FOXP3", "PD1", "Hoechst", "Ki67", "CD11c", "COX-IV", "Hoechst", "LysozymeC", "SOX9", "PMEL",
  "CD103", "Hoechst", "CyclinD1", "BAF1", "Hoechst", "B-actin", "Mast cell tryptase", "CD15", "Podoplanin", "Hoechst",
  "B-tubulin", "Catalase", "y-H2AX", "Hoechst", "E-cadherin", "Vimentin", "Neurofilament L (do not use)", "GranzymeB", "Hoechst", "MHC-II",
  "H3K27me3", "Collagen (SHG)"
];

// Helper function to find channel index by name
const getChannelIndex = (channelName) => {
  return CHANNEL_LIST.findIndex(ch => ch === channelName || ch.includes(channelName.split(' ')[0]));
};

// Default channels configuration (all available channels)
const IMAGE_CHANNELS = {
  'CD31': { 'color': [141,211,199], 'window': [300, 6000], 'targetC': 19 },
  'CD20': { 'color': [191,91,23], 'window': [3000, 5000], 'targetC': 27 },
  'CD11b': { 'color': [190,186,218], 'window': [700, 4000], 'targetC': 37 },
  'CD4': { 'color': [251,128,114], 'window': [1638, 5000], 'targetC': 25 },
  'CD11c': { 'color': [128,177,211], 'window': [370, 1000], 'targetC': 42 },
  'Catalase': { 'color': [253,180,98], 'window': [1000, 4000], 'targetC': 59 }
};

// T-cell maturation channels
const T_CELL_MATURATION_CHANNELS = {
  'CD3E': { 'color': [179,222,105], 'window': [1000, 5000], 'targetC': 34},
  'CD4': { 'color': [251,128,114], 'window': [1638, 5000], 'targetC': 25 },
  'CD8a': { 'color': [204,204,204], 'window': [1000, 5000], 'targetC': getChannelIndex('CD8a') },
  'PD1': { 'color': [255,242,174], 'window': [1000, 3000], 'targetC': 39 },
  'LAG3': { 'color': [166,206,227], 'window': [1000, 2000], 'targetC': getChannelIndex('LAG3') },
  'CD103': { 'color': [178,223,138], 'window': [1000, 2000], 'targetC': getChannelIndex('CD103') }
};

// Inflammatory zone channels
const INFLAMMATORY_ZONE_CHANNELS = {
  'CD11b': { 'color': [190,186,218], 'window': [1500, 7500], 'targetC': 37 },
  'CD11c': { 'color': [128,177,211], 'window': [370, 3200], 'targetC': 42 },
  'CD163': { 'color': [253,191,111], 'window': [1000, 5000], 'targetC': getChannelIndex('CD163') },
  'CD31': { 'color': [255,127,0], 'window': [4000, 16000], 'targetC': 19 },
  'S100A': { 'color': [51,160,44], 'window': [4500, 8500], 'targetC': getChannelIndex('S100A') },
  'SOX10': { 'color': [31,120,180], 'window': [1500, 4500], 'targetC': getChannelIndex('SOX10') }
};

// Oxidative stress regulation channels
const OXIDATIVE_STRESS_CHANNELS = {
  
  'COX-IV': { 'color': [251,180,174], 'window': [4000, 16000], 'targetC': getChannelIndex('COX-IV') },
  'y-H2AX': { 'color': [179,205,227], 'window': [4000, 11000], 'targetC': getChannelIndex('y-H2AX') },
  'H3K27me3': { 'color': [204,235,197], 'window': [3000, 9000], 'targetC': getChannelIndex('H3K27me3') },
  'CyclinD1': { 'color': [254,217,166], 'window': [600, 2600], 'targetC': getChannelIndex('CyclinD1') },
  'B-catenin': { 'color': [255,255,204], 'window': [9000, 12000], 'targetC': getChannelIndex('B-catenin') },
  'Catalase': { 'color': [253,218,236], 'window': [3500, 13000], 'targetC': 59 }
};

// B-cell infiltration channels
const B_CELL_INFILTRATION_CHANNELS = {
  'CD20': { 'color': [191,91,23], 'window': [3000, 5000], 'targetC': 27 }
};

// Define channels for each interaction type
const INTERACTION_CHANNELS = {
  'T-cell maturation': ['CD3E', 'CD4', 'CD8a', 'PD1', 'LAG3', 'CD103'],
  'Inflammatory zone': ['CD11b', 'CD11c', 'CD163', 'CD31', 'S100A', 'SOX10'],
  'Oxidative stress regulation': ['Catalase', 'COX-IV', 'y-H2AX', 'H3K27me3', 'CyclinD1', 'B-catenin'],
  'B-cell infiltration': ['CD20']
};

// Map interaction types to their channel configurations
const INTERACTION_CHANNEL_CONFIGS = {
  'T-cell maturation': T_CELL_MATURATION_CHANNELS,
  'Inflammatory zone': INFLAMMATORY_ZONE_CHANNELS,
  'Oxidative stress regulation': OXIDATIVE_STRESS_CHANNELS,
  'B-cell infiltration': B_CELL_INFILTRATION_CHANNELS
};

const INTERACTION_TO_ROI = {
  'B-cell infiltration': { file: 'roi_segmentation_B-cell_infiltration.json', obsType: 'ROI_B-cell', color: [255, 180, 180] },
  'T-cell maturation': { file: 'roi_segmentation_T-cell_maturation.json', obsType: 'ROI_T-cell', color: [180, 180, 255] },
  'Inflammatory zone': { file: 'roi_segmentation_Inflammatory_zone.json', obsType: 'ROI_Inflammatory', color: [180, 255, 180] },
  'Oxidative stress regulation': { file: 'roi_segmentation_Oxidative_stress_regulation.json', obsType: 'ROI_Oxidative', color: [255, 255, 180] }
};
const ROI_DEFAULTS = { strokeWidth: 16, defaultOpacity: 0.5 };

const generateVitessceConfig = (selectedGroups = [], selectedROIGroups = [], hasHeatmapResults = false) => {
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  
  // Get active channels based on selected interaction types
  let activeChannelConfig = {};
  if (selectedGroups.length > 0) {
    // Use channels from selected interaction types
    selectedGroups.forEach(group => {
      const channelConfig = INTERACTION_CHANNEL_CONFIGS[group] || {};
      Object.assign(activeChannelConfig, channelConfig);
    });
  } else {
    // If no group selected, use default channels
    activeChannelConfig = IMAGE_CHANNELS;
  }
  
  let channelNames = Object.keys(activeChannelConfig);
  
  // Ensure we have at least one channel
  if (channelNames.length === 0) {
    console.warn('No channels found, using default channels');
    activeChannelConfig = IMAGE_CHANNELS;
    channelNames = Object.keys(IMAGE_CHANNELS);
  }
  
  const coordination_space = {
    'dataset': { "A": "bv" },
    'imageLayer': { "image": "image" },
    'imageChannel': {},
    'spatialChannelColor': {},
    'spatialChannelOpacity': {},
    'spatialChannelVisible': {},
    'spatialChannelWindow': {},
    'spatialTargetC': {},
    'spatialLayerOpacity': { "image": 0.5 },
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
        "spatialChannelVisible": channelNames,
        "spatialChannelOpacity": channelNames,
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
          "imageChannel": { "image": channelNames },
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

  const metaChannel = coordination_space['metaCoordinationScopesBy']['metaA']['imageChannel'];
  const metaA = coordination_space['metaCoordinationScopes']['metaA'];
  
  // Use activeChannelConfig instead of IMAGE_CHANNELS
  Object.entries(activeChannelConfig).forEach(([chName, chProps]) => {
    Object.assign(coordination_space['spatialChannelColor'], { [chName]: chProps.color });
    Object.assign(coordination_space['spatialChannelOpacity'], { [chName]: 0.5 });
    Object.assign(coordination_space['spatialChannelVisible'], { [chName]: true });
    Object.assign(coordination_space['spatialChannelWindow'], { [chName]: chProps.window });
    Object.assign(coordination_space['spatialTargetC'], { [chName]: chProps.targetC });
    
    ['spatialTargetC', 'spatialChannelColor', 'spatialChannelVisible', 'spatialChannelOpacity', 'spatialChannelWindow'].forEach(key => {
      metaChannel[key][chName] = chName;
    });
    metaA['spatialChannelColor'].push(chName);
  });

  const files = [{
    'fileType': 'image.ome-zarr',
    'url': 'https://lsp-public-data.s3.amazonaws.com/biomedvis-challenge-2025/Dataset1-LSP13626-melanoma-in-situ/0',
  }];

  // Only add ROI overlay files if selected in ROI Navigator
  selectedROIGroups.forEach(group => {
    const roi = INTERACTION_TO_ROI[group];
    if (!roi) return;
    
    const { obsType, color, file } = roi;
    
    Object.entries({
      'spatialSegmentationFilled': true,
      'spatialSegmentationStrokeWidth': ROI_DEFAULTS.strokeWidth,
      'spatialLayerOpacity': ROI_DEFAULTS.defaultOpacity,
      'spatialLayerVisible': true,
      [CoordinationType.TOOLTIPS_VISIBLE]: true,
      'spatialChannelColor': color
    }).forEach(([key, value]) => {
      coordination_space[key][obsType] = value;
      metaA[key].push(obsType);
    });
    
    files.push({
      'fileType': 'obsSegmentations.json',
      'url': isLocalhost ? `http://localhost:5000/api/${file}?t=${Date.now()}` : `./${file}`,
      'coordinationValues': { 'obsType': obsType }
    });
  });

  const coordScopes = {
    'metaCoordinationScopes': ["metaA"],
    'metaCoordinationScopesBy': ["metaA"],
    'spatialTargetX': "A",
    'spatialTargetY': "A",
    'spatialTargetZ': "A",
    'spatialZoom': "A",
    'spatialTargetResolution': "image",
    'spatialTargetT': "image",
    'spatialRenderingMode': "image",
    'spatialChannelVisible': channelNames,
    'spatialChannelOpacity': Object.keys(coordination_space['spatialChannelOpacity']),
    'spatialChannelColor': channelNames,
    'spatialLayerOpacity': Object.keys(coordination_space['spatialLayerOpacity']),
    'spatialLayerVisible': Object.keys(coordination_space['spatialLayerVisible']),
    'spatialSegmentationFilled': Object.keys(coordination_space['spatialSegmentationFilled']),
    'spatialSegmentationStrokeWidth': Object.keys(coordination_space['spatialSegmentationStrokeWidth']),
    [CoordinationType.TOOLTIPS_VISIBLE]: Object.keys(coordination_space[CoordinationType.TOOLTIPS_VISIBLE])
  };
  
  return {
    'version': '1.0.16',
    'name': `BioMedVis Challenge - ${selectedGroups.length > 0 ? selectedGroups.join(", ") : "Image Only"}`,
    'description': `Dynamic config with selected interaction types: ${selectedGroups.length > 0 ? selectedGroups.join(", ") : "None"}`,
    'datasets': [{ 'uid': 'bv', 'name': 'Blood Vessel', 'files': files }],
    'initStrategy': 'auto',
    'coordinationSpace': coordination_space,
    'layout': [
      { 'component': 'spatialBeta', 'coordinationScopes': coordScopes, 'x': 3, 'y': 0, 'w': 9, 'h': 12 },
      { 'component': 'description', 'x': 0, 'y': 0, 'w': 3, 'h': 4 },
      { 'component': 'layerControllerBeta', 'coordinationScopes': coordScopes, 'x': 0, 'y': 4, 'w': 3, 'h': 8 }
    ]
  };
};

const MainView = ({ onSetView }) => {
  const [config, setConfig] = useState(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [interactionHeatmapResult, setInteractionHeatmapResult] = useState(null);
  const [channelHeatmapResults, setChannelHeatmapResults] = useState(null);
  const [activeGroups, setActiveGroups] = useState({ 1: true, 2: true, 3: true, 4: true });
  const [configKey, setConfigKey] = useState(0);
  const [selectedGroups, setSelectedGroups] = useState(['B-cell infiltration']);
  const vitessceRef = useRef(null);
  const [mouseCoords, setMouseCoords] = useState(null);
  const containerRef = useRef(null);

  const groupColors = { 1: '#d7191c', 2: '#fdae61', 3: '#abdda4', 4: '#2b83ba' };
  const groupNames = { 1: 'B-cell infiltration', 2: 'T-cell maturation', 3: 'Inflammatory zone', 4: 'Oxidative stress regulation' };

  const updateConfig = (channelGroups, roiOverlayGroups = [], preserveView = false) => {
    const newConfig = generateVitessceConfig(channelGroups, roiOverlayGroups, !!interactionHeatmapResult);
    const spatial = newConfig.coordinationSpace;
    
    if (preserveView && config?.coordinationSpace) {
      ['spatialTargetX', 'spatialTargetY', 'spatialZoom'].forEach(key => {
        if (config.coordinationSpace[key]?.A !== undefined) spatial[key].A = config.coordinationSpace[key].A;
      });
    }
    
    setConfig(newConfig);
    setConfigKey(prev => prev + 1);
  };

  useEffect(() => {
    // Initialize with default channels (B-cell infiltration)
    updateConfig(['B-cell infiltration'], []);
    if (!localStorage.getItem('hasSeenInstructions')) {
      setShowInstructions(true);
    }
  }, []);

  useEffect(() => {
    // Update config when channel or ROI overlay selection changes
    if (selectedGroups && typeof selectedGroups === 'object' && !Array.isArray(selectedGroups)) {
      // New format: { channels: [], roiOverlay: [] }
      const channelGroups = selectedGroups.channels || [];
      const roiOverlayGroups = selectedGroups.roiOverlay || [];
      updateConfig(channelGroups, roiOverlayGroups, true);
    } else if (Array.isArray(selectedGroups)) {
      // Old format: just array of groups (for backward compatibility)
      updateConfig(selectedGroups, [], true);
    }
  }, [selectedGroups]);

  // Calculate world coordinates from mouse position
  useEffect(() => {
    if (!config || !containerRef.current) return;

    const calculateWorldCoords = (clientX, clientY) => {
      const container = containerRef.current;
      if (!container) return null;

      const canvas = container.querySelector('canvas');
      if (!canvas) return null;

      const canvasRect = canvas.getBoundingClientRect();
      const canvasX = clientX - canvasRect.left;
      const canvasY = clientY - canvasRect.top;

      if (canvasX < 0 || canvasY < 0 || canvasX > canvasRect.width || canvasY > canvasRect.height) {
        return null;
      }

      // Get view state from config
      const cs = config?.coordinationSpace || {};
      const targetX = cs.spatialTargetX?.A ?? 5454;
      const targetY = cs.spatialTargetY?.A ?? 2600;
      const zoom = cs.spatialZoom?.A ?? -3.2;

      // Calculate scale: zoom = -log2(scale), so scale = 2^(-zoom)
      const scale = Math.pow(2, -zoom);

      // Get canvas dimensions
      const canvasWidth = canvas.width;
      const canvasHeight = canvas.height;
      const displayWidth = canvasRect.width;
      const displayHeight = canvasRect.height;

      // Account for device pixel ratio
      const pixelRatio = canvasWidth / displayWidth;
      const actualX = canvasX * pixelRatio;
      const actualY = canvasY * pixelRatio;

      // Calculate center of canvas
      const centerX = canvasWidth / 2;
      const centerY = canvasHeight / 2;

      // Calculate offset from center in pixels
      const offsetXPixels = actualX - centerX;
      const offsetYPixels = actualY - centerY;

      // Convert pixel offset to world coordinates
      const offsetX = offsetXPixels / scale;
      const offsetY = offsetYPixels / scale;

      // Calculate world coordinates
      const worldX = Math.round(targetX + offsetX);
      const worldY = Math.round(targetY + offsetY);

      // Clamp to image bounds
      const clampedX = Math.max(0, Math.min(10908, worldX));
      const clampedY = Math.max(0, Math.min(5508, worldY));

      return { x: clampedX, y: clampedY };
    };

    const handleMouseMove = (e) => {
      const coords = calculateWorldCoords(e.clientX, e.clientY);
      setMouseCoords(coords);
    };

    const handleMouseLeave = () => {
      setMouseCoords(null);
    };

    const container = containerRef.current;
    if (container) {
      const timeoutId = setTimeout(() => {
        container.addEventListener('mousemove', handleMouseMove);
        container.addEventListener('mouseleave', handleMouseLeave);
      }, 500);

      return () => {
        clearTimeout(timeoutId);
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('mouseleave', handleMouseLeave);
      };
    }
  }, [config]);

  const handleSetView = (roiView) => {
    if (roiView.refreshConfig) {
      const channelGroups = roiView.currentROIGroup ? [roiView.currentROIGroup] : (roiView.selectedGroups || selectedGroups);
      const roiOverlayGroups = roiView.selectedROIGroups || [];
      const newConfig = generateVitessceConfig(
        channelGroups,
        roiOverlayGroups,
        !!interactionHeatmapResult
      );
      const spatial = newConfig.coordinationSpace;
      
      ['spatialTargetX', 'spatialTargetY', 'spatialZoom'].forEach(key => {
        if (roiView[key] !== undefined) spatial[key].A = roiView[key];
      });
      
      setConfig(newConfig);
      setConfigKey(prev => prev + 1);
      
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (isLocalhost) {
        fetch('http://localhost:5000/api/updateconfig', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newConfig)
        }).catch(error => console.error('Error sending config to backend:', error));
      }
    }

    if (roiView.selectedGroups && JSON.stringify(roiView.selectedGroups) !== JSON.stringify(selectedGroups)) {
      setSelectedGroups(roiView.selectedGroups);
    }
    onSetView?.(roiView);
  };

  const handleHeatmapResults = (results) => {
    if (results.channel_heatmaps) {
      setChannelHeatmapResults({ channel_heatmaps: results.channel_heatmaps });
    } else if (results.heatmaps) {
      const channelHeatmaps = Object.fromEntries(
        Object.entries(results.heatmaps).filter(([key]) => !key.startsWith('group_'))
      );
      setChannelHeatmapResults(Object.keys(channelHeatmaps).length > 0 ? { channel_heatmaps: channelHeatmaps } : null);
    } else {
      setChannelHeatmapResults(results);
    }
  };

  const handleInteractionResults = (results) => {
    setInteractionHeatmapResult(results);
  };

  const handleGroupToggle = (groupId) => {
    setActiveGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  const handleCloseInstructions = () => {
    setShowInstructions(false);
    localStorage.setItem('hasSeenInstructions', 'true');
  };

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
            
            <h2 style={{ color: '#333', marginBottom: '20px', fontSize: '24px', fontWeight: '600' }}>
              Welcome to SSGAT Viewer!
            </h2>
            
            <div style={{ fontSize: '16px', lineHeight: '1.6', color: '#555' }}>
              <p style={{ marginBottom: '20px' }}>
                To view and explore all automatically detected ROIs, please first select an interaction type in the ROI Navigator panel.
              </p>
              
              <p style={{ marginBottom: '20px' }}>
                To inspect a specific ROI, refer to the bars above the rings to identify ROI order. In the volume image, hover over a marker to display its ID, then use the arrows in the ROI Navigator panel to select it, zoom in, and click Set View.
              </p>
              
              <div style={{ 
                backgroundColor: '#f8f9fa', 
                padding: '15px', 
                borderRadius: '8px', 
                borderLeft: '4px solid #2b83ba',
                marginBottom: '20px'
              }}>
                <strong>Available Interactions:</strong>
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
        <div 
          ref={containerRef}
          className="vitessce-container" 
          style={{ flex: '1 1 auto', position: 'relative', margin: '0', padding: '0', border: '0', background: '#000' }}
        >
          {config ? (
            <Vitessce
              ref={vitessceRef}
              key={`${configKey}-${JSON.stringify(config?.datasets?.[0]?.files?.map(f => f.url))}`}
              config={config}
              onConfigChange={setConfig}
              theme="light"
              height={null}
              width={null}
            />
          ) : (
            <div style={{ padding: '20px', color: '#fff', textAlign: 'center' }}>
              Loading configuration...
            </div>
          )}
          {mouseCoords && (
            <div
              style={{
                position: 'absolute',
                top: '10%',
                right: '10px',
                transform: 'translateY(-50%)',
                padding: '8px 12px',
                backgroundColor: 'rgba(0, 0, 0, 0.85)',
                color: '#00ff00',
                fontSize: '13px',
                fontFamily: 'monospace',
                pointerEvents: 'none',
                zIndex: 10000,
                whiteSpace: 'nowrap',
                boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
                border: '1px solid rgba(0, 255, 0, 0.5)',
                borderRadius: '4px',
                fontWeight: '500',
                minWidth: '200px'
              }}
            >
              <div>X: {mouseCoords.x.toLocaleString()}</div>
              <div>Y: {mouseCoords.y.toLocaleString()}</div>
            </div>
          )}
        </div>

        <button
          onClick={() => setShowInstructions(true)}
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

        <div style={{ position: 'fixed', top: '15px', left: '10px', zIndex: 10, width: '24%', height: '30%' }}>
          <ROISelector 
            onSetView={handleSetView} 
            onHeatmapResults={handleHeatmapResults}
            onInteractionResults={handleInteractionResults}
            onGroupSelection={setSelectedGroups}
          />
        </div>

        {channelHeatmapResults?.channel_heatmaps && Object.keys(channelHeatmapResults.channel_heatmaps).length > 0 && (
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
              onClose={() => setChannelHeatmapResults(null)}
              onHeatmapClick={() => {}}
              onGroupToggle={handleGroupToggle}
            />
          </div>
        )}

        {interactionHeatmapResult && Object.keys(interactionHeatmapResult).length > 0 && (
          <div style={{ 
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
              onClose={() => setInteractionHeatmapResult(null)}
              onGroupToggle={handleGroupToggle}
            />
          </div>
        )}
      </div>
    </>
  );
};

export default MainView; 