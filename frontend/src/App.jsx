import React, { useState } from 'react';
import MainView from './components/Original';
import './App.css';

function App() {
  const [currentConfig, setCurrentConfig] = useState(null);
  const [showInstructions, setShowInstructions] = useState(false);

  const handleROISelection = (roiView) => {
    console.log('App: Received ROI selection:', roiView);
  };

  const toggleInstructions = () => {
    setShowInstructions(!showInstructions);
  };

  return (
    <div className="App">
      {/* Instruction Button - Top Right */}
      <button className="instruction-button" onClick={toggleInstructions}>
        Instruction
      </button>
      
      {/* Instruction Window - Top Right */}
      {showInstructions && (
        <div className="instruction-window">
          <div className="instruction-header">
            <span>How to explore detected ROIs</span>
            <button className="instruction-close" onClick={toggleInstructions}>×</button>
          </div>
          <div className="instruction-content">
              <h4><strong>Select Interaction Type in ROI Navigator</strong> </h4>
              <li><strong> Arrow controls:</strong> Browse ROIs</li>
              <li><strong> Set View:</strong> Zoom to selected ROI.</li>
              <li><strong>Heatmap:</strong> View Channels heatmap in this ROI.</li>
              <li><strong>Interaction: </strong>  View interaction heatmap in this ROI.</li>
          </div>
        </div>
      )}
      
      <MainView onSetView={handleROISelection} />
    </div>
  );
}

export default App;
