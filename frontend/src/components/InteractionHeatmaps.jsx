import React, { useState } from 'react';

function InteractionHeatmaps({ currentROI, onInteractionResults }) {
  const [isAnalyzingInteractionHeatmap, setIsAnalyzingInteractionHeatmap] = useState(false);

  const analyzeInteractionHeatmap = async () => {
    setIsAnalyzingInteractionHeatmap(true);
    try {
      const factor = 1;
      const roiSize = 200;

      const x = Number(currentROI.x) || 0;
      const y = Number(currentROI.y) || 0;

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

      const response = await fetch('http://localhost:5000/api/analyze_interaction_heatmap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ roi })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze interaction heatmap');
      }

      const data = await response.json();
      onInteractionResults(data);
    } catch (error) {
      console.error('Error analyzing interaction heatmap:', error);
      alert('Error analyzing interaction heatmap: ' + error.message);
    } finally {
      setIsAnalyzingInteractionHeatmap(false);
    }
  };

  return (
    <div>
      <button 
        onClick={analyzeInteractionHeatmap}
        disabled={isAnalyzingInteractionHeatmap}
        style={{
          backgroundColor: '#6f42c1',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          padding: '6px 12px',
          fontSize: '12px',
          marginRight: '4px',
          cursor: isAnalyzingInteractionHeatmap ? 'not-allowed' : 'pointer'
        }}
      >
        {isAnalyzingInteractionHeatmap ? 'Analyzing...' : 'Interactions'}
      </button>
    </div>
  );
}

export default InteractionHeatmaps; 