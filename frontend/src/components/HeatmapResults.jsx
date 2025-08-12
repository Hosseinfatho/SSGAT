import React from 'react';
import Plot from 'react-plotly.js';

// Function to convert RGB color to Plotly colorscale with emphasis on small values
const rgbToColorscale = (rgbColor) => {
  const [r, g, b] = rgbColor;
  return [
    [0, 'rgba(0, 0, 0, 0)'],  // Black transparent
    [0.1, `rgba(${r/2}, ${g/2}, ${b/2}, 0.4)`],  // Emphasize small values
    [0.3, `rgba(${r/1.5}, ${g/1.5}, ${b/1.5}, 0.6)`],
    [0.6, `rgba(${r/1.2}, ${g/1.2}, ${b/1.2}, 0.8)`],
    [1, `rgba(${r}, ${g}, ${b}, 1)`]
  ];
};

const HeatmapResults = ({ 
  heatmapResults, 
  interactionHeatmapResult, 
  activeGroups, 
  groupColors, 
  groupNames,
  imageChannels,
  onClose,
  onHeatmapClick,
  onGroupToggle
}) => {
  if (!heatmapResults) return null;

  return (
    <>
      <button 
        onClick={onClose}
        className="btn-close"
        style={{
          position: 'absolute',
          top: '-30px',
          right: '0px',
          zIndex: 1002,
          background: 'red',
          color: 'white',
          border: 'none',
          borderRadius: '50%',
          width: '25px',
          height: '25px',
          cursor: 'pointer',
          fontSize: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        ×
      </button>

      {/* Regular Heatmaps - Horizontal Layout */}
      {heatmapResults && heatmapResults.channel_heatmaps && Object.keys(heatmapResults.channel_heatmaps).length > 0 && (
                 <div className="heatmap-grid" style={{ 
           position: 'fixed', 
           bottom: '10px', 
           left: '600px', 
           zIndex: 1001, 
           backgroundColor: 'transparent', 
           width: '1000px', 
           overflow: 'visible',
           display: 'flex',
           flexDirection: 'row',
           gap: '0px',
           flexWrap: 'nowrap',
           alignItems: 'flex-start'
         }}>
          
          {Object.entries(heatmapResults.channel_heatmaps).map(([channelName, channelData], index) => (
            <div key={`${channelName}-${index}`} style={{ 
              position: 'relative',
              minWidth: '180px',
              flexShrink: 0,
              background: 'transparent'
            }}>

              <Plot
                data={[{
                  z: channelData.slice().reverse(),
                  type: 'heatmap',
                  colorscale: imageChannels && imageChannels[channelName] ? 
                    rgbToColorscale(imageChannels[channelName].color) : [
                      [0, 'rgba(0, 0, 0, 0)'],
                      [0.1, 'rgba(68, 1, 84, 0.4)'],
                      [0.3, 'rgba(59, 82, 139, 0.6)'],
                      [0.6, 'rgba(33, 145, 140, 0.8)'],
                      [1, 'rgba(94, 201, 98, 1)']
                    ],
                  hoverongaps: false,
                  hovertemplate: 'X: %{x}<br>Y: %{y}<br>Intensity: %{z:.3f}<extra></extra>'
                }]}
                                 layout={{
                   width: 180,
                   height: 150,
                   margin: { t: 25, b: 5, l: 2, r: 2 },
                   paper_bgcolor: 'rgba(0, 0, 0, 0.1)',
                   plot_bgcolor: 'rgba(0, 0, 0, 0.1)',
                   title: {
                     text: channelName,
                     font: { color: 'white', size: 14 },
                     x: 0.5
                   },
                   xaxis: {
                     title: 'X',
                     titlefont: { color: 'white', size: 10 },
                     tickfont: { color: 'white', size: 8 },
                     showgrid: false
                   },
                   yaxis: {
                     title: 'Y',
                     titlefont: { color: 'white', size: 10 },
                     tickfont: { color: 'white', size: 8 },
                     showgrid: false
                   }
                 }}
                config={{ 
                  displayModeBar: false,
                  responsive: true
                }}
                onClick={onHeatmapClick}
                style={{
                  background: 'transparent'
                }}
              />
            </div>
          ))}
        </div>
      )}
    </>
  );
};

export default HeatmapResults; 