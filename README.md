#  SSGAT: Spatial Feature Graph Attention Network

> **Advanced spatial biology analysis using Graph Attention Networks for cellular interaction discovery**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Online-brightgreen)](https://hosseinfatho.github.io/SSGAT/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)

##  Quick Start

### Live Demo
** [Try it online](https://hosseinfatho.github.io/SSGAT/)**

### Local Development
```bash
# Backend (Python)
cd backend
conda create -n SPA python=3.8
conda activate SPA
pip install -r requirements.txt
python server.py

# Frontend (React)
cd frontend
npm install
npm run dev
```

##  What it does

SSGAT analyzes spatial biological data to discover cellular interactions using:

- **Graph Attention Networks (GAT)** for pattern recognition
- **ROI Analysis** with scoring system
- **Interactive Visualization** with Vitessce
- **Multi-marker Analysis** for cellular interactions

## 🔬 Key Features

- **Interactive ROI Selection** - Navigate through regions of interest
- **Cellular Interaction Analysis** - B-cell infiltration, T-cell maturation, etc.
- **Real-time Heatmaps** - Visualize marker interactions
- **Score-based Filtering** - Find high-scoring regions automatically
- **Multi-dimensional Data** - Handle complex spatial datasets

##  Supported Interactions

- **B-cell infiltration**
- **T-cell maturation** 
- **Inflammatory zones**
- **Oxidative stress regulation**

##  Tech Stack

- **Backend**: Python, PyTorch, Graph Attention Networks
- **Frontend**: React, Vitessce, D3.js
- **Data**: OME-Zarr format
- **Deployment**: GitHub Pages

##  Project Structure

```
SSGAT/
├── backend/                    # Python backend processing
│   ├── data0.py               # Data loading and preprocessing from OME-Zarr
│   ├── download00.py          # Data download utilities
│   ├── create_segmentation1.py # Cell segmentation and mask generation
│   ├── merge_features2.py     # Feature extraction and merging
│   ├── build_graph_gat3.py    # Local ROI graph construction
│   ├── train_gat4.py          # GAT model training for different markers
│   ├── evaluate_gat5.py       # Model evaluation and performance metrics
│   ├── Extract_ROI6.py        # ROI extraction and scoring system
│   ├── generate_vitnesse_config_sdk7.py # Vitnesse visualization config
│   ├── surrogate_labeling.py  # Surrogate labeling for training
│   ├── models/                # Trained model files (*.pt)
│   ├── output/                # Generated outputs and results
│   └── graph_analysis/        # Graph statistics and visualizations
├── frontend/                  # React frontend for visualization
│   ├── src/
│   │   ├── components/        # React components (Mainview, ROISelector, etc.)
│   │   └── App.jsx           # Main application component
│   └── package.json
└── README.md
```

---

** Built for spatial biology research | 🚀 Deployed on GitHub Pages**
