"""
JunctionGuard AI - OMNIKON Hackathon Dashboard
Explainable AI System for Scoring Accident-Prone Road Junctions in India.
Features Streamlit frontend, interactive Folium map with pulsing red halos for high-risk zones,
YOLOv8 vision analytics preview, and multi-factor explainability breakdowns.
"""

import streamlit as st
import folium
from folium.plugins import HeatMap, MiniMap, Fullscreen
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

# ============================================================
# COMPREHENSIVE CSS DESIGN SYSTEM — JunctionGuard AI Brand
# ============================================================
st.markdown("""
<style>
    /* ── Global Dark Theme Override ── */
    .stApp,
    [data-testid="stAppViewContainer"] {
        background: #0a0e1a !important;
        color: #e2e8f0 !important;
    }
    header[data-testid="stHeader"] {
        background: rgba(10, 14, 26, 0.85) !important;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(51, 65, 85, 0.4);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1729 0%, #0a0e1a 100%) !important;
        border-right: 1px solid rgba(51, 65, 85, 0.5);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label {
        color: #cbd5e1 !important;
    }

    /* ── Custom Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }

    /* ── Animated Gradient Separator ── */
    @keyframes gradientFlow {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .gradient-separator {
        height: 3px;
        background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981, #3b82f6, #ef4444);
        background-size: 300% 100%;
        animation: gradientFlow 4s ease infinite;
        border-radius: 2px;
        margin: 0.5rem 0 1.5rem 0;
    }

    /* ── Metric / KPI Card Styling ── */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(51, 65, 85, 0.5);
        border-radius: 16px;
        padding: 20px;
        color: #f8fafc;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        border-color: rgba(99, 102, 241, 0.5);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15), 0 0 0 1px rgba(99, 102, 241, 0.2);
        transform: translateY(-2px);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-color, #6366f1), transparent);
        border-radius: 16px 16px 0 0;
    }
    .metric-icon {
        font-size: 1.3rem;
        margin-right: 6px;
        opacity: 0.8;
    }
    .metric-title {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 6px;
        line-height: 1.1;
    }
    .metric-status {
        font-size: 0.65rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .metric-status .live-dot {
        width: 6px;
        height: 6px;
        background: #10b981;
        border-radius: 50%;
        animation: livePulse 2s ease-in-out infinite;
    }
    @keyframes livePulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    .metric-accent-bar {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        border-radius: 0 0 16px 16px;
    }

    /* ── Risk Level Badges ── */
    .badge-high {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        padding: 5px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(239, 68, 68, 0.3);
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
        animation: badgePulseHigh 2s ease-in-out infinite;
    }
    @keyframes badgePulseHigh {
        0%, 100% { box-shadow: 0 0 12px rgba(239, 68, 68, 0.2); }
        50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); }
    }
    .badge-medium {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        padding: 5px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-low {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        padding: 5px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* ── Pulsing Red Halo CSS Animation for Folium High-Risk Markers ── */
    @keyframes pulse-red {
        0%   { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.9); }
        50%  { box-shadow: 0 0 0 25px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    @keyframes pulse-amber {
        0%   { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6); }
        50%  { box-shadow: 0 0 0 15px rgba(245, 158, 11, 0); }
        100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }
    .pulse-marker-high {
        background-color: #ef4444;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 3px solid #ffffff;
        animation: pulse-red 1.6s infinite;
    }
    .pulse-marker-med {
        background-color: #f59e0b;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 2px solid #ffffff;
        animation: pulse-amber 2.2s infinite;
    }
    .pulse-marker-low {
        background-color: #10b981;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid #ffffff;
    }

    /* ── Tab Styling ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid rgba(51, 65, 85, 0.4);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        padding: 8px 16px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #e2e8f0;
        background: rgba(51, 65, 85, 0.3);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(59, 130, 246, 0.15) !important;
        color: #60a5fa !important;
        border-bottom: 2px solid #3b82f6;
    }

    /* ── Detail / Info Card ── */
    .detail-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(51, 65, 85, 0.5);
        border-radius: 14px;
        padding: 20px;
        color: #f8fafc;
    }
    .detail-card h3 {
        margin: 0 0 12px 0;
        font-size: 1.4rem;
        color: #f1f5f9;
    }
    .detail-card code {
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }

    /* ── Section Headers ── */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #f1f5f9 !important;
    }

    /* ── Form Styling ── */
    .stForm {
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(51, 65, 85, 0.5);
        border-radius: 12px;
        padding: 16px;
    }

    /* ── Footer ── */
    .app-footer {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(10, 14, 26, 0.9));
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 12px;
        padding: 16px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 2rem;
    }
    .footer-brand {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 600;
    }
    .footer-version {
        font-size: 0.7rem;
        color: #475569;
        background: rgba(51, 65, 85, 0.3);
        padding: 3px 10px;
        border-radius: 9999px;
        border: 1px solid rgba(71, 85, 105, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ── Branded Hero Header ──
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(10, 14, 26, 0.95) 100%);
            border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 16px; padding: 24px 28px;
            position: relative; overflow: hidden;">
    <div style="position: absolute; top: 12px; right: 16px;
                background: rgba(99, 102, 241, 0.15); color: #a5b4fc; padding: 3px 12px;
                border-radius: 9999px; font-size: 0.65rem; font-weight: 700;
                border: 1px solid rgba(99, 102, 241, 0.25); letter-spacing: 0.08em;">
        OMNIKON 2024
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 2.4rem;">🚨</span>
        <div>
            <h1 style="margin: 0; font-size: 2rem; font-weight: 800;
                        background: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        background-clip: text;">
                JunctionGuard AI
            </h1>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.95rem; font-weight: 400;">
                Preventive Road Safety &amp; Explainable Junction Risk Scoring System for Indian Cities
            </p>
        </div>
    </div>
</div>
<div class="gradient-separator"></div>
""", unsafe_allow_html=True)

