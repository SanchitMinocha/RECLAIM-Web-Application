# RECLAIM: End-to-End Reservoir Sedimentation ML Pipeline

![Pipeline Workflow](https://img.shields.io/badge/Workflow-ML--Deployment-blue)
![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)
![Django serving](https://img.shields.io/badge/serving-Django--4.2-092e20)

RECLAIM is an end-to-end Machine Learning deployment pipeline designed to automate the estimation of reservoir capacity loss. The system orchestrates raw GIS data ingestion, automated feature engineering, and high-fidelity inference to serve actionable hydrological insights.

---

## 🏗️ Pipeline Architecture

The RECLAIM pipeline is divided into four distinct phases:

### phase 1: Data Ingestion & Inflow
- **GIS Ingestion**: Support for multi-source uploads including GeoJSON catchment boundaries and reservoir polygons.
- **Time-Series Inflow**: Integrated processing of meteorological CSVs (Precipitation, Temperature, Wind) and reservoir operational data (AEC curves, Inflow/Outflow).
- **Sample Data Pipeline**: Pre-validated datasets for rapid benchmarking and automated form populating.

### Phase 2: Automated Feature Engineering
Located in the `reclaim/` core, this stage transforms raw spatial and temporal data:
- **Spatial Alignment**: Automated CRS re-projection to EPSG:4326 for global consistency.
- **Feature Generation**: Extraction of catchment-specific attributes and environmental variables from global NetCDF datasets (Land cover, Terrain, Soil types).
- **Session-Based Storage**: Isolated data preprocessing in unique job directories to ensure multi-user concurrency.

### Phase 3: Model Inference & Synthesis
- **Predictive Engine**: Execution of the RECLAIM sedimentation model using calculated features and user parameters.
- **Trend Synthesis**: Interpolation of sedimentation rates across selected observation periods (1900–Current).
- **Data Validation**: Schema enforcement for meteorological and operational files to ensure inference stability.

### Phase 4: Serving & Visualization (The Interface)
- **Interactive Serving**: A Django-driven REST/Web interface for model triggering.
- **GIS Visualization**: Real-time Leaflet.js rendering of processed catchment and reservoir geometries.
- **Insight Delivery**: Professional Plotly visualization of time-series forecasts and metadata synthesis.
- **Export Layer**: Automated CSV generation of predicted time-series for downstream MLOps consumption.

---

## 🚀 Deployment Guide

### Environment Initialization
```bash
git clone https://github.com/SanchitMinocha/RECLAIM-Web-Application.git
cd RECLAIM-Web-Application
python3 -m venv .reclaim_webapp_env
source .reclaim_webapp_env/bin/activate
pip install -r requirements.txt
```

### Serving the Pipeline
1. **Apply Migrations**: `python manage.py migrate`
2. **Launch Server**: `python manage.py runserver`
3. **Admin Monitoring**: Access `/admin` to monitor model metadata and trigger system-wide cleanup.

---

## 🛠️ System Configuration

### Storage Management
The pipeline includes an **Automated Cleanup Routine** to manage heavy GIS files:
- **Toggle**: Controls available via `FileCleanupSettings` in the Admin Dashboard.
- **Mechanism**: Auto-purges job-specific directories in `uploaded_files/` post-inference.

### Heavy Data Optimization
Large global datasets (NetCDF/Heavy GeoJSON) are handled outside the main Git tree to keep the deployment package optimized. Refer to `.gitignore` for data exclusion rules.

---

## 📊 Pipeline Components

| Component | Responsibility | Technology |
| :--- | :--- | :--- |
| **Ingestion Engine** | Geo-spatial & CSV file handling | `geopandas`, `django-fs` |
| **Feature Generator** | NetCDF data extraction & engineering | `reclaim.gf`, `numpy` |
| **Inference Layer** | Core estimation logic | `reclaim.Reclaim` |
| **Service UI** | Glassmorphic dashboard & serving | `vanilla-js`, `leaflet` |

**Lead Developer**: Joshua Zhao  
**Project Lead & Mentor**: Sanchit Minocha
