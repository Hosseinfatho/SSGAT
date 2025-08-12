import React from 'react';
import Plot from 'react-plotly.js';

const InteractionHeatmap = ({ 
  interactionHeatmapResult, 
  activeGroups, 
  groupColors, 
  groupNames,
  onClose,
  onGroupToggle
}) => {
  if (!interactionHeatmapResult) return null;

  return (
    <div style={{ 
      background: 'rgba(0, 0, 0, 0.8)', 
      borderRadius: '8px', 
      padding: '15px',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      backdropFilter: 'blur(10px)',
      minWidth: '350px'
    }}>
      {/* Close Button */}
      <button 
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '5px',
          right: '5px',
          background: 'none',
          border: 'none',
          color: '#fff',
          fontSize: '16px',
          cursor: 'pointer',
          padding: '5px',
          borderRadius: '50%',
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        ×
      </button>

      {/* Title */}
      <h3 style={{ 
        color: 'white', 
        margin: '0 0 10px 0', 
        fontSize: '16px',
        textAlign: 'center',
        fontWeight: 'bold'
      }}>
        Interaction Heatmap
      </h3>
      
      {/* Interaction Checkboxes */}
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        gap: '4px',
        marginBottom: '10px'
      }}>
        {Object.entries(groupNames).map(([group, name]) => (
          <label key={group} style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            border: '1px solid rgba(255, 255, 255, 0.2)'
          }}>
            <input
              type="checkbox"
              checked={activeGroups[group]}
              onChange={() => onGroupToggle(group)}
              style={{ margin: 0, transform: 'scale(1.1)' }}
            />
            <span style={{ color: groupColors[group], fontWeight: 'bold', fontSize: '14px' }}>{name}</span>
          </label>
        ))}
      </div>

      {/* Selected Interaction Heatmaps */}
      {(() => {
        const activeGroupsList = Object.entries(activeGroups).filter(([group, isActive]) => isActive);
        if (activeGroupsList.length === 0) return null;
        
        // Create overlay data for all active groups with normalization
        const overlayData = activeGroupsList.map(([groupId], index) => {
          const groupKey = `group_${groupId}`;
          const groupData = interactionHeatmapResult.heatmaps[groupKey];
          if (!groupData) return null;
          
          // Normalize the data to 0-1 range with better visibility for small values
          const flatData = groupData.flat();
          const minVal = Math.min(...flatData);
          const maxVal = Math.max(...flatData);
          const range = maxVal - minVal;
          
          // Apply square root transformation to enhance small values
          const normalizedData = groupData.slice().reverse().map(row => 
            row.map(val => {
              if (range <= 0) return 0;
              const normalized = (val - minVal) / range;
              // Apply square root transformation to make small values more visible
              return Math.sqrt(normalized);
            })
          );
          
          return {
            z: normalizedData,
            type: 'heatmap',
            colorscale: [
              [0, 'rgba(0, 0, 0, 0)'],  // Black transparent
              [0.3, groupColors[groupId] + '30'], // 30% opacity
              [0.6, groupColors[groupId] + '60'], // 60% opacity
              [1, groupColors[groupId]] // Full opacity
            ],
            showscale: false,
            opacity: 1.0,
            name: groupNames[groupId]
          };
        }).filter(Boolean);
        
        if (overlayData.length === 0) return null;
        
        return (
          <div style={{ 
            display: 'flex',
            justifyContent: 'center'
          }}>
            <Plot
              data={overlayData}
              layout={{
                width: 320,
                height: 200,
                margin: { t: 20, b: 20, l: 20, r: 20 },
                paper_bgcolor: 'rgba(0, 0, 0, 0.1)',
                plot_bgcolor: 'rgba(0, 0, 0, 0.1)',
                xaxis: {
                  title: 'X',
                  titlefont: { color: 'white', size: 10 },
                  tickfont: { color: 'white', size: 8 },
                  showgrid: false,
                  showticklabels: true,
                  zeroline: false
                },
                yaxis: {
                  title: 'Y',
                  titlefont: { color: 'white', size: 10 },
                  tickfont: { color: 'white', size: 8 },
                  showgrid: false,
                  showticklabels: true,
                  zeroline: false
                }
              }}
              config={{ 
                displayModeBar: false,
                responsive: true
              }}
              style={{
                background: 'transparent'
              }}
            />
          </div>
        );
      })()}
    </div>
  );
};

export default InteractionHeatmap;
