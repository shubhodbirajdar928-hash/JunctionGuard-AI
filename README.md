## 📖 Overview

A real-time, explainable AI surveillance platform that scores accident-prone road junctions across India. It combines computer vision (YOLOv8), historical accident analytics, and crowdsourced citizen reports to produce a transparent, weighted risk score for each monitored junction — helping traffic authorities proactively identify and address danger zones *before* accidents happen.

> India records ~1.5 lakh road fatalities annually. This platform turns passive CCTV footage and open data into actionable, junction-level safety intelligence.

---

## 🚀 Live Demo

> 🔗 **[https://junctionguard-ai.onrender.com](https://junctionguard-ai.onrender.com)**
>
> *(Note: Render free tier may spin down after inactivity — allow ~30 seconds for cold start)*

---

## ✨ Features

### 📊 Real-Time Command Dashboard
- KPI overview: total junctions, HIGH/MEDIUM/LOW risk counts, active alerts
- Junction selector, time-range filter, and risk-level multi-select

### 🗺️ Interactive Alert Map
- **Folium-powered map** with 3 tile modes: Satellite (Esri), Street (OSM), Dark Tactical
- **Pulsing red radar halos** on HIGH-risk junctions (animated CSS rings)
- HeatMap overlay for accident density, MarkerCluster for grouped markers
- Click-on-map → auto-syncs junction to sidebar

### ⚖️ Explainability & Factor Breakdown
- Every risk score broken into **5 weighted contributing factors**:
  | Factor | Weight |
  |---|---|
  | Historical Accident Severity (Kaggle dataset) | 30% |
  | Traffic Density & Flow Velocity | 20% |
  | Near-Miss / Conflict Proximity Index | 20% |
  | Pedestrian Activity Level | 15% |
  | Citizen Hazard Reports | 15% |
- Visual weight bars and hover explanations per junction

### 📹 Live CCTV Vision Analytics
- **YOLOv8n** inference detecting: Cars, Motorcycles, Buses, Trucks, Pedestrians
- Color-coded bounding boxes; **Two-Wheeler Share %** metric for Indian traffic
- Frame-by-frame JSON/CSV detection reports
- OpenCV contour fallback when YOLO is offline (demo mode)
- Live stream URL ingestion via `yt-dlp`

### 🚨 Citizen Hazard Reporting
- **HTML5 GPS auto-detection** + IP geolocation fallback
- Haversine distance snap to nearest junction
- Photo/video evidence upload
- AI-generated safety recommendations per hazard type
- Synced to SQLite + Supabase cloud

---

## 🏗️ Technical Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  JUNCTIONGUARD AI PLATFORM                   │
│                  Streamlit Web Dashboard                     │
└───────┬──────────────────┬───────────────────┬──────────────┘
        │                  │                   │
 ┌──────▼──────┐    ┌──────▼──────┐    ┌───────▼──────┐
 │Vision Module│    │ Risk Engine │    │ Citizen      │
 │ YOLOv8n     │    │ 5-Factor    │    │ Reporting    │
 │ OpenCV      │    │ Weighted    │    │ Portal       │
 └──────┬──────┘    └──────┬──────┘    └───────┬──────┘
        │                  │                   │
 ┌──────▼──────┐    ┌──────▼──────┐    ┌───────▼──────┐
 │Frame Extract│    │Kaggle India │    │SQLite DB +   │
 │ @ 0.5s intvl│    │Accident Data│    │JSON Reports  │
 └─────────────┘    │  (3,000 rec)│    │+ Supabase    │
                    └─────────────┘    └──────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit ≥ 1.30 |
| **Mapping** | Folium ≥ 0.15, streamlit-folium, Esri ArcGIS + OSM tiles |
| **Computer Vision** | YOLOv8n (Ultralytics ≥ 8.1), OpenCV-headless ≥ 4.8 |
| **Data Processing** | Pandas ≥ 2.0, NumPy ≥ 1.24 |
| **Visualization** | Plotly ≥ 5.18 |
| **Primary Database** | SQLite (`junctions.db`) |
| **Cloud Database** | Supabase (PostgreSQL, real-time CRUD) |
| **Geocoding** | OpenStreetMap Nominatim API, IP-based geolocation |
| **Stream Ingestion** | yt-dlp ≥ 2024.1 |
| **Data Validation** | Pydantic ≥ 2.0 |
| **Deployment** | Render (cloud), `render.yaml` |

### Database Schema (6 Tables)

| Table | Purpose |
|---|---|
| `junctions` | Junction metadata, GPS coords, risk score |
| `detection_indicators` | YOLO frame outputs per junction |
| `risk_scores` | Full 5-factor breakdown history |
| `citizen_reports` | Crowdsourced hazard submissions + media |
| `accident_history` | Year/month severity, fatalities, injuries |
| `vision_logs` | Vehicle counts, congestion score |

---

## 📦 Setup & Installation

### Prerequisites

- Python 3.10 or higher
- Git
- (Optional) Supabase account for cloud sync

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/JunctionGuard-AI.git
cd JunctionGuard-AI
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # On macOS/Linux
# venv\Scripts\activate         # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Supabase (optional — app runs on SQLite without these)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

> ℹ️ If Supabase credentials are not provided, the app automatically falls back to the local SQLite database.

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open at **`http://localhost:8501`**

### 6. (Optional) Process a Video File

```python
from src.vision.video_processor import VideoTrafficDetector

detector = VideoTrafficDetector()
result = detector.process_video("data/sample_videos/junction.mp4", output_dir="data/output")
print(result)
```

---

## 📁 Project Structure

```
JunctionGuard-AI/
├── app.py                          # Main Streamlit dashboard (1,408 lines)
├── app/
│   ├── components.py               # Reusable UI components & custom styles
│   ├── pages/
│   │   └── 1_Citizen_Report.py     # Citizen hazard reporting portal
│   └── data_loader.py              # App-level data utilities
├── src/
│   ├── analytics/
│   │   ├── risk_engine.py          # Explainable 5-factor risk scoring
│   │   ├── data_loader.py          # Kaggle accident dataset pipeline
│   │   └── indicator_engine.py     # Traffic indicator computation
│   ├── vision/
│   │   ├── detector.py             # YOLOv8 + OpenCV detection engine
│   │   ├── video_processor.py      # Frame extraction & JSON export
│   │   ├── stream_processor.py     # Live CCTV stream handling
│   │   └── analyzer.py             # Vision analytics aggregator
│   ├── database.py                 # SQLite CRUD + schema + seed data
│   ├── supabase_client.py          # Cloud real-time sync
│   ├── geo_utils.py                # Haversine, geocoding, IP location
│   └── schema.py                   # Pydantic data models
├── data/
│   ├── india_road_accidents_3000.csv   # Kaggle accident dataset
│   ├── citizen_reports/                # Crowdsourced report storage
│   ├── sample_videos/                  # Sample CCTV footage
│   └── output/                         # Detection JSON/CSV exports
├── tests/                          # Unit tests
├── scripts/                        # Utility scripts
├── yolov8n.pt                      # YOLOv8 nano model weights
├── junctions.db                    # SQLite database
├── render.yaml                     # Render deployment config
├── requirements.txt                # Python dependencies
├── .streamlit/                     # Streamlit configuration
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
└── CODE_OF_CONDUCT.md
```

---

## 🗺️ Monitored Junctions

| Junction | City | State | Risk Level |
|---|---|---|---|
| Silk Board Junction | Bengaluru | Karnataka | 🔴 HIGH (88.4) |
| Goraguntepalya Junction | Bengaluru | Karnataka | 🔴 HIGH (82.1) |
| ITO Crossing | New Delhi | Delhi | 🔴 HIGH (76.2) |
| Panjagutta Junction | Hyderabad | Telangana | 🟡 MEDIUM (64.8) |
| Dadar TT Circle | Mumbai | Maharashtra | 🟡 MEDIUM (58.5) |
| Kathipara Junction | Chennai | Tamil Nadu | 🟡 MEDIUM (42.0) |
| Dabholkar Corner | Kolhapur | Maharashtra | 🟡 MEDIUM (40.8) |
| Shivaji Chowk | Kolhapur | Maharashtra | 🟢 LOW (38.0) |
| Rajaram Corner | Kolhapur | Maharashtra | 🟢 LOW (36.0) |
| Cyber Chowk | Kolhapur | Maharashtra | 🟢 LOW (34.0) |
| Chandani Chowk Junction | Pune | Maharashtra | 🟢 LOW (31.5) |
| Kawala Naka | Kolhapur | Maharashtra | 🟢 LOW |

---

## 👥 Team & Contributions

| Name | Role | Contributions |
|---|---|---|
| **Sai Prasad** | Team Lead / Full-Stack Developer | System architecture, main dashboard (`app.py`), database design, deployment on Render |
| **[Team Member 2]** | Computer Vision Engineer | YOLOv8 integration, `src/vision/` pipeline, video processor, stream analytics |
| **[Team Member 3]** | Data & Analytics Engineer | Risk engine (`risk_engine.py`), Kaggle dataset pipeline, indicator computation |
| **[Team Member 4]** | Frontend / UI Developer | Streamlit UI components, Folium map integration, custom CSS/animations |
| **[Team Member 5]** | Backend / DevOps | Supabase integration, geo-utilities, citizen reporting portal, CI/CD |

> 📝 *Please update team member names and specific contribution details as needed.*

---

## 🚀 Deployment

### Render (Cloud)

The project includes a `render.yaml` configuration for one-click Render deployment:

```bash
# Push to your repository — Render auto-deploys on push
git push origin main
```

### Local Docker (Optional)

```bash
docker build -t junctionguard-ai .
docker run -p 8501:8501 junctionguard-ai
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

```bash
# Test Supabase connectivity specifically
python test_supabase_connection.py
```

---

## 📊 Risk Scoring Formula

```
Risk Score (0–100) =
    (Historical Accident Score × 0.30)
  + (Traffic Density Score    × 0.20)
  + (Near-Miss Conflict Score × 0.20)
  + (Pedestrian Activity Score× 0.15)
  + (Citizen Reports Score    × 0.15)
```

All component scores are normalized to a 0–100 scale before weighting.

---

## 🔮 Future Roadmap

- [ ] Real CCTV RTSP/HLS stream integration with municipal feeds
- [ ] WebSocket live dashboard push updates
- [ ] Mobile PWA for citizen reporting
- [ ] SMS/WhatsApp alert system for traffic police
- [ ] Custom YOLOv8 fine-tuning on Indian traffic scenes (auto-rickshaws, cycle-rickshaws)
- [ ] LSTM/Prophet predictive risk forecasting
- [ ] Government PDF/Excel reporting portal
- [ ] Pan-India expansion (500+ junctions, 50 cities)
- [ ] NHAI & MoRTH integration

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

## 🔒 Security

See [SECURITY.md](./SECURITY.md) for information on how data is handled, stored, and protected.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on how to get started.

---

## 📬 Contact

For queries related to this project, please open an issue on GitHub or reach out via the hackathon submission portal.

---

<div align="center">

**Built with ❤️ for OMNIKON Hackathon**

*JunctionGuard AI — Roads Safer, Cities Smarter.*

</div>
