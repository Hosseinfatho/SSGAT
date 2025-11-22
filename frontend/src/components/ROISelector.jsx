import React, { useState, useEffect } from 'react';
import Heatmaps from './Heatmaps';
import InteractionHeatmaps from './InteractionHeatmaps';



function ROISelector({ onSetView, onHeatmapResults, onInteractionResults, onGroupSelection }) {
  const [rois, setRois] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedGroups, setSelectedGroups] = useState(['B-cell infiltration']); // For Tissue Microenvironment (channels)
  const [selectedROIGroups, setSelectedROIGroups] = useState([]); // For ROI Navigator (overlay)
  const [interactionGroups, setInteractionGroups] = useState([]);

  // Notify parent component when selectedGroups (Tissue Microenvironment) changes
  useEffect(() => {
    console.log('ROISelector: selectedGroups (Tissue Microenvironment) changed to:', selectedGroups);
    
    // Notify parent component about group selection for channels
    if (onGroupSelection) {
      onGroupSelection(selectedGroups);
    }
    
    // Don't trigger config refresh here - only when Set View is pressed
  }, [selectedGroups, onGroupSelection]);

  // Notify parent component when selectedROIGroups (ROI Navigator) changes
  useEffect(() => {
    console.log('ROISelector: selectedROIGroups (ROI Navigator) changed to:', selectedROIGroups);
    
    // Notify parent about ROI overlay selection
    if (onGroupSelection) {
      // Pass both channel selection and ROI overlay selection
      onGroupSelection({
        channels: selectedGroups,
        roiOverlay: selectedROIGroups
      });
    }
  }, [selectedROIGroups, selectedGroups, onGroupSelection]);

  const computeCentroid = (allCoords) => {
    const flatCoords = allCoords.flat();
    const sum = flatCoords.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
    return [sum[0] / flatCoords.length, sum[1] / flatCoords.length];
  };

  useEffect(() => {
    console.log('ROISelector: Starting to fetch ROI data...');
    
    // Define available interaction types and their corresponding files - updated
    const interactionTypes = [
      'B-cell infiltration',
      'T-cell maturation',
      'Inflammatory zone', 
      'Oxidative stress regulation'
    ];
    
    setInteractionGroups(interactionTypes);
    
    // Adaptive sizing based on screen size
    const adjustROISize = () => {
      const container = document.querySelector('.roi-selector-container');
    };
    
    // Adjust size on mount and resize
    adjustROISize();
    window.addEventListener('resize', adjustROISize);
    
    // Cleanup
    return () => window.removeEventListener('resize', adjustROISize);
  }, []);

  // Separate useEffect to load initial ROI data
  useEffect(() => {
    if (selectedGroups.length > 0) {
      loadROIData(selectedGroups[0]);
    }
  }, [selectedGroups]);
  
  const loadROIData = (interactionType) => {
    console.log('ROISelector: ===== loadROIData START =====');
    console.log('ROISelector: Loading ROI data for:', interactionType);
    console.log('ROISelector: Current hostname:', window.location.hostname);
    
    // Convert interaction type to filename format
    const filename = interactionType.replace(/\s+/g, '_');
    console.log('ROISelector: Generated filename:', filename);
    
    // Use local JSON files for GitHub Pages, API for local development
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    console.log('ROISelector: isLocalhost:', isLocalhost);
    
    let url;
    if (isLocalhost) {
      // Use API for local development - load from top5_roi_scores files
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
      url = `${apiBaseUrl}/api/top5_roi_scores_${filename}.json`;
    } else {
      // Use local JSON files for GitHub Pages
      // Convert underscores back to spaces for filename matching
      const filenameWithSpaces = filename.replace(/_/g, ' ');
      url = `./top5_roi_scores_${filenameWithSpaces}.json`;
    }
    
    console.log('ROISelector: Generated URL:', url);
    
    fetch(url)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        console.log("ROISelector: Received ROI data for", interactionType, ":", data);
        console.log("ROISelector: Data keys:", Object.keys(data));
        
        // Handle different possible data structures
        let roisArray = [];
        if (data.top_rois && Array.isArray(data.top_rois)) {
          roisArray = data.top_rois;
        } else if (Array.isArray(data)) {
          roisArray = data;
        } else if (data.features && Array.isArray(data.features)) {
          roisArray = data.features;
        } else {
          console.error("ROISelector: Invalid ROI data structure:", data);
          console.log("ROISelector: Available keys:", Object.keys(data));
          return;
        }
        
        console.log("ROISelector: roisArray:", roisArray);
        
        if (roisArray.length === 0) {
          console.warn("ROISelector: No ROI data found");
          setRois([]);
          return;
        }

        console.log("ROISelector: Processing", roisArray.length, "ROI features");
        console.log("ROISelector: First ROI sample:", roisArray[0]);

        // Use ROIs in original order from file (no sorting) - take top 5
        const sortedRois = roisArray.slice(0, 5);
        console.log("ROISelector: ROIs in original order:", sortedRois);
        
        const extracted = sortedRois.map((roi, index) => {
          const roiId = roi.roi_id || (index + 1); // Use roi_id from file or fallback to index
          console.log("ROISelector: Processing ROI", roiId, "with score:", roi.scores?.combined_score);
          console.log("ROISelector: Full ROI object:", roi);
          console.log("ROISelector: ROI position x:", roi.position?.x, "y:", roi.position?.y);
          
          // Add safety checks for missing data
          // Use nullish coalescing to only default to 0 if score is null/undefined, not if it's 0
          const score = roi.scores?.combined_score ?? 0;
          const x = roi.position?.x || 0;
          const y = roi.position?.y || 0;
          
          const newTooltipName = `ROI_${roiId} Score: ${score.toFixed(3)}`;
          
          // Calculate centroid from ROI position
          const centroid = [x, y];
          
          const extractedRoi = {
            id: newTooltipName,
            x: centroid[0],
            y: centroid[1],
            z: roi.position?.z || 0, // Use z from file or default to 0
            score: score, // Use actual score from file
            interactions: [interactionType], // Use the current interaction type
            tooltip_name: newTooltipName,
            roi_id: roiId, // Use roi_id from file
            raw: roi,
            useTop5RoiFile: true // Flag to indicate we want to use top5_roi file
          };
          
          console.log("ROISelector: Extracted ROI", roiId, ":", extractedRoi);
          return extractedRoi;
        });

        console.log("ROISelector: Final extracted ROIs:", extracted);
        setRois(extracted);
      })
      .catch((err) => {
        console.error("ROISelector: Failed to load ROI data for", interactionType, ":", err);
        console.error("ROISelector: URL attempted:", url);
        setRois([]);
      });
  };

  // Notify parent component when selectedGroups changes
  // useEffect(() => {
  //   if (selectedGroups.length > 0) {
  //     onSetView({
  //       selectedGroups: selectedGroups
  //     });
  //   }
  // }, [selectedGroups, onSetView]);

  // Use the loaded ROI data instead of the rois from Original.jsx
  const filteredRois = rois;

  console.log('ROISelector Debug:', {
    totalRois: rois.length,
    selectedGroups,
    filteredRois: filteredRois.length,
    sampleRoi: rois[0] ? {
      id: rois[0].id,
      interactions: rois[0].interactions,
      score: rois[0].score
    } : null
  });

  const currentROI = filteredRois[currentIndex] || {};
  
  // Debug logging for current ROI
  console.log('ROISelector: Current ROI debug:', {
    currentIndex,
    totalRois: filteredRois.length,
    currentROI,
    roi_id: currentROI.roi_id,
    score: currentROI.score
  });
  


  const handleSetView = () => {
    if (currentROI && currentROI.x !== undefined && currentROI.y !== undefined) {
      // Transform coordinates: X = x*8, Y = (5508 - y*8) (flipped)
      const roiX = currentROI.x * 8;
      const roiY = (currentROI.y * 8);
      
      // Find the interaction group for the current ROI
      const currentROIGroup = currentROI.interactions && currentROI.interactions.length > 0 
        ? currentROI.interactions[0] 
        : (selectedROIGroups.length > 0 ? selectedROIGroups[0] : null);
      
      console.log('ROISelector: Set View for ROI:', {
        roi_id: currentROI.roi_id,
        x: currentROI.x,
        y: currentROI.y,
        transformedX: roiX,
        transformedY: roiY,
        interactionType: currentROIGroup
      });
      
      const viewConfig = {
        spatialTargetX: roiX,
        spatialTargetY: roiY,
        spatialZoom: -1.0,  // Moderate zoom to show ROI with range x±200, y±200
        refreshConfig: true,  // Only refresh config when Set View is pressed
        currentROIGroup: currentROIGroup, // Pass the current ROI group
        selectedROIGroups: selectedROIGroups.length > 0 ? selectedROIGroups : (currentROIGroup ? [currentROIGroup] : []), // Pass ROI overlay groups to show circles
        useSegmentationFile: true, // Flag to indicate we want to use segmentation file
        selectedROI: currentROI  // Pass the full ROI data for interaction calculations
      };
      

      onSetView(viewConfig);
    } else {
      console.warn('No valid ROI selected for Set View');
    }
  };



  const toggleGroup = (group) => {
    // Toggle for Tissue Microenvironment (channels)
    let newSelectedGroups;
    
    if (selectedGroups.includes(group)) {
      newSelectedGroups = selectedGroups.filter(g => g !== group);
    } else {
      newSelectedGroups = [group];
    }
    
    setSelectedGroups(newSelectedGroups);
    
    // Notify parent about channel selection
    if (onGroupSelection) {
      onGroupSelection({
        channels: newSelectedGroups,
        roiOverlay: selectedROIGroups
      });
    }
  };

  const toggleROIGroup = (group) => {
    // Toggle for ROI Navigator (overlay)
    let newSelectedROIGroups;
    
    if (selectedROIGroups.includes(group)) {
      newSelectedROIGroups = selectedROIGroups.filter(g => g !== group);
      console.log('ROISelector: Unselecting ROI group, newSelectedROIGroups:', newSelectedROIGroups);
    } else {
      newSelectedROIGroups = [group];
      console.log('ROISelector: Selecting ROI group, newSelectedROIGroups:', newSelectedROIGroups);
    }
    
    setSelectedROIGroups(newSelectedROIGroups);
    setCurrentIndex(0);
    
    // Notify parent about ROI overlay selection
    if (onGroupSelection) {
      onGroupSelection({
        channels: selectedGroups,
        roiOverlay: newSelectedROIGroups
      });
    }
    
    onSetView({
      selectedROIGroups: newSelectedROIGroups,
      refreshConfig: true  // Refresh config to show/hide overlay
    });
  };

  const next = () => {
    console.log('ROISelector: Next button clicked, currentIndex:', currentIndex, 'filteredRois.length:', filteredRois.length);
    setCurrentIndex(i => {
      const newIndex = (i + 1) % filteredRois.length;
      console.log('ROISelector: Next - new index:', newIndex);
      return newIndex;
    });
  };

  const prev = () => {
    console.log('ROISelector: Prev button clicked, currentIndex:', currentIndex, 'filteredRois.length:', filteredRois.length);
    setCurrentIndex(i => {
      const newIndex = (i - 1 + filteredRois.length) % filteredRois.length;
      console.log('ROISelector: Prev - new index:', newIndex);
      return newIndex;
    });
  };

  if (interactionGroups.length === 0) {
    return <p>Loading ROIs or no interactions found...</p>;
  }

  if (selectedGroups.length === 0) {
    return (
      <div className="roi-selector-container">
        <h4 style={{ fontSize: '14px', marginBottom: '8px', fontWeight: '600', color: '#000' }}>ROI Navigator</h4>
        <p style={{ fontSize: '11px', marginBottom: '8px', color: '#000' }}>Available interaction types:</p>
        {interactionGroups.map(group => (
          <label key={group} className="checkbox-item" style={{ fontSize: '11px', marginBottom: '4px', color: '#000' }}>
            <input
              type="radio"
              name="interactionType"
              checked={selectedGroups.includes(group)}
              onChange={() => toggleGroup(group)}
              style={{ marginRight: '6px' }}
            />
            {group}
          </label>
        ))}
      </div>
    );
  }

  // Define interaction order and labels with their channels
  const interactionOrder = [
    { id: 1, name: 'T-cell maturation', channels: ['CD3E', 'CD4', 'CD8a', 'PD1', 'LAG3', 'CD103'] },
    { id: 2, name: 'Inflammatory zone', channels: ['CD11b', 'CD11c', 'CD163', 'CD31', 'S100A', 'SOX10'] },
    { id: 3, name: 'Oxidative stress regulation', channels: ['Catalase', 'COX-IV', 'y-H2AX', 'H3K27me3', 'CyclinD1', 'B-catenin'] },
    { id: 4, name: 'B-cell infiltration', channels: ['CD20'] }
  ];

  return (
    <div className="roi-selector-container" style={{ width: '100%', height: '100%' }}>
      <h4 style={{ fontSize: '16px', marginBottom: '4px', fontWeight: '600', color: '#000' }}>Tissue Microenvironment</h4>
      {interactionOrder.map(({ id, name }) => {
        const isSelected = selectedGroups.includes(name);
        return (
          <div 
            key={name} 
            onClick={() => {
              toggleGroup(name);
              console.log('ROISelector: ===== DIV CLICK ND =====');
            }}
            style={{ 
              fontSize: '13px', 
              marginBottom: '2px', 
              color: '#000',
              cursor: 'pointer',
              padding: '2px 6px',
              backgroundColor: isSelected ? '#e0e0e0' : 'transparent',
              border: isSelected ? '1px solid #999' : '1px solid transparent',
              borderRadius: '3px'
            }}
          >
            <input
              type="radio"
              name="interactionType"
              value={name}
              checked={isSelected}
              readOnly
              style={{ marginRight: '6px', pointerEvents: 'none' }}
            />
            <span>{name}</span>
          </div>
        );
      })}
      
      <hr style={{ borderColor: "rgba(0, 0, 0, 0.2)", margin: '6px 0' }} />
      
      <h4 style={{ fontSize: '16px', marginBottom: '4px', fontWeight: '600', color: '#000' }}>ROI Navigator</h4>
      {interactionOrder.map(({ id, name }) => {
        const isSelected = selectedROIGroups.includes(name);
        return (
          <div 
            key={`roi-${name}`} 
            onClick={() => {
              toggleROIGroup(name);
            }}
            style={{ 
              fontSize: '13px', 
              marginBottom: '2px', 
              color: '#000',
              cursor: 'pointer',
              padding: '2px 6px',
              backgroundColor: isSelected ? '#e0e0e0' : 'transparent',
              border: isSelected ? '1px solid #999' : '1px solid transparent',
              borderRadius: '3px'
            }}
          >
            <input
              type="radio"
              name="roiNavigator"
              value={name}
              checked={isSelected}
              readOnly
              style={{ marginRight: '6px', pointerEvents: 'none' }}
            />
            <span>{name}</span>
          </div>
        );
      })}

      <hr style={{ borderColor: "rgba(255, 255, 255, 0.2)", margin: '12px 0' }} />
      {selectedROIGroups.length > 0 ? (
        <>
                     <div className="text-center" style={{ marginBottom: "3px", display: "flex", justifyContent: "center", alignItems: "center", gap: "6px" }}>
             <span style={{ fontSize: "14px", fontWeight: "600", color: "#000" }}>
               {currentROI.roi_id ? `ROI ${currentROI.roi_id}` : `ROI ${currentIndex + 1}`}
             </span>
             <span style={{ fontSize: "12px", fontWeight: "bold", color: "#000" }}>
               Score: {currentROI.score !== undefined && currentROI.score !== null ? currentROI.score.toFixed(3) : (currentROI.raw?.scores?.combined_score !== undefined ? currentROI.raw.scores.combined_score.toFixed(3) : "0.000")}
             </span>
           </div>

           <div className="text-center" style={{ marginBottom: "1px", display: "flex", justifyContent: "center", alignItems: "center", gap: "5px", marginLeft: "10px" }}>
             <button 
               onClick={prev}
               className="btn"
               style={{ padding: "3px 6px", fontSize: "14px" }}
             >
               ←
             </button>
             <button 
               onClick={() => handleSetView()}
               className="btn"
               style={{ padding: "4px 10px", fontSize: "14px" }}
             >
               Set View
             </button>
             <button 
               onClick={next}
               className="btn"
               style={{ padding: "3px 6px", fontSize: "14px" }}
             >
               →
             </button>
             
             {/* Analysis Buttons - Only show in local development */}
             {(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && (
               <>
                 <Heatmaps 
                   currentROI={currentROI}
                   onHeatmapResults={onHeatmapResults}
                   selectedInteractionType={selectedROIGroups[0] || selectedGroups[0]}
                   selectedROIIndex={currentIndex}
                 />
                 <InteractionHeatmaps 
                   currentROI={currentROI}
                   onInteractionResults={onInteractionResults}
                 />
               </>
             )}
           </div>
                </>
      ) : null}
    </div>
  );
}

export default ROISelector;
