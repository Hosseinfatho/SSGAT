import React from 'react';
import MainView from './components/Original';
import './App.css';

function App() {
  const handleROISelection = (roiView) => {
    console.log('App: Received ROI selection:', roiView);
  };

  return (
    <div className="App">
      <MainView onSetView={handleROISelection} />
    </div>
  );
}

export default App;