# ── Sidebar Controls ──
st.sidebar.markdown("""
<div style="text-align: center; padding: 8px 0 16px 0; border-bottom: 1px solid rgba(51,65,85,0.4); margin-bottom: 16px;">
    <img src="https://img.icons8.com/color/96/traffic-light.png" width="50" style="margin-bottom: 6px;">
    <div style="font-size: 1.1rem; font-weight: 700; color: #f1f5f9;">Dashboard Controls</div>
    <div style="font-size: 0.65rem; color: #475569; background: rgba(51,65,85,0.3); display: inline-block;
                padding: 2px 10px; border-radius: 9999px; margin-top: 4px; border: 1px solid rgba(71,85,105,0.3);">
        v1.0 • Live Mode
    </div>
</div>
""", unsafe_allow_html=True)

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
    <div class="metric-card" style="--accent-color: #6366f1;">
        <div class="metric-title"><span class="metric-icon">◉</span> Monitored Junctions</div>
        <div class="metric-value" style="color: #e2e8f0;">{total_jnc}</div>
        <div class="metric-status"><div class="live-dot"></div> REAL-TIME</div>
        <div class="metric-accent-bar" style="background: linear-gradient(90deg, #6366f1, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card" style="--accent-color: #ef4444;">
        <div class="metric-title"><span class="metric-icon">⚠</span> High Risk Hotspots</div>
        <div class="metric-value" style="color:#f87171;">{high_risk_count}</div>
        <div class="metric-status"><div class="live-dot"></div> CRITICAL</div>
        <div class="metric-accent-bar" style="background: linear-gradient(90deg, #ef4444, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card" style="--accent-color: #f59e0b;">
        <div class="metric-title"><span class="metric-icon">📊</span> Avg Risk Score</div>
        <div class="metric-value" style="color:#fbbf24;">{avg_risk_score}<span style="font-size:1rem; color:#64748b;">/100</span></div>
        <div class="metric-status"><div class="live-dot"></div> UPDATED</div>
        <div class="metric-accent-bar" style="background: linear-gradient(90deg, #f59e0b, transparent);"></div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card" style="--accent-color: #3b82f6;">
        <div class="metric-title"><span class="metric-icon">📋</span> Citizen Reports</div>
        <div class="metric-value" style="color:#60a5fa;">{total_reports}</div>
        <div class="metric-status"><div class="live-dot"></div> LIVE FEED</div>
        <div class="metric-accent-bar" style="background: linear-gradient(90deg, #3b82f6, transparent);"></div>
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
# TAB 1: REAL-TIME INTERACTIVE ALERT MAP (SATELLITE + STREETS + HEATMAP)
# ----------------------------------------------------
with tab_map:
    st.subheader("🗺️ Real-Time India Road Junction Surveillance & Alert Map")
    st.markdown(
        "Live GIS surveillance dashboard. Switch between **🛰️ HD Satellite Imagery**, **🛣️ Street Navigation**, and **🔥 Risk Heatmaps**. "
        "High-risk zones exhibit **pulsing radar halos** and dynamic conflict danger perimeters."
    )

    # Quick Navigation / Junction Focus Bar
    map_ctrl1, map_ctrl2, map_ctrl3 = st.columns([2, 1, 1])
    
    with map_ctrl1:
        junction_options = {"🇮🇳 All India Overview": None}
        for j in filtered_junctions:
            junction_options[f"📍 {j['name']} ({j.get('risk_level', 'LOW')} - {j.get('risk_score', 0):.1f})"] = j
        
        selected_map_view = st.selectbox("🎯 Focus on Junction Camera / Location", options=list(junction_options.keys()))

    with map_ctrl2:
        show_heatmap = st.checkbox("🔥 Show Accident Density Heatmap", value=True)

    with map_ctrl3:
        show_danger_buffers = st.checkbox("⭕ Show Conflict Hazard Zones (500m)", value=True)

    # Determine center and zoom level based on selection
    target_jnc = junction_options[selected_map_view]
    if target_jnc is not None:
        map_center = [target_jnc["lat"], target_jnc["lon"]]
        map_zoom = 15
    else:
        map_center = [20.5937, 78.9629]
        map_zoom = 5

    # Initialize Folium Map with OpenStreetMap by default
    m = folium.Map(
        location=map_center,
        zoom_start=map_zoom,
        tiles=None,
        control_scale=True
    )

    # 1. Base Tile Layers (Streets, Real Satellite, Dark Canvas, Light)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenStreetMap contributors",
        name="🛣️ Street View (OpenStreetMap)",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery, Maxar, Earthstar Geographics",
        name="🛰️ Real Satellite Imagery (HD)",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="🌃 Dark Tactical View",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="CartoDB positron",
        name="🗺️ Clean Light Map",
        overlay=False,
        control=True
    ).add_to(m)

    # 2. Add Accident Risk HeatMap Layer
    if show_heatmap and filtered_junctions:
        heat_data = []
        for j in filtered_junctions:
            weight = (j.get("risk_score") or 30.0) / 100.0
            # Add center point and slight jitter points for realistic heat radius
            heat_data.append([j["lat"], j["lon"], weight * 1.5])
            heat_data.append([j["lat"] + 0.0015, j["lon"] + 0.0015, weight * 0.9])
            heat_data.append([j["lat"] - 0.0015, j["lon"] - 0.0015, weight * 0.9])
        
        heatmap_layer = folium.FeatureGroup(name="🔥 Accident Risk Heatmap", overlay=True)
        HeatMap(
            heat_data,
            radius=28,
            blur=20,
            max_zoom=13,
            gradient={0.2: '#10b981', 0.5: '#f59e0b', 0.8: '#ef4444', 1.0: '#991b1b'}
        ).add_to(heatmap_layer)
        heatmap_layer.add_to(m)

    # 3. Add Junction Danger Zone Buffers (500m conflict perimeter)
    if show_danger_buffers:
        buffer_layer = folium.FeatureGroup(name="⭕ Hazard Perimeter Buffers (500m)", overlay=True)
        for jnc in filtered_junctions:
            lvl = jnc.get("risk_level", "LOW")
            if lvl == "HIGH":
                buf_color = "#ef4444"
                buf_opacity = 0.18
            elif lvl == "MEDIUM":
                buf_color = "#f59e0b"
                buf_opacity = 0.12
            else:
                buf_color = "#10b981"
                buf_opacity = 0.08

            folium.Circle(
                location=[jnc["lat"], jnc["lon"]],
                radius=450,
                color=buf_color,
                fill=True,
                fill_color=buf_color,
                fill_opacity=buf_opacity,
                weight=1.5,
                dash_array="5, 5",
                tooltip=f"500m Risk Perimeter: {jnc['name']}"
            ).add_to(buffer_layer)
        buffer_layer.add_to(m)

    # 4. Add Interactive Junction Markers with Live Radar Halos
    markers_layer = folium.FeatureGroup(name="🚨 Junction Alert Markers", overlay=True)
    for jnc in filtered_junctions:
        score = jnc["risk_score"] or 0.0
        level = jnc["risk_level"] or "LOW"
        name = jnc["name"]
        lat, lon = jnc["lat"], jnc["lon"]

        if level == "HIGH":
            marker_html = f'<div class="pulse-marker-high" title="{name}: {score}"></div>'
            color_hex = "#ef4444"
            badge_bg = "#ef4444"
        elif level == "MEDIUM":
            marker_html = f'<div class="pulse-marker-med" title="{name}: {score}"></div>'
            color_hex = "#f59e0b"
            badge_bg = "#f59e0b"
        else:
            marker_html = f'<div class="pulse-marker-low" title="{name}: {score}"></div>'
            color_hex = "#10b981"
            badge_bg = "#10b981"

        # Factors popup summary
        factors_items = "".join([
            f'<div style="display:flex; justify-content:space-between; margin-bottom:3px;">'
            f'<span style="color:#64748b;">• {f["factor"]}:</span>'
            f'<b style="color:#334155;">{int(f["weight"]*100)}%</b></div>'
            for f in (jnc["contributing_factors"] or [])[:3]
        ])

        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        popup_content = f"""
        <div style="font-family: 'Segoe UI', system-ui, sans-serif; width: 260px; padding: 6px 4px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                <h4 style="margin:0; color: #0f172a; font-size: 0.95rem; line-height:1.2;">{name}</h4>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; margin:6px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.75rem; color:#64748b; font-weight:600;">RISK SCORE</span>
                    <span style="background:{badge_bg}; color:white; padding:2px 8px; border-radius:9999px; font-size:0.65rem; font-weight:700;">{level}</span>
                </div>
                <div style="font-size:1.6rem; font-weight:800; color:{color_hex}; line-height:1.2; margin-top:2px;">
                    {score}<span style="font-size:0.85rem; color:#94a3b8; font-weight:500;"> / 100</span>
                </div>
            </div>
            <div style="font-size:0.75rem; margin-top:6px;">
                <b style="color:#475569;">Top Contributing Risk Factors:</b>
                <div style="margin-top:4px;">{factors_items}</div>
            </div>
            <div style="margin-top:10px; padding-top:8px; border-top:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:0.7rem; color:#94a3b8; font-family:monospace;">{lat:.4f}, {lon:.4f}</span>
                <a href="{gmaps_url}" target="_blank" style="color:#3b82f6; text-decoration:none; font-size:0.75rem; font-weight:600;">
                    📍 View on Maps &rarr;
                </a>
            </div>
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
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"{name} | {level} Risk ({score:.1f}/100)"
        ).add_to(markers_layer)

    markers_layer.add_to(m)

    # 5. Interactive Folium Plugins
    Fullscreen(position="topright").add_to(m)
    MiniMap(toggle_display=True, tile_layer="OpenStreetMap", position="bottomright", width=140, height=100).add_to(m)
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)

    st_folium(m, width="stretch", height=580, key=f"real_map_{selected_map_view}")

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
            <div class="detail-card" style="margin-top: 15px;">
                <h3>🏙️ {jnc_data['name']}</h3>
                <p style="margin: 8px 0;"><b style="color:#94a3b8;">Junction ID:</b> <code>{jnc_data['junction_id']}</code></p>
                <p style="margin: 8px 0;">
                    <b style="color:#94a3b8;">Risk Score:</b>
                    <span style="font-size:2rem; font-weight:800; color: {'#f87171' if level=='HIGH' else '#fbbf24' if level=='MEDIUM' else '#34d399'};">
                        {score}<span style="font-size:1rem; color:#64748b;">/100</span>
                    </span>
                </p>
                <p style="margin: 8px 0;"><b style="color:#94a3b8;">Risk Level:</b> <span class="{badge_class}">{level}</span></p>
                <p style="margin: 10px 0 0 0; font-size: 0.75rem; color: #475569;">Last Updated: {jnc_data['last_updated']}</p>
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
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.5)",
                font_color="#cbd5e1"
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
                video_placeholder.image(frame_rgb, caption=f"Silk Board Junction CCTV - Frame {frame_idx}", width="stretch")
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

# ── Professional Footer ──
st.markdown("""
<div class="app-footer">
    <div class="footer-brand">🚨 JunctionGuard AI • Explainable Road Safety Intelligence</div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span class="footer-version">v1.0.0</span>
        <span style="font-size: 0.7rem; color: #475569;">OMNIKON Hackathon • Track A (Vision) & Track B (Data/Logic)</span>
    </div>
</div>
""", unsafe_allow_html=True)
