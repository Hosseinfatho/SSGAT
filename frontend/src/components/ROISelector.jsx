import React, { useState, useEffect } from 'react';
import Heatmaps from './Heatmaps';
import InteractionHeatmaps from './InteractionHeatmaps';



function ROISelector({ onSetView, onHeatmapResults, onInteractionResults, onGroupSelection }) {
  const [rois, setRois] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [interactionGroups, setInteractionGroups] = useState([]);

  // Notify parent component when selectedGroups changes
  useEffect(() => {
    console.log('ROISelector: selectedGroups changed to:', selectedGroups);
    
    // Notify parent component about group selection
    if (onGroupSelection) {
      onGroupSelection(selectedGroups);
    }
    
    // Config is now generated directly in frontend - no need to send to backend
  }, [selectedGroups, onGroupSelection]);

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
      if (container) {
        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;
        const screenDiagonal = Math.sqrt(screenWidth * screenWidth + screenHeight * screenHeight);
        
        // Calculate scale based on screen diagonal (approximate)
        let scale = 1.0;
        if (screenDiagonal > 3000) { // 32-inch and larger
          scale = 0.7;
        } else if (screenDiagonal > 2500) { // 27-inch
          scale = 0.75;
        } else if (screenDiagonal > 2000) { // 24-inch
          scale = 1.0;
        } else if (screenDiagonal > 1500) { // 16-inch laptop
          scale = 0.8;
        } else if (screenDiagonal > 1200) { // 13-inch laptop
          scale = 0.7;
        } else { // Tablet and smaller
          scale = 0.65;
        }
        
        container.style.transform = `scale(${scale})`;
        console.log(`ROI Navigator adjusted: screen diagonal ${screenDiagonal.toFixed(0)}px, scale ${scale}`);
      }
    };
    
    // Adjust size on mount and resize
    adjustROISize();
    window.addEventListener('resize', adjustROISize);
    
    // Cleanup
    return () => window.removeEventListener('resize', adjustROISize);
    
    // Don't load ROI data initially - wait for user selection
    console.log('ROISelector: Interaction types loaded, waiting for user selection');
  }, []);
  
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
      // Use API for local development - load from top5_roi files
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
      url = `${apiBaseUrl}/api/top5_roi_${filename}.json`;
    } else {
      // Use local JSON files for GitHub Pages
              url = `./data/top5_roi_${filename}.json`;
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
        
        // Handle top5_roi format (top_rois array)
        const roisArray = data.top_rois || [];
        console.log("ROISelector: roisArray:", roisArray);
        
        if (!Array.isArray(roisArray)) {
          console.error("ROISelector: Invalid ROI data structure:", data);
          return;
        }

        console.log("ROISelector: Processing", roisArray.length, "ROI features");
        console.log("ROISelector: First ROI sample:", roisArray[0]);

        // Use ROIs in original order from file (no sorting)
        const sortedRois = roisArray.slice(0, 4);
        console.log("ROISelector: ROIs in original order:", sortedRois);
        
        const extracted = sortedRois.map((roi, index) => {
          const roiId = roi.roi_id || (index + 1); // Use roi_id from file or fallback to index
          console.log("ROISelector: Processing ROI", roiId, "with score:", roi.scores.combined_score);
          console.log("ROISelector: Full ROI object:", roi);
          console.log("ROISelector: ROI position x:", roi.position.x, "y:", roi.position.y);
          const newTooltipName = `ROI_${roiId} Score: ${roi.scores.combined_score.toFixed(3)}`;
          
          // Calculate centroid from ROI position
          const centroid = [roi.position.x, roi.position.y];
          
          const extractedRoi = {
            id: newTooltipName,
            x: centroid[0],
            y: centroid[1],
            z: roi.position.z || 0, // Use z from file or default to 0
            score: roi.scores.combined_score, // Use actual score from file
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
  
  // Debug: Log currentROI to see what data we have
        console.log('ROISelector Debug - currentROI:', currentROI);
      console.log('ROISelector Debug - currentROI.score:', currentROI.score);
      console.log('ROISelector Debug - currentROI.x:', currentROI.x);
      console.log('ROISelector Debug - currentROI.y:', currentROI.y);
      console.log('ROISelector Debug - currentROI.roi_id:', currentROI.roi_id);
      console.log('ROISelector Debug - filteredRois length:', filteredRois.length);
      console.log('ROISelector Debug - currentIndex:', currentIndex);
      console.log('ROISelector Debug - all filteredRois:', filteredRois);
      console.log('ROISelector Debug - selectedGroups:', selectedGroups);

  const handleSetView = () => {
    if (currentROI && currentROI.x !== undefined && currentROI.y !== undefined) {
      // Transform coordinates: X = x*8, Y = (5508 - y*8) (flipped)
      const roiX = currentROI.x * 8;
      const roiY = 5508 - (currentROI.y * 8);
      
      // Find the interaction group for the current ROI
      const currentROIGroup = currentROI.interactions && currentROI.interactions.length > 0 
        ? currentROI.interactions[0] 
        : null;
      
      const viewConfig = {
        spatialTargetX: roiX,
        spatialTargetY: roiY,
        spatialZoom: -1.0,  // Moderate zoom to show ROI with range x±200, y±200
        refreshConfig: true,
        currentROIGroup: currentROIGroup, // Pass the current ROI group
        useSegmentationFile: true // Flag to indicate we want to use segmentation file
      };
      
      console.log('=== SET VIEW CALCULATION ===');
      console.log('Original coordinates from file:', currentROI.x, currentROI.y);
      console.log('X calculation:', currentROI.x, '* 8 =', roiX);
      console.log('Y calculation:', '5508 - (', currentROI.y, '* 8) = 5508 -', (currentROI.y * 8), '=', roiY);
      console.log('Setting view to ROI:', currentROI.id, 'at position:', roiX, roiY, 'with group:', currentROIGroup);
      console.log('Using segmentation file for ROI display');
      console.log('=== END SET VIEW CALCULATION ===');
      onSetView(viewConfig);
    } else {
      console.warn('No valid ROI selected for Set View');
    }
  };



  const toggleGroup = (group) => {
    console.log('ROISelector: ===== toggleGroup START =====');
    console.log('ROISelector: toggleGroup called with:', group);
    console.log('ROISelector: Current selectedGroups:', selectedGroups);
    console.log('ROISelector: Group already selected?', selectedGroups.includes(group));
    
    let newSelectedGroups;
    
    if (selectedGroups.includes(group)) {
      // If the group is already selected, unselect it
      newSelectedGroups = selectedGroups.filter(g => g !== group);
      console.log('ROISelector: Unselecting group, newSelectedGroups:', newSelectedGroups);
    } else {
      // If selecting a new group, unselect all others and select only this one
      newSelectedGroups = [group];
      console.log('ROISelector: Selecting new group, newSelectedGroups:', newSelectedGroups);
    }
    
    console.log('ROISelector: Setting new selectedGroups:', newSelectedGroups);
    setSelectedGroups(newSelectedGroups);
    setCurrentIndex(0);
    
    // Always load ROI data when selecting a group
    if (newSelectedGroups.length > 0) {
      console.log('ROISelector: About to call loadROIData with:', newSelectedGroups[0]);
      loadROIData(newSelectedGroups[0]);
    } else {
      console.log('ROISelector: No groups selected, not calling loadROIData');
    }
    
    // Notify parent component about the change with refreshConfig to update view
    console.log('ROISelector: Calling onSetView with:', {
      selectedGroups: newSelectedGroups,
      refreshConfig: true,
      spatialTargetX: 5454,
      spatialTargetY: 2600,
      spatialZoom: -3.0
    });
    
    onSetView({
      selectedGroups: newSelectedGroups,
      refreshConfig: true,
      spatialTargetX: 5454,  // Default center X
      spatialTargetY: 2600,  // Default center Y
      spatialZoom: -3.0      // Default zoom
    });
    
    console.log('ROISelector: ===== toggleGroup END =====');
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
        <p style={{ fontSize: '11px', marginBottom: '8px', color: '#000' }}>Please select an interaction type to view ROIs:</p>
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

  return (
    <div className="roi-selector-container">
      <h4 style={{ fontSize: '14px', marginBottom: '2px', fontWeight: '600', color: '#000' }}>ROI Navigator</h4>
             <p style={{ fontSize: '11px', marginBottom: '2px', color: '#000' }}>Select Interaction Type </p>
             {interactionGroups.map(group => {
               console.log('ROISelector: Rendering radio button for:', group, 'checked:', selectedGroups.includes(group));
               console.log('ROISelector: About to render div for:', group);
               return (
         <div 
           key={group} 
           onClick={() => {
             console.log('ROISelector: ===== DIV CLICK START =====');
             console.log('ROISelector: Div clicked for:', group);
             console.log('ROISelector: About to call toggleGroup with:', group);
             toggleGroup(group);
             console.log('ROISelector: ===== DIV CLICK END =====');
           }}
           style={{ 
             fontSize: '11px', 
             marginBottom: '1px', 
             color: '#000',
             cursor: 'pointer',
             padding: '2px 4px',
             backgroundColor: selectedGroups.includes(group) ? '#e0e0e0' : 'transparent',
             border: selectedGroups.includes(group) ? '1px solid #999' : '1px solid transparent',
             borderRadius: '3px'
           }}
         >
           <input
             type="radio"
             name="interactionType"
             value={group}
             checked={selectedGroups.includes(group)}
             readOnly
             style={{ marginRight: '4px', pointerEvents: 'none' }}
           />
           {group}
         </div>
       );
       })}
      


      <hr style={{ borderColor: "rgba(255, 255, 255, 0.2)" }} />
      {selectedGroups.length > 0 ? (
        <>
          <div className="text-center" style={{ marginBottom: "3px", display: "flex", justifyContent: "center", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "11px", fontWeight: "600", color: "#000" }}>
              {currentROI.roi_id ? `ROI ${currentROI.roi_id}` : `ROI ${currentIndex + 1}`}
            </span>
            <span style={{ fontSize: "10px", fontWeight: "bold", color: "#000" }}>
              Score: {currentROI.score ? currentROI.score.toFixed(3) : "0.000"}
            </span>
          </div>



          <div className="text-center" style={{ marginBottom: "1px" }}>
            <button 
              onClick={prev}
              className="btn"
              style={{ marginRight: "3px", padding: "3px 6px", fontSize: "11px" }}
            >
              ←
            </button>
            <button 
              onClick={() => handleSetView()}
              className="btn"
              style={{ marginRight: "3px", padding: "4px 10px", fontSize: "11px" }}
            >
              Set View
            </button>
            <button 
              onClick={next}
              className="btn"
              style={{ padding: "3px 6px", fontSize: "11px" }}
            >
              →
            </button>
          </div>

          {/* Analysis Buttons - Only show in local development */}
          {(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && (
            <div className="text-center" style={{ marginTop: "1px", display: "flex", justifyContent: "center", gap: "1px" }}>
              <Heatmaps 
                currentROI={currentROI}
                onHeatmapResults={onHeatmapResults}
                selectedInteractionType={selectedGroups[0]}
                selectedROIIndex={currentIndex}
              />
              <InteractionHeatmaps 
                currentROI={currentROI}
                onInteractionResults={onInteractionResults}
              />
            </div>
          )}
                </>
      ) : null}
    </div>
  );
}

export default ROISelector;
