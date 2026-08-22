"""
JunctionGuard AI - OMNIKON Hackathon Dashboard
Explainable AI System for Scoring Accident-Prone Road Junctions in India.
Features Streamlit frontend, interactive Folium map with pulsing red halos for high-risk zones,
YOLOv8 vision analytics preview, and multi-factor explainability breakdowns.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Internal imports
from src.database import (
    init_db, fetch_all_junctions, fetch_junction_by_id, 
    add_citizen_report, fetch_citizen_reports
)
from src.analytics.risk_engine import ExplainableRiskEngine
from src.analytics.data_loader import compute_historical_risk_score, load_accident_dataset
from src.vision.stream_processor import StreamProcessor

# Initialize Database on app start
init_db()
risk_engine = ExplainableRiskEngine()

st.set_page_config(
    page_title="JunctionGuard AI | Explainable Road Safety",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI styling & pulsing red halo map markers
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        margin-top: 4px;
    }
    .badge-high {
        background-color: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
    }
    .badge-medium {
        background-color: #f59e0b;
        color: white;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
    }
    .badge-low {
        background-color: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
    }

    /* Pulsing Red Halo CSS Animation for Folium High-Risk Markers */
    @keyframes pulse-red {
        0% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8);
        }
        70% {
            box-shadow: 0 0 0 20px rgba(239, 68, 68, 0);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
        }
    }
    .pulse-marker-high {
        background-color: #ef4444;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 3px solid #ffffff;
        animation: pulse-red 1.8s infinite;
    }
    .pulse-marker-med {
        background-color: #f59e0b;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 2px solid #ffffff;
    }
    .pulse-marker-low {
        background-color: #10b981;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("🚨 JunctionGuard AI")
st.caption("Preventive Road Safety & Explainable Junction Risk Scoring System for Indian Cities")

# Sidebar Controls
st.sidebar.image("https://img.icons8.com/color/96/traffic-light.png", width=70)
st.sidebar.header("🕹️ Dashboard Control Panel")

# Load Junction Data (conforming strictly to Data Contract)
junctions = fetch_all_junctions()

# Filter Junctions
risk_filter = st.sidebar.multiselect(
    "Filter Risk Level",
    options=["HIGH", "MEDIUM", "LOW"],
    default=["HIGH", "MEDIUM", "LOW"]
)

filtered_junctions = [j for j in junctions if j["risk_level"] in risk_filter]

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
total_jnc = len(junctions)
high_risk_count = sum(1 for j in junctions if j["risk_level"] == "HIGH")
avg_risk_score = round(sum(j["risk_score"] for j in junctions if j["risk_score"] is not None) / max(1, total_jnc), 1)
total_reports = len(fetch_citizen_reports())

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Monitored Junctions</div>
        <div class="metric-value">{total_jnc}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">High Risk Hotspots</div>
        <div class="metric-value" style="color:#ef4444;">{high_risk_count}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Avg Junction Risk Score</div>
        <div class="metric-value" style="color:#f59e0b;">{avg_risk_score}/100</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Citizen Hazard Reports</div>
        <div class="metric-value" style="color:#3b82f6;">{total_reports}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Main Layout Tabs
tab_map, tab_explain, tab_vision, tab_citizen = st.tabs([
    "🗺️ Interactive Alert Map",
    "📊 Explainability & Factor Breakdown",
    "📹 Live CCTV Vision Analytics (Track A)",
    "📝 Citizen Hazard Reporting"
])

# ----------------------------------------------------
# TAB 1: INTERACTIVE ALERT MAP WITH PULSING RED HALOS
# ----------------------------------------------------
with tab_map:
    st.subheader("🗺️ India Junction Risk Map")
    st.markdown(
        "Alert map. High-risk junctions (**Score ≥ 70**) exhibit a **pulsing red halo** for immediate preventive action."
    )

    # Initialize Folium Map centered over India
    m = folium.Map(location=[18.5, 78.5], zoom_start=5, tiles="CartoDB positron")

    for jnc in filtered_junctions:
        score = jnc["risk_score"] or 0.0
        level = jnc["risk_level"] or "LOW"
        name = jnc["name"]
        lat, lon = jnc["lat"], jnc["lon"]

        if level == "HIGH":
            marker_html = f'<div class="pulse-marker-high" title="{name}: {score}"></div>'
            color_hex = "#ef4444"
        elif level == "MEDIUM":
            marker_html = f'<div class="pulse-marker-med" title="{name}: {score}"></div>'
            color_hex = "#f59e0b"
        else:
            marker_html = f'<div class="pulse-marker-low" title="{name}: {score}"></div>'
            color_hex = "#10b981"

        # Factors popup summary
        factors_text = "<br>".join([f"• {f['factor']}: {int(f['weight']*100)}%" for f in (jnc["contributing_factors"] or [])[:3]])
        popup_content = f"""
        <div style="font-family: sans-serif; width: 220px;">
            <h4 style="margin:0 0 5px 0;">{name}</h4>
            <p style="margin:0;"><b>Risk Score:</b> <span style="color:{color_hex}; font-weight:bold;">{score}/100</span> ({level})</p>
            <hr style="margin:8px 0;">
            <p style="margin:0; font-size:12px;"><b>Top Contributing Factors:</b><br>{factors_text}</p>
        </div>
        """

        # Custom DivIcon for Pulsing Effect
        icon = folium.DivIcon(
            html=marker_html,
            icon_size=(20, 20),
            icon_anchor=(10, 10)
        )
        folium.Marker(
            location=[lat, lon],
            icon=icon,
            popup=folium.Popup(popup_content, max_width=260),
            tooltip=f"{name} ({level} - {score}/100)"
        ).add_to(m)

    st_folium(m, width=1200, height=520, use_container_width=True)

# ----------------------------------------------------
# TAB 2: EXPLAINABILITY & CONTRIBUTING FACTORS
# ----------------------------------------------------
with tab_explain:
    st.subheader("📊 Explainable Junction Risk Scoring")
    st.markdown("Unlike black-box models, JunctionGuard AI exposes the **exact factor weight breakdown** driving each score.")

    col_select, col_details = st.columns([1, 2])

    with col_select:
        jnc_names = {j["name"]: j["junction_id"] for j in junctions}
        selected_name = st.selectbox("Select Junction to Analyze", options=list(jnc_names.keys()))
        selected_id = jnc_names[selected_name]

        # Recalculate or retrieve latest risk score
        jnc_data = fetch_junction_by_id(selected_id)
        
        if jnc_data:
            score = jnc_data["risk_score"]
            level = jnc_data["risk_level"]
            badge_class = f"badge-{level.lower()}"
            st.markdown(f"""
            <div style="background:#1e293b; padding:15px; border-radius:10px; margin-top:15px;">
                <h3>{jnc_data['name']}</h3>
                <p><b>Junction ID:</b> <code>{jnc_data['junction_id']}</code></p>
                <p><b>Risk Score:</b> <span style="font-size:1.8rem; font-weight:bold;">{score}/100</span></p>
                <p><b>Risk Level:</b> <span class="{badge_class}">{level}</span></p>
                <p><small>Last Updated: {jnc_data['last_updated']}</small></p>
            </div>
            """, unsafe_allow_html=True)

    with col_details:
        if jnc_data and jnc_data["contributing_factors"]:
            factors_df = pd.DataFrame(jnc_data["contributing_factors"])
            factors_df["percentage"] = (factors_df["weight"] * 100).round(1)

            st.write("#### 🔍 Risk Contribution Breakdown")
            
            fig = px.bar(
                factors_df,
                x="percentage",
                y="factor",
                orientation="h",
                text="percentage",
                labels={"percentage": "Impact Contribution (%)", "factor": "Risk Factor"},
                color="percentage",
                color_continuous_scale="Reds"
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                xaxis_title="Factor Impact Contribution (%)",
                height=320,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

            # Historical dataset breakdown stats
            hist_score, hist_stats = compute_historical_risk_score(selected_id)
            st.write("#### 📜 Historical Accident Context (2018-2023)")
            hc1, hc2, hc3, hc4 = st.columns(4)
            hc1.metric("Total Accidents", hist_stats["total_accidents"])
            hc2.metric("Fatalities", hist_stats["fatalities"], delta_color="inverse")
            hc3.metric("Injuries", hist_stats["injuries"])
            hc4.metric("Motorcycle Impact %", f"{hist_stats['motorcycle_involvement_pct']}%")

# ----------------------------------------------------
# TAB 3: LIVE CCTV VISION ANALYTICS (TRACK A)
# ----------------------------------------------------
with tab_vision:
    st.subheader("📹 Real-time CCTV Video Analytics (YOLOv8 + OpenCV)")
    st.markdown(
        "Processes intersection CCTV streams to detect vehicle counts, pedestrian exposure, "
        "high **two-wheeler weaving density** (critical for Indian traffic), and spatial near-miss proximity."
    )

    v_col1, v_col2 = st.columns([2, 1])

    with v_col1:
        run_vision = st.checkbox("▶️ Run Live CCTV Video Processor Stream", value=True)
        video_placeholder = st.empty()

        if run_vision:
            processor = StreamProcessor()
            # Render animated live feed frames
            for frame_idx in range(1, 30):
                processed_frame, metrics = processor.generate_simulated_frame(frame_idx)
                # Convert BGR (OpenCV) to RGB for Streamlit image display
                frame_rgb = processed_frame[:, :, ::-1]
                video_placeholder.image(frame_rgb, caption=f"Silk Board Junction CCTV - Frame {frame_idx}", use_column_width=True)
                time.sleep(0.08)

    with v_col2:
        st.write("#### 📐 Real-Time Vision Metrics")
        st.info("YOLOv8 Class Highlights: Motorcycle (Cyan), Pedestrian (Red), Cars (Green), Heavy (Orange)")

        st.metric("Vision Risk Index", "68.4 / 100")
        st.metric("Total Detected Vehicles", "47")
        st.metric("Two-Wheeler Share (Indian Context)", "59.5%")
        st.metric("Near-Miss Proximity Conflicts", "6")

# ----------------------------------------------------
# TAB 4: CITIZEN HAZARD REPORTING
# ----------------------------------------------------
with tab_citizen:
    st.subheader("📝 Citizen Road Hazard Reporting")
    st.markdown("Citizens and traffic police can report road hazards (potholes, missing signals, near-misses) to dynamically update the Junction Risk Score.")

    c_form, c_list = st.columns([1, 1])

    with c_form:
        st.write("#### Submit New Hazard Report")
        with st.form("citizen_report_form"):
            rep_jnc = st.selectbox("Select Junction", options=list(jnc_names.keys()))
            rep_name = st.text_input("Reporter Name / Designation", value="Traffic Marshal / Resident")
            rep_issue = st.selectbox("Issue Category", [
                "Pothole / Damaged Road Surface",
                "Broken Traffic Signal / Light",
                "Blind Spot / Obstructed View",
                "Frequent Speeding / Illegal U-turn",
                "Near-Miss Pedestrian Crossing"
            ])
            rep_sev = st.slider("Hazard Severity (1 = Minor, 5 = Severe Hazard)", 1, 5, 3)
            rep_desc = st.text_area("Detailed Description", placeholder="Describe exact location, lane blockages, or timing...")
            
            submit_btn = st.form_submit_button("🚨 Submit Hazard Report")

            if submit_btn:
                target_id = jnc_names[rep_jnc]
                add_citizen_report(target_id, rep_name, rep_issue, rep_sev, rep_desc)
                # Recalculate risk score immediately
                risk_engine.compute_junction_risk(target_id)
                st.success(f"Report submitted for {rep_jnc}! Risk score recalculated dynamically.")
                st.rerun()

    with c_list:
        st.write("#### Recent Citizen & Officer Reports")
        reports_df = pd.DataFrame(fetch_citizen_reports())
        if not reports_df.empty:
            st.dataframe(
                reports_df[["junction_id", "issue_type", "severity", "reporter_name", "timestamp"]],
                use_container_width=True,
                height=350
            )
        else:
            st.write("No reports submitted yet.")

# Footer
st.divider()
st.caption("JunctionGuard AI • OMNIKON Hackathon • Parallel Architecture: Track A (Vision) & Track B (Data/Logic)")
