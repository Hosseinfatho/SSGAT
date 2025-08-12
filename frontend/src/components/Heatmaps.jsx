import React, { useState } from 'react';

function Heatmaps({ currentROI, onHeatmapResults }) {
  const [isAnalyzingHeatmaps, setIsAnalyzingHeatmaps] = useState(false);

  const SPECIFIC_CHANNELS = ['CD31', 'CD11b', 'Catalase', 'CD4', 'CD20', 'CD11c'];

  const analyzeHeatmaps = async () => {
    setIsAnalyzingHeatmaps(true);
    try {
      const factor = 1;
      const roiSize = 200;

      const x = Number(currentROI.x) || 0;
      const y = 688-Number(currentROI.y) || 0;

      const roi = {
        xMin: Math.max(0, Math.floor((x - roiSize/2) / factor)),
        xMax: Math.min(1363, Math.floor((x + roiSize/2) / factor)),
        yMin: Math.max(0, Math.floor((y - roiSize/2) / factor)),
        yMax: Math.min(688, Math.floor((y + roiSize/2) / factor)),
        zMin: 0,
        zMax: 193
      };

      const xRange = roi.xMax - roi.xMin;
      const yRange = roi.yMax - roi.yMin;
      const maxRange = Math.max(xRange, yRange);

      const centerX = (roi.xMin + roi.xMax) / 2;
      const centerY = (roi.yMin + roi.yMax) / 2;

      roi.xMin = Math.max(0, Math.floor(centerX - maxRange/2));
      roi.xMax = Math.min(1363, Math.floor(centerX + maxRange/2));
      roi.yMin = Math.max(0, Math.floor(centerY - maxRange/2));
      roi.yMax = Math.min(688, Math.floor(centerY + maxRange/2));

      const response = await fetch('http://localhost:5000/api/analyze_heatmaps', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          roi,
          channels: SPECIFIC_CHANNELS,
          range: {
            min: 0,
            max: 1
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze heatmaps');
      }

      const data = await response.json();
      onHeatmapResults(data);
    } catch (error) {
      console.error('Error analyzing heatmaps:', error);
      alert('Error analyzing heatmaps: ' + error.message);
    } finally {
      setIsAnalyzingHeatmaps(false);
    }
  };

  return (
    <div>
      <button 
        onClick={analyzeHeatmaps}
        disabled={isAnalyzingHeatmaps}
        style={{
          backgroundColor: '#ffc107',
          color: 'black',
          border: 'none',
          borderRadius: '4px',
          padding: '6px 12px',
          fontSize: '12px',
          marginInlineStart: '60px',
          cursor: isAnalyzingHeatmaps ? 'not-allowed' : 'pointer'
        }}
      >
        {isAnalyzingHeatmaps ? 'Analyzing...' : 'Heatmaps'}
      </button>
    </div>
  );
}

export default Heatmaps; 