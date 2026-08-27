"""
JunctionGuard AI - OMNIKON Hackathon Dashboard
Explainable AI System for Scoring Accident-Prone Road Junctions in India.
Features Streamlit frontend, interactive Folium map with pulsing red halos for high-risk zones,
YOLOv8 vision analytics preview, and multi-factor explainability breakdowns.
"""

import os
import json
import uuid
import mimetypes
import cv2
import streamlit as st
import folium
from folium.plugins import HeatMap, MiniMap, Fullscreen, MarkerCluster, LocateControl
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
import importlib
import src.geo_utils
importlib.reload(src.geo_utils)
from src.geo_utils import find_nearest_junction, reverse_geocode_location, get_ip_location, forward_geocode_location
import streamlit.components.v1 as st_components
from src.analytics.data_loader import compute_historical_risk_score, load_accident_dataset
from src.vision.stream_processor import StreamProcessor

import importlib
import app.components as app_comp
importlib.reload(app_comp)
from app.components import (
    render_risk_badge,
    render_contributing_factors,
    render_awaiting_data_banner,
    inject_custom_styles,
    get_risk_badge_html,
    render_navbar,
    render_dashboard_overview_header,
    render_footer
)

# ── Handle Browser GPS Callback (from HTML5 Geolocation Button) ──
if "geo_lat" in st.query_params and "geo_lng" in st.query_params:
    try:
        g_lat = float(st.query_params["geo_lat"])
        g_lng = float(st.query_params["geo_lng"])
        nav_target = st.query_params.get("nav", "Citizen Hazard Reporting")
        st.session_state["tab_picked_lat"] = g_lat
        st.session_state["tab_picked_lng"] = g_lng
        st.session_state["sentinel_picked_lat"] = g_lat
        st.session_state["sentinel_picked_lng"] = g_lng
        st.session_state["_pending_nav"] = nav_target  # applied before widget renders
        _all_j = fetch_all_junctions()
        near_j, _ = find_nearest_junction(g_lat, g_lng, _all_j)
        addr = near_j['name'] if near_j else reverse_geocode_location(g_lat, g_lng)
        st.session_state["selected_junction_name_val"] = addr
        st.session_state["tab_select_junction_dropdown"] = addr
        st.session_state["sync_dropdown_from_map"] = addr
        st.session_state["sentinel_jnc_input"] = addr
        st.session_state["sentinel_select_junction_dropdown"] = addr
        st.query_params.clear()
        st.rerun()
    except Exception as ex:
        print(f"[Query Geolocation Handle Note] {ex}")

# Initialize Database on app start
init_db()
risk_engine = ExplainableRiskEngine()

st.set_page_config(
    page_title="JunctionGuard AI | Command Center",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Stitch Tactical Vision Interface Design System
inject_custom_styles()

# ── Sidebar Navigation & Controls ──
with st.sidebar:
    st.markdown("""
    <div style="padding: 6px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 16px;">
        <div style="display:flex; align-items:center; gap:10px;">
            <div class="brand-shield-logo" style="width:34px; height:34px;"></div>
            <div>
                <div style="font-family:'Space Grotesk', sans-serif; font-size:1.05rem; font-weight:800; color:#ffffff;">JunctionGuard</div>
                <div style="font-size:0.65rem; color:#9ca3af; font-family:'JetBrains Mono', monospace;">AI SURVEILLANCE SYSTEM</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    nav_options = [
        "Dashboard",
        "Interactive Alert Map",
        "Explainability & Factor Breakdown",
        "Live CCTV Vision Analytics",
        "Citizen Hazard Reporting"
    ]

    # Apply any pending programmatic navigation BEFORE the widget is instantiated
    _pending_nav = st.session_state.pop("_pending_nav", None)
    _nav_index = nav_options.index(_pending_nav) if _pending_nav in nav_options else 0
    # Preserve current selection if no pending nav requested
    if _pending_nav is None and "app_sidebar_navigation" in st.session_state:
        _current = st.session_state["app_sidebar_navigation"]
        if _current in nav_options:
            _nav_index = nav_options.index(_current)

    sidebar_nav = st.radio(
        "NAVIGATION",
        options=nav_options,
        index=_nav_index,
        format_func=lambda x: {
            "Dashboard": "📊  Dashboard",
            "Interactive Alert Map": "🗺️  Interactive Alert Map",
            "Explainability & Factor Breakdown": "⚖️  Explainability & Factor Breakdown",
            "Live CCTV Vision Analytics": "📹  Live CCTV Vision Analytics",
            "Citizen Hazard Reporting": "🚨  Citizen Hazard Reporting"
        }.get(x, x),
        key="app_sidebar_navigation",
        label_visibility="collapsed"
    )

    st.markdown("<div style='margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 14px;'></div>", unsafe_allow_html=True)

    # Junction Selector Dropdown
    junctions_raw = fetch_all_junctions()
    jnc_select_options = ["All Junctions"] + [j["name"] for j in junctions_raw]
    sidebar_selected_jnc = st.selectbox("JUNCTION SELECTOR", options=jnc_select_options, index=0)

    # Time Range Dropdown
    sidebar_time_range = st.selectbox("TIME RANGE", options=["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Live Stream"], index=0)

    # Risk Filter Multiselect
    risk_filter = st.multiselect(
        "FILTER RISK LEVEL",
        options=["HIGH", "MEDIUM", "LOW"],
        default=["HIGH", "MEDIUM", "LOW"]
    )

    st.markdown("""
    <div style="margin-top: 30px; padding: 12px; background: #12151a; border: 1px solid rgba(249,115,22,0.3); border-radius: 8px; display: flex; align-items: center; gap: 10px;">
        <div class="brand-shield-logo" style="width:34px; height:34px;"></div>
        <div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #ffffff;">JunctionGuard AI</div>
            <div style="font-size: 0.68rem; color: #9ca3af;">Roads Safer, Cities Smarter.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render Top Tactical Navigation Bar
render_navbar(sidebar_nav)

# Render Subheader Overview Bar
nav_subtitles = {
    "Dashboard": "Real-time Junction Risk Surveillance System",
    "Interactive Alert Map": "Real-time Spatial Hazard & Risk Density Surveillance",
    "Explainability & Factor Breakdown": "Transparent AI Scoring & Contributing Factor Weights",
    "Live CCTV Vision Analytics": "Autonomous Vision Inference & Traffic Anomaly Detection",
    "Citizen Hazard Reporting": "Crowdsourced Hazard Verification & Community Evidence"
}
render_dashboard_overview_header(title=sidebar_nav, subtitle=nav_subtitles.get(sidebar_nav, "Real-time Junction Risk Surveillance System"))

# Load and filter junction records
junctions = fetch_all_junctions()
selected_jnc_record = next((j for j in junctions if j["name"] == sidebar_selected_jnc), None) if sidebar_selected_jnc != "All Junctions" else None

if sidebar_selected_jnc != "All Junctions":
    filtered_junctions = [j for j in junctions if j["name"] == sidebar_selected_jnc]
else:
    filtered_junctions = [j for j in junctions if j["risk_level"] in risk_filter]

def render_surveillance_folium_map(base_view_mode: str, height: int = 380, key_prefix: str = "dash"):
    """Reusable interactive map renderer with Esri dark tiles and pulsing radar halos."""
    enable_heatmap = "Heatmap" in base_view_mode

    # When a specific junction is selected in the sidebar, center directly on it with close zoom!
    if selected_jnc_record:
        map_junctions = [selected_jnc_record]
        map_center = [selected_jnc_record["lat"], selected_jnc_record["lon"]]
        map_zoom = 15
    else:
        map_junctions = [j for j in filtered_junctions if j["risk_level"] in risk_filter]
        pune_jnc = next((j for j in map_junctions if "Pune" in j.get("city", "") or "Shivaji" in j["name"]), None)
        if pune_jnc:
            map_center = [18.5204, 73.8567]
            map_zoom = 11
        elif map_junctions:
            map_center = [map_junctions[0]["lat"], map_junctions[0]["lon"]]
            map_zoom = 11
        else:
            map_center = [18.5204, 73.8567]
            map_zoom = 6

    m = folium.Map(
        location=map_center,
        zoom_start=map_zoom,
        min_zoom=2,
        max_zoom=19,
        tiles=None,
        control_scale=True,
        world_copy_jump=False,
        max_bounds=True,
        min_lat=-85, max_lat=85, min_lon=-180, max_lon=180
    )

    overview_map_css = """
    <style>
    .leaflet-container {
        background-color: #0a0c0e !important;
    }
    .leaflet-tile, .leaflet-pane, .leaflet-tile-pane, .leaflet-tile-container img {
        filter: none !important;
        -webkit-filter: none !important;
        opacity: 1 !important;
        transition: none !important;
    }
    .leaflet-tile:hover {
        filter: none !important;
        -webkit-filter: none !important;
        opacity: 1 !important;
    }
    .leaflet-marker-icon {
        background: transparent !important;
        border: none !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(overview_map_css))

    satellite_tile = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite Imagery",
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    )
    streets_tile = folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street Navigation",
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    )
    dark_tile = folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Dark Gray Canvas",
        name="Dark Tactical",
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    )

    if "Satellite" in base_view_mode:
        satellite_tile.add_to(m)
    elif "Street" in base_view_mode:
        streets_tile.add_to(m)
    else:
        dark_tile.add_to(m)

    if enable_heatmap and map_junctions:
        heat_data = [[j["lat"], j["lon"], float(j["risk_score"] or 50.0) / 100.0] for j in map_junctions]
        HeatMap(
            heat_data,
            radius=32,
            blur=22,
            min_opacity=0.45,
            max_zoom=14,
            gradient={0.2: '#3b82f6', 0.4: '#10b981', 0.6: '#fbbf24', 0.8: '#f97316', 1.0: '#ef4444'}
        ).add_to(m)

    markers_layer = folium.FeatureGroup(name="Junction Markers")
    for j in map_junctions:
        lat = j["lat"]
        lon = j["lon"]
        name = j["name"]
        score = j["risk_score"] or 0.0
        level = (j["risk_level"] or "LOW").upper()

        if level == "HIGH":
            halo_cls = "heat-aura-high"
            circle_color = "#ef4444"
            aura_radius = 450
        elif level == "MEDIUM":
            halo_cls = "heat-aura-med"
            circle_color = "#f59e0b"
            aura_radius = 320
        else:
            halo_cls = "heat-aura-low"
            circle_color = "#10b981"
            aura_radius = 200

        # Thermal heat wave aura circle on the junction
        folium.Circle(
            location=[lat, lon],
            radius=aura_radius,
            color=circle_color,
            weight=1,
            opacity=0.35,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.20
        ).add_to(m)

        marker_html = f'<div class="{halo_cls}"></div>'
        icon = folium.DivIcon(html=marker_html, icon_size=(30, 30), icon_anchor=(15, 15), class_name="junction-heat-icon")
        folium.Marker(
            location=[lat, lon],
            icon=icon,
            tooltip=f"{name} | {level} Risk ({score:.1f}/100)"
        ).add_to(markers_layer)

    markers_layer.add_to(m)

    return st_folium(
        m,
        width="stretch",
        height=height,
        key=f"{key_prefix}_overview_map_{base_view_mode}_{sidebar_selected_jnc.replace(' ', '_')}_{round(map_center[0], 3)}_{round(map_center[1], 3)}_{len(map_junctions)}",
        returned_objects=["last_object_clicked"],
        return_on_hover=False
    )

# ----------------------------------------------------
# 1. DASHBOARD OVERVIEW (HOME)
# ----------------------------------------------------
if sidebar_nav == "Dashboard":
    # Top KPI Summary Cards (Matching Reference Image)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    if selected_jnc_record:
        total_jnc = 1
        high_risk_count = 1 if selected_jnc_record.get("risk_level") == "HIGH" else 0
        avg_risk_score = round(selected_jnc_record.get("risk_score") or 0.0, 1)
        all_reps = fetch_citizen_reports()
        total_reports = sum(1 for r in all_reps if r.get("junction_id") == selected_jnc_record.get("junction_id"))
    else:
        total_jnc = len(junctions)
        high_risk_count = sum(1 for j in junctions if j["risk_level"] == "HIGH")
        avg_risk_score = round(sum(j["risk_score"] for j in junctions if j["risk_score"] is not None) / max(1, total_jnc), 1)
        total_reports = len(fetch_citizen_reports())

    with kpi1:
        st.markdown(f"""
        <div class="kpi-tactical-card">
            <div>
                <div class="kpi-label">MONITORED JUNCTIONS</div>
                <div class="kpi-num">{total_jnc}</div>
                <div class="kpi-sub" style="color: #f97316;"><span class="live-dot-green"></span> REAL-TIME</div>
            </div>
            <div class="kpi-icon-wrap kpi-icon-jnc" style="background: rgba(249, 115, 22, 0.12); border: 1px solid rgba(249, 115, 22, 0.35);"></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="kpi-tactical-card kpi-card-critical">
            <div>
                <div class="kpi-label">HIGH RISK HOTSPOTS</div>
                <div class="kpi-num" style="color: #f87171;">{high_risk_count}</div>
                <div class="kpi-sub" style="color: #ef4444;"><span class="live-dot-red"></span> CRITICAL</div>
            </div>
            <div class="kpi-icon-wrap kpi-icon-alert" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.45);"></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="kpi-tactical-card">
            <div>
                <div class="kpi-label">AVG RISK SCORE</div>
                <div class="kpi-num" style="color: #fbbf24;">{avg_risk_score} <span class="kpi-denom">/100</span></div>
                <div class="kpi-sub" style="color: #f59e0b;"><span class="live-dot-green"></span> UPDATED</div>
            </div>
            <div class="kpi-icon-wrap kpi-icon-score" style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35);"></div>
        </div>
        """, unsafe_allow_html=True)

    with kpi4:
        st.markdown(f"""
        <div class="kpi-tactical-card">
            <div>
                <div class="kpi-label">CITIZEN REPORTS</div>
                <div class="kpi-num" style="color: #34d399;">{total_reports}</div>
                <div class="kpi-sub" style="color: #10b981;"><span class="live-dot-green"></span> LIVE FEED</div>
            </div>
            <div class="kpi-icon-wrap kpi-icon-reports" style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35);"></div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Top Row: Interactive Risk Map (Left) & Live CCTV Feed (Right)
    col_map, col_cctv = st.columns([1, 1])

    with col_map:
        # Header with view mode buttons matching reference image
        map_h_col1, map_h_col2 = st.columns([1, 1])
        with map_h_col1:
            st.markdown('<div class="panel-title" style="font-size:0.95rem; font-weight:700; color:#ffffff; letter-spacing:0.04em; text-transform:uppercase; margin-top:6px;">INTERACTIVE RISK MAP</div>', unsafe_allow_html=True)
        with map_h_col2:
            base_view_mode = st.selectbox(
                "Map Mode",
                options=[
                    "Heatmap Mode",
                    "Dark Tactical",
                    "Satellite Imagery",
                    "Street Navigation"
                ],
                index=0,
                label_visibility="collapsed",
                key="dash_map_mode_select"
            )

        render_surveillance_folium_map(base_view_mode, height=380, key_prefix="dash")

        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#12151a; border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:6px 12px; margin-top:6px; font-size:0.72rem; font-family:'JetBrains Mono', monospace;">
            <span style="color:#9ca3af;">RISK LEVEL:</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#f87171;"><span class="live-dot-red"></span> HIGH</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#fbbf24;"><span style="width:6px; height:6px; border-radius:50%; background:#f59e0b; display:inline-block;"></span> MEDIUM</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#34d399;"><span style="width:6px; height:6px; border-radius:50%; background:#10b981; display:inline-block;"></span> LOW</span>
        </div>
        """, unsafe_allow_html=True)

    with col_cctv:
        # Header for CCTV Feed matching reference image
        cctv_h_col1, cctv_h_col2 = st.columns([1, 1])
        with cctv_h_col1:
            st.markdown('<div class="panel-title" style="font-size:0.95rem; font-weight:700; color:#ffffff; letter-spacing:0.04em; text-transform:uppercase; margin-top:6px;">LIVE CCTV FEED</div>', unsafe_allow_html=True)
        with cctv_h_col2:
            st.markdown('<div style="text-align:right; margin-top:6px;"><span style="display:inline-flex; align-items:center; gap:6px; font-size:0.75rem; font-weight:700; color:#ef4444; font-family:\'JetBrains Mono\', monospace;"><span class="live-dot-red"></span> LIVE</span></div>', unsafe_allow_html=True)

        now_str = datetime.now().strftime("%I:%M:%S %p")
        jnc_label = f"{selected_jnc_record['junction_id']} {selected_jnc_record['name']}" if selected_jnc_record else "J-17 Shivajinagar Junction, Pune"
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#12151a; border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:6px 12px; margin-bottom:8px; font-size:0.74rem; font-family:'JetBrains Mono', monospace;">
            <span style="color:#e2e2e5;">JUNCTION ID: <b style="color:#ffffff;">{jnc_label}</b></span>
            <span style="color:#f97316; font-weight:700;">{now_str}</span>
        </div>
        """, unsafe_allow_html=True)

        # Video stream playback
        sample_video_path = "data/sample_videos/indian_traffic_1.mp4"
        if os.path.exists(sample_video_path):
            st.video(sample_video_path)
        else:
            st.info("CCTV video stream loaded. Connect RTSP stream for live telemetry.")

        # Bottom CCTV controls matching reference image
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1, 3])
        with ctrl_col1:
            st.button("📸", help="Capture Snapshot", key="dash_cctv_snap")
        with ctrl_col2:
            st.button("⏺️", help="Record Incident", key="dash_cctv_rec")
        with ctrl_col3:
            st.button("⛶", help="Fullscreen", key="dash_cctv_full")
        with ctrl_col4:
            st.selectbox("Camera", options=["Camera 01 - Northbound", "Camera 02 - East Crossing", "Camera 03 - Pedestrian Refuge"], index=0, label_visibility="collapsed", key="dash_cctv_cam_sel")

    # Bottom Row: 4 Panels matching reference image
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        with st.container(border=True):
            st.markdown('<div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; font-family:\'Space Grotesk\', sans-serif;">RISK SEVERITY FILTERS</div>', unsafe_allow_html=True)
            st.multiselect(
                "Filter Severity",
                options=["HIGH", "MEDIUM", "LOW"],
                default=["HIGH", "MEDIUM", "LOW"],
                label_visibility="collapsed",
                key="dash_p1_severity_multiselect"
            )
            st.checkbox("🔥 Accident Density Heatmap", value=True, key="dash_p1_heat_chk")
            st.checkbox("🛡️ Hazard Conflict Buffers", value=True, key="dash_p1_buf_chk")
            st.slider("Heat Intensity Radius", min_value=15, max_value=45, value=28, step=5, key="dash_p1_heat_slider")
            st.selectbox("Safety Buffer Radius", options=["250 Meters", "500 Meters", "1000 Meters"], index=1, key="dash_p1_buf_sel")

    with p2:
        with st.container(border=True):
            st.markdown('''
            <div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; font-family:'Space Grotesk', sans-serif;">
                RISK TREND (LAST 24 HOURS)
            </div>
            <div style="display:flex; gap:10px; font-size:0.68rem; font-family:'JetBrains Mono', monospace; margin-bottom:6px;">
                <span style="color:#ef4444;">● High Risk</span>
                <span style="color:#f59e0b;">● Medium Risk</span>
                <span style="color:#10b981;">● Low Risk</span>
            </div>
            ''', unsafe_allow_html=True)
            trend_df = pd.DataFrame({
                "High Risk": [68, 74, 82, 65, 78, 85, 76],
                "Medium Risk": [45, 52, 48, 55, 42, 50, 48],
                "Low Risk": [18, 22, 16, 25, 20, 15, 21]
            }, index=["10 AM", "2 PM", "6 PM", "10 PM", "2 AM", "6 AM", "10 AM"])
            st.line_chart(trend_df, color=["#ef4444", "#f59e0b", "#10b981"], height=160)

    with p3:
        with st.container(border=True):
            st.markdown('''
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                <div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; font-family:'Space Grotesk', sans-serif;">
                    ALERT SUMMARY
                </div>
                <span style="font-size:0.72rem; color:#f97316; font-weight:700; font-family:'JetBrains Mono', monospace;">View All</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:6px; margin-bottom:10px;">
                <div style="background:rgba(239,68,68,0.10); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:7px 10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.74rem; font-weight:700; color:#f87171;">⚠️ High Risk Detected</span>
                        <span style="font-size:0.64rem; color:#9ca3af; font-family:'JetBrains Mono', monospace;">2 min ago</span>
                    </div>
                    <div style="font-size:0.70rem; color:#cbd5e1; margin-top:2px;">JM Road, Pune</div>
                </div>
                <div style="background:rgba(245,158,11,0.10); border:1px solid rgba(245,158,11,0.3); border-radius:6px; padding:7px 10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.74rem; font-weight:700; color:#fbbf24;">⚡ Accident Prone Zone</span>
                        <span style="font-size:0.64rem; color:#9ca3af; font-family:'JetBrains Mono', monospace;">12 min ago</span>
                    </div>
                    <div style="font-size:0.70rem; color:#cbd5e1; margin-top:2px;">Kharadi Bypass</div>
                </div>
                <div style="background:rgba(245,158,11,0.10); border:1px solid rgba(245,158,11,0.3); border-radius:6px; padding:7px 10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.74rem; font-weight:700; color:#fbbf24;">🚗 Heavy Traffic Congestion</span>
                        <span style="font-size:0.64rem; color:#9ca3af; font-family:'JetBrains Mono', monospace;">18 min ago</span>
                    </div>
                    <div style="font-size:0.70rem; color:#cbd5e1; margin-top:2px;">Hinjewadi Phase 1</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)


    with p4:
        with st.container(border=True):
            st.markdown('<div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; font-family:\'Space Grotesk\', sans-serif;">QUICK ACTIONS</div>', unsafe_allow_html=True)
            
            # Working Safety Audit Report CSV download
            audit_report_df = pd.DataFrame([
                {
                    "Junction ID": j.get("junction_id", ""),
                    "Name": j.get("name", ""),
                    "City": j.get("city", "Pune"),
                    "Risk Level": j.get("risk_level", "LOW"),
                    "Risk Score": j.get("risk_score", 0.0),
                    "Latitude": j.get("lat", 0.0),
                    "Longitude": j.get("lon", 0.0),
                    "Last Updated": j.get("last_updated", "")
                }
                for j in filtered_junctions
            ])
            report_csv = audit_report_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📄 Generate Report (CSV)",
                data=report_csv,
                file_name=f"JunctionGuard_Safety_Audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="dash_p4_action_rep",
                use_container_width=True
            )

            # Working Spatial GeoJSON export download
            geojson_dict = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(j.get("lon", 0.0)), float(j.get("lat", 0.0))]
                        },
                        "properties": {
                            "junction_id": j.get("junction_id", ""),
                            "name": j.get("name", ""),
                            "risk_level": j.get("risk_level", "LOW"),
                            "risk_score": float(j.get("risk_score", 0.0)),
                            "city": j.get("city", "Pune")
                        }
                    }
                    for j in filtered_junctions
                ]
            }
            geojson_str = json.dumps(geojson_dict, indent=2).encode('utf-8')
            st.download_button(
                label="📥 Export GIS Data (GeoJSON)",
                data=geojson_str,
                file_name=f"JunctionGuard_Spatial_{datetime.now().strftime('%Y%m%d_%H%M')}.geojson",
                mime="application/geo+json",
                key="dash_p4_action_exp",
                use_container_width=True
            )


# ----------------------------------------------------
# 2. INTERACTIVE ALERT MAP
# ----------------------------------------------------
elif sidebar_nav == "Interactive Alert Map":
    map_h_col1, map_h_col2 = st.columns([1, 1])
    with map_h_col1:
        st.markdown('<div class="panel-title" style="font-size:0.95rem; font-weight:700; color:#ffffff; letter-spacing:0.04em; text-transform:uppercase; margin-top:6px;">INTERACTIVE RISK MAP &amp; HOTSPOT SPATIAL INTELLIGENCE</div>', unsafe_allow_html=True)
    with map_h_col2:
        base_view_mode = st.selectbox(
            "Map Mode",
            options=[
                "Heatmap Mode",
                "Dark Tactical",
                "Satellite Imagery",
                "Street Navigation"
            ],
            index=0,
            label_visibility="collapsed",
            key="iam_map_mode_select"
        )

    col_iam_map, col_iam_tools = st.columns([2.3, 1])
    with col_iam_map:
        render_surveillance_folium_map(base_view_mode, height=490, key_prefix="iam")
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; background:#12151a; border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:6px 12px; margin-top:6px; font-size:0.72rem; font-family:'JetBrains Mono', monospace;">
            <span style="color:#9ca3af;">RISK LEVEL:</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#f87171;"><span class="live-dot-red"></span> HIGH</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#fbbf24;"><span style="width:6px; height:6px; border-radius:50%; background:#f59e0b; display:inline-block;"></span> MEDIUM</span>
            <span style="display:inline-flex; align-items:center; gap:5px; color:#34d399;"><span style="width:6px; height:6px; border-radius:50%; background:#10b981; display:inline-block;"></span> LOW</span>
        </div>
        """, unsafe_allow_html=True)

    with col_iam_tools:
        with st.container(border=True):
            st.markdown('<div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; font-family:\'Space Grotesk\', sans-serif;">SPATIAL RISK FILTERS</div>', unsafe_allow_html=True)
            st.checkbox("🔥 Accident Density Heatmap", value=True, key="iam_heat_chk")
            st.checkbox("🛡️ Hazard Conflict Buffers", value=True, key="iam_buf_chk")
            st.slider("Heat Intensity Radius", min_value=15, max_value=45, value=28, step=5, key="iam_heat_slider")
            st.selectbox("Safety Buffer Radius", options=["250 Meters", "500 Meters", "1000 Meters"], index=1, key="iam_buf_sel")

        with st.container(border=True):
            st.markdown('<div style="font-size: 0.82rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; font-family:\'Space Grotesk\', sans-serif;">JUNCTION INSPECTOR</div>', unsafe_allow_html=True)
            j_inspect_options = [j["name"] for j in filtered_junctions]
            if j_inspect_options:
                chosen_inspect = st.selectbox("Inspect Junction", options=j_inspect_options, index=0, key="iam_inspect_jnc")
                j_obj = next((j for j in filtered_junctions if j["name"] == chosen_inspect), None)
                if j_obj:
                    j_lvl = (j_obj.get("risk_level") or "LOW").upper()
                    j_score = j_obj.get("risk_score") or 0.0
                    st.markdown(f"""
                    <div style="margin-top: 8px; padding: 8px 10px; background: rgba(255,255,255,0.03); border-radius: 6px; font-family:'JetBrains Mono', monospace; font-size: 0.74rem;">
                        <div>Score: <b style="color:{'#f87171' if j_lvl=='HIGH' else '#fbbf24' if j_lvl=='MEDIUM' else '#34d399'}">{j_score:.1f}/100</b></div>
                        <div style="margin-top: 4px;">Status: <b>{j_lvl}</b></div>
                        <div style="margin-top: 4px; color:#9ca3af;">Coords: {j_obj.get('lat', 0):.4f}, {j_obj.get('lon', 0):.4f}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div style="font-size: 0.85rem; font-weight: 700; color: #ffffff; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; font-family:\'Space Grotesk\', sans-serif;">MONITORED JUNCTIONS SPATIAL RISK INVENTORY</div>', unsafe_allow_html=True)
        jnc_table_data = []
        for j in filtered_junctions:
            jnc_table_data.append({
                "Junction Name": j.get("name", "Unknown"),
                "City": j.get("city", "Pune"),
                "Risk Level": j.get("risk_level", "LOW"),
                "Risk Score": f"{j.get('risk_score', 0.0):.1f} / 100",
                "Latitude": f"{j.get('lat', 0.0):.4f}",
                "Longitude": f"{j.get('lon', 0.0):.4f}",
            })
        if jnc_table_data:
            st.dataframe(pd.DataFrame(jnc_table_data), use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 3. EXPLAINABILITY & CONTRIBUTING FACTORS
# ----------------------------------------------------
elif sidebar_nav == "Explainability & Factor Breakdown":
    st.subheader("Explainable Junction Risk Scoring Engine")
    st.markdown("Unlike black-box models, JunctionGuard AI exposes the **exact factor weight breakdown** driving each score.")

    col_select, col_details = st.columns([1, 2])

    with col_select:
        jnc_names = {j["name"]: j["junction_id"] for j in junctions}
        j_keys = list(jnc_names.keys())
        default_idx = j_keys.index(sidebar_selected_jnc) if sidebar_selected_jnc in j_keys else 0
        selected_name = st.selectbox("Select Junction to Analyze", options=j_keys, index=default_idx)
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

            top_factors = jnc_data["contributing_factors"]
            if top_factors and top_factors[0].get("factor") in ["Citizen Reports", "Citizen Hazard Reports"]:
                try:
                    from src.analytics.risk_engine import get_citizen_cluster_stats
                    cluster_info = get_citizen_cluster_stats(selected_id)
                    sub_line = cluster_info.get("summary_line")
                except Exception:
                    sub_line = None
                if sub_line:
                    st.markdown(f"""
                    <div style="background: rgba(245, 158, 11, 0.12); border-left: 3px solid #f59e0b; border-radius: 6px; padding: 7px 12px; margin: 8px 0 14px 0; font-size: 0.82rem; color: #fbbf24;">
                        📢 <b>Citizen Alert Cluster:</b> {sub_line}
                    </div>
                    """, unsafe_allow_html=True)
            
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
# 4. LIVE CCTV VISION ANALYTICS (TRACK A)
# ----------------------------------------------------
elif sidebar_nav == "Live CCTV Vision Analytics":
    st.subheader("Real-Time CCTV Video Analytics (YOLOv8 + OpenCV)")
    st.markdown(
        "Processes intersection CCTV streams to detect vehicle counts, pedestrian exposure, "
        "high **two-wheeler weaving density** (critical for Indian traffic), and spatial near-miss proximity."
    )

    demo_sources = {
        "🎬 Demo Clip 1: Shivaji Chowk (J001) - Dense Urban Crossing": {"video": "data/sample_videos/indian_traffic_1.mp4", "jnc_id": "J001", "name": "Shivaji Chowk"},
        "🎬 Demo Clip 2: Rajaram Corner (J002) - Multi-Lane Arterial Junction": {"video": "data/sample_videos/indian_traffic_2.mp4", "jnc_id": "J002", "name": "Rajaram Corner"},
        "🎬 Demo Clip 3: Dabholkar Corner (J003) - Bus Terminal & Commercial Crossing": {"video": "data/sample_videos/indian_traffic_3.mp4", "jnc_id": "J003", "name": "Dabholkar Corner"},
        "🎬 Demo Clip 4: Cyber Chowk (J004) - High-Density Two-Wheeler & Mixed Flow": {"video": "data/sample_videos/indian_traffic_4.mp4", "jnc_id": "J004", "name": "Cyber Chowk"},
        "🎬 Demo Clip 5: Kawala Naka (J005) - Heavy Vehicle Bottleneck & Peak Hour Traffic": {"video": "data/sample_videos/indian_traffic_5.mp4", "jnc_id": "J005", "name": "Kawala Naka"},
        "💻 Live Synthetic Junction Stream": {"video": None, "jnc_id": None, "name": "Synthetic Stream"}
    }

    source_label = st.selectbox("Select CCTV Feed / Demo Clip Source:", options=list(demo_sources.keys()), index=0)
    selected_meta = demo_sources[source_label]

    v_col1, v_col2 = st.columns([2, 1])

    with v_col1:
        run_vision = st.checkbox("▶️ Play CCTV Video Stream Overlay", value=True)
        video_placeholder = st.empty()

    with v_col2:
        st.write("#### 📐 Vision & Spatial Indicators (Supabase Cached)")
        st.info("YOLOv8 Class Highlights: Motorcycle (Cyan), Pedestrian (Red), Cars (Green), Heavy (Orange)")

        # Fetch pre-computed Supabase / SQLite indicators if available
        sb_indicators = {}
        if selected_meta["jnc_id"]:
            try:
                from src.supabase_client import fetch_detection_indicators
                records = fetch_detection_indicators(selected_meta["jnc_id"])
                # Match by video filename if multiple records exist
                matched = [r for r in records if r.get("source_video") == os.path.basename(selected_meta["video"])]
                if matched:
                    sb_indicators = matched[-1]
            except Exception:
                pass

            if not sb_indicators:
                try:
                    from src.database import fetch_detection_indicators_from_db
                    records = fetch_detection_indicators_from_db(selected_meta["jnc_id"])
                    matched = [r for r in records if r.get("source_video") == os.path.basename(selected_meta["video"])]
                    if matched:
                        sb_indicators = matched[0]
                except Exception:
                    pass

        if sb_indicators:
            st.success("⚡ Loaded pre-computed indicators (Zero Inference Latency)")
            st.metric("Traffic Density (avg vehicles/frame)", f"{sb_indicators.get('traffic_density', 0.0)}")
            st.metric("Speed / Movement Proxy", f"{sb_indicators.get('speed_proxy', 0.0)} px/s")
            st.metric("Pedestrian Activity Level", f"{sb_indicators.get('pedestrian_activity', 0.0)} peds/frame")
            st.metric("Conflict / Near-Miss Proxy Count", f"{sb_indicators.get('conflict_proxy', 0)}")
        else:
            metric_risk = st.empty()
            metric_veh = st.empty()
            metric_2w = st.empty()
            metric_near = st.empty()

            metric_risk.metric("Vision Risk Index", "-- / 100")
            metric_veh.metric("Total Detected Vehicles", "--")
            metric_2w.metric("Two-Wheeler Share (Indian Context)", "--%")
            metric_near.metric("Near-Miss Proximity Conflicts", "--")

    if run_vision:
        processor = StreamProcessor()
        video_file = selected_meta["video"]

        if video_file and os.path.exists(video_file):
            stream_gen = processor.process_video_stream(video_file, max_frames=80, step=3)
            has_frames = False
            for frame_idx, (processed_frame, metrics) in enumerate(stream_gen):
                has_frames = True
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, caption=f"YOLOv8 Analysis - {selected_meta['name']} (Frame {frame_idx * 3})", width="stretch")
                if not sb_indicators:
                    metric_risk.metric("Vision Risk Index", f"{metrics.get('vision_risk_score', 0.0)} / 100")
                    metric_veh.metric("Total Detected Vehicles", f"{metrics.get('total_vehicles', 0)}")
                    metric_2w.metric("Two-Wheeler Share (Indian Context)", f"{metrics.get('two_wheeler_share_pct', 0.0)}%")
                    metric_near.metric("Near-Miss Proximity Conflicts", f"{metrics.get('near_miss_count', 0)}")
                time.sleep(0.04)

            if not has_frames:
                video_placeholder.warning("⚠️ Error Handled: This video file is corrupt or unreadable. System handled the error gracefully without crashing.")
        else:
            for frame_idx in range(1, 30):
                processed_frame, metrics = processor.generate_simulated_frame(frame_idx)
                frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, caption=f"Silk Board Junction CCTV - Frame {frame_idx}", width="stretch")
                if not sb_indicators:
                    metric_risk.metric("Vision Risk Index", f"{metrics.get('vision_risk_score', 0.0)} / 100")
                    metric_veh.metric("Total Detected Vehicles", f"{metrics.get('total_vehicles', 0)}")
                    metric_2w.metric("Two-Wheeler Share (Indian Context)", f"{metrics.get('two_wheeler_share_pct', 0.0)}%")
                    metric_near.metric("Near-Miss Proximity Conflicts", f"{metrics.get('near_miss_count', 0)}")
                time.sleep(0.08)

# ----------------------------------------------------
# 5. CITIZEN HAZARD REPORTING
# ----------------------------------------------------
elif sidebar_nav == "Citizen Hazard Reporting":
    if "submitted_report_msg" in st.session_state:
        st.success(st.session_state.pop("submitted_report_msg"))

    c_map, c_form = st.columns([1, 1])

    # ── Map Fragment: isolate map interactions so full app doesn't rerun/flash ──
    @st.fragment
    def render_tab_map_picker():
        # 🔍 Quick Search Location Bar
        search_c1, search_c2 = st.columns([3, 1])
        with search_c1:
            search_query = st.text_input(
                "Search location",
                placeholder="🔍 Search area, road, or city (e.g. Kolhapur, Koge, MG Road...)",
                label_visibility="collapsed",
                key="tab_map_search_txt"
            )
        with search_c2:
            if st.button("🔍 Find", key="tab_map_search_btn", use_container_width=True):
                if search_query and search_query.strip():
                    with st.spinner("Searching..."):
                        from src.geo_utils import forward_geocode_location
                        found = forward_geocode_location(search_query.strip())
                    if found:
                        f_lat, f_lon, f_name = found
                        st.session_state["tab_picked_lat"] = f_lat
                        st.session_state["tab_picked_lng"] = f_lon
                        st.session_state["selected_junction_name_val"] = f_name
                        st.session_state["tab_select_junction_dropdown"] = f_name
                        st.session_state["sync_dropdown_from_map"] = f_name
                        st.rerun(scope="app")
                    else:
                        st.warning("Location not found. Try a nearby landmark or city.")

        all_jnc_list = fetch_all_junctions()
        if "tab_picked_lat" in st.session_state and "tab_picked_lng" in st.session_state:
            initial_lat = float(st.session_state["tab_picked_lat"])
            initial_lon = float(st.session_state["tab_picked_lng"])
            initial_zoom = 15
        else:
            pune_jnc = next((j for j in all_jnc_list if "Pune" in j.get("city", "") or "Shivaji" in j["name"]), None)
            initial_lat = pune_jnc['lat'] if pune_jnc else (all_jnc_list[0]['lat'] if all_jnc_list else 18.5204)
            initial_lon = pune_jnc['lon'] if pune_jnc else (all_jnc_list[0]['lon'] if all_jnc_list else 73.8567)
            initial_zoom = 12

        m_picker = folium.Map(
            location=[initial_lat, initial_lon],
            zoom_start=initial_zoom,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Dark Gray Canvas"
        )

        LocateControl(
            auto_start=False,
            flyTo=True,
            keepCurrentZoomLevel=False,
            position='topleft',
            strings={"title": "🎯 Locate My Exact Device GPS Position"}
        ).add_to(m_picker)

        # Anti-flicker CSS injected inside map iframe (Bug 1 Fix)
        map_inner_css = """
        <style>
        .leaflet-container, .leaflet-grab, .leaflet-interactive, .leaflet-drag-target {
            cursor: crosshair !important;
            background-color: #081425 !important;
        }
        .leaflet-tile, .leaflet-pane, .leaflet-tile-pane, .leaflet-tile-container img {
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
            opacity: 1 !important;
        }
        .leaflet-tile:hover {
            filter: none !important;
            -webkit-filter: none !important;
            opacity: 1 !important;
        }
        .leaflet-marker-icon {
            background: transparent !important;
            border: none !important;
        }
        </style>
        """
        m_picker.get_root().html.add_child(folium.Element(map_inner_css))

        for jnc in all_jnc_list:
            level = (jnc.get("risk_level") or "LOW").upper()
            m_col = "#ef4444" if level == "HIGH" else ("#f59e0b" if level == "MEDIUM" else "#10b981")
            m_html = f'<div style="width:18px; height:18px; border-radius:50%; background:{m_col}; box-shadow:0 0 10px {m_col}; border:2px solid #ffffff;"></div>'
            folium.Marker(
                [jnc['lat'], jnc['lon']],
                popup=jnc['name'],
                tooltip=f"Junction: {jnc['name']} ({level})",
                icon=folium.DivIcon(html=m_html, icon_size=(18, 18), icon_anchor=(9, 9), class_name="junction-heat-marker")
            ).add_to(m_picker)

        if "tab_picked_lat" in st.session_state and "tab_picked_lng" in st.session_state:
            p_lat = st.session_state["tab_picked_lat"]
            p_lng = st.session_state["tab_picked_lng"]
            pin_html = '<div style="width:26px; height:26px; border-radius:50%; background:#ef4444; box-shadow:0 0 16px #ef4444; border:3px solid #ffffff; display:flex; align-items:center; justify-content:center;"><div style="width:6px; height:6px; background:#fff; border-radius:50%;"></div></div>'
            folium.Marker(
                [p_lat, p_lng],
                popup=folium.Popup(f"<b>📍 Selected Hazard Location</b><br>({p_lat:.5f}, {p_lng:.5f})", max_width=250),
                tooltip="📍 Selected Hazard Pinpoint",
                icon=folium.DivIcon(html=pin_html, icon_size=(26, 26), icon_anchor=(13, 13), class_name="junction-heat-marker")
            ).add_to(m_picker)

        map_data = st_folium(
            m_picker,
            width="stretch",
            height=380,
            key=f"citizen_tab_map_picker_{round(initial_lat, 4)}_{round(initial_lon, 4)}",
            returned_objects=["last_clicked"],
            return_on_hover=False
        )

        if map_data and map_data.get("last_clicked"):
            c_lat = map_data["last_clicked"]["lat"]
            c_lng = map_data["last_clicked"]["lng"]
            if st.session_state.get("tab_picked_lat") != c_lat or st.session_state.get("tab_picked_lng") != c_lng:
                st.session_state["tab_picked_lat"] = c_lat
                st.session_state["tab_picked_lng"] = c_lng

                near_jnc, dist_km = find_nearest_junction(c_lat, c_lng, all_jnc_list, threshold_km=1.0)
                det_val = near_jnc['name'] if near_jnc else reverse_geocode_location(c_lat, c_lng)

                st.session_state["selected_junction_name_val"] = det_val
                st.session_state["tab_select_junction_dropdown"] = det_val
                st.session_state["sync_dropdown_from_map"] = det_val
                # Full page rerun so c_form selectbox picks up the new location
                st.rerun(scope="app")

        # ── Status bar: detected name, coordinates, Reset Location button ──
        if "tab_picked_lat" in st.session_state and "tab_picked_lng" in st.session_state:
            click_lat = st.session_state["tab_picked_lat"]
            click_lng = st.session_state["tab_picked_lng"]
            all_jnc_list2 = fetch_all_junctions()
            near_jnc2, dist_km2 = find_nearest_junction(click_lat, click_lng, all_jnc_list2, threshold_km=1.0)
            if near_jnc2:
                st.success(f"✅ **Junction Auto-Detected**: {near_jnc2['name']} ({round(dist_km2*1000)}m away)")
            else:
                st.success(f"📍 **Pinpoint Auto-Detected**: {st.session_state.get('selected_junction_name_val', '')}")

            st.markdown(
                f'<div style="margin-top:4px; font-size:0.76rem; color:#64748b; font-family:monospace;">'
                f'🌐 Lat: <code style="color:#a5b4fc">{click_lat:.6f}</code>&nbsp;&nbsp;'
                f'Lng: <code style="color:#a5b4fc">{click_lng:.6f}</code></div>',
                unsafe_allow_html=True
            )

            if st.button("🗑️ Reset Location", key="tab_reset_loc_btn", use_container_width=True):
                for k in ["tab_picked_lat", "tab_picked_lng",
                          "selected_junction_name_val", "tab_select_junction_dropdown"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            st.caption("🖱️ Click anywhere on the map to drop a hazard pin.")

        # ── Live Device Hardware GPS & Network Auto-Detection ──
        st.markdown("---")
        gps_html = """
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        * { box-sizing: border-box; }
        body { margin: 0; padding: 0; background: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .btn-gps {
            width: 100%;
            background: linear-gradient(135deg, #059669 0%, #0284c7 100%);
            color: #ffffff;
            border: none;
            padding: 11px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35);
            transition: all 0.2s ease;
        }
        .btn-gps:hover { opacity: 0.92; }
        #msg { margin-top: 6px; font-size: 0.76rem; color: #cbd5e1; text-align: center; line-height: 1.35; }
        </style>
        </head>
        <body>
        <button class="btn-gps" id="locate-btn" onclick="getExactLocation()">
            🎯 Device GPS Location
        </button>
        <div id="msg"></div>
        <script>
        function getExactLocation() {
            var btn = document.getElementById("locate-btn");
            var msg = document.getElementById("msg");
            btn.disabled = true;
            btn.style.opacity = "0.7";
            msg.innerHTML = "<span style='color:#38bdf8;'>⏳ Requesting live GPS... Please click <b>Allow</b>.</span>";

            if (!navigator.geolocation) {
                msg.innerHTML = "<span style='color:#ef4444;'>❌ Geolocation not supported in this browser.</span>";
                btn.disabled = false;
                btn.style.opacity = "1.0";
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    var lat = pos.coords.latitude;
                    var lng = pos.coords.longitude;
                    var acc = Math.round(pos.coords.accuracy || 0);
                    msg.innerHTML = "<span style='color:#34d399; font-weight:600;'>✅ Exact location found (±" + acc + "m)! Updating map...</span>";
                    setTimeout(function() {
                        var target = "/?geo_lat=" + encodeURIComponent(lat) + "&geo_lng=" + encodeURIComponent(lng) + "&nav=" + encodeURIComponent("Citizen Hazard Reporting");
                        try {
                            window.top.location.href = target;
                        } catch(e) {
                            try {
                                window.parent.location.href = target;
                            } catch(e2) {
                                window.location.href = target;
                            }
                        }
                    }, 150);
                },
                function(err) {
                    btn.disabled = false;
                    btn.style.opacity = "1.0";
                    if (err.code === 1) {
                        msg.innerHTML = "<span style='color:#f87171;'>❌ <b>Permission Denied</b>: Click location icon in browser bar and click <b>Allow</b>.</span>";
                    } else if (err.code === 2) {
                        msg.innerHTML = "<span style='color:#fbbf24;'>⚠️ <b>Wi-Fi required</b>: Ensure Wi-Fi is ON in System Settings.</span>";
                    } else {
                        msg.innerHTML = "<span style='color:#fbbf24;'>⚠️ GPS timed out. Use Network Auto-Detect button.</span>";
                    }
                },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
            );
        }
        </script>
        </body>
        </html>
        """
        loc_c1, loc_c2 = st.columns([1, 1])
        with loc_c1:
            st_components.html(gps_html, height=80)
        with loc_c2:
            if st.button("🌐 Network / IP Auto-Detect", key="btn_ip_autodetect", use_container_width=True):
                with st.spinner("Detecting exact network location..."):
                    loc = get_ip_location()
                    if loc:
                        ip_lat, ip_lon, ip_name = loc
                        st.session_state["tab_picked_lat"] = ip_lat
                        st.session_state["tab_picked_lng"] = ip_lon
                        near_j, dist_km = find_nearest_junction(ip_lat, ip_lon, all_jnc_list, threshold_km=1.0)
                        det_name = near_j['name'] if near_j else (reverse_geocode_location(ip_lat, ip_lon) or ip_name)
                        st.session_state["selected_junction_name_val"] = det_name
                        st.session_state["tab_select_junction_dropdown"] = det_name
                        st.session_state["sync_dropdown_from_map"] = det_name
                        st.toast(f"📍 Detected: {det_name}")
                        st.rerun()
                    else:
                        st.error("Could not detect location via IP. Please use the map or city buttons.")

        # ── Quick City Jump Presets ──
        st.markdown("<div style='font-size:0.8rem; font-weight:600; color:#94a3b8; margin-top:6px; margin-bottom:6px;'>⚡ Quick Jump to City:</div>", unsafe_allow_html=True)
        q_col1, q_col2, q_col3, q_col4 = st.columns(4)
        with q_col1:
            if st.button("📍 Kolhapur", key="tab_quick_kolhapur", use_container_width=True):
                st.session_state["tab_picked_lat"] = 16.7050
                st.session_state["tab_picked_lng"] = 74.2433
                st.session_state["selected_junction_name_val"] = "Kolhapur, Maharashtra"
                st.session_state["tab_select_junction_dropdown"] = "Kolhapur, Maharashtra"
                st.session_state["sync_dropdown_from_map"] = "Kolhapur, Maharashtra"
                st.rerun()
        with q_col2:
            if st.button("📍 Bangalore", key="tab_quick_blr", use_container_width=True):
                st.session_state["tab_picked_lat"] = 12.9716
                st.session_state["tab_picked_lng"] = 77.5946
                st.session_state["selected_junction_name_val"] = "Bangalore, Karnataka"
                st.session_state["tab_select_junction_dropdown"] = "Bangalore, Karnataka"
                st.session_state["sync_dropdown_from_map"] = "Bangalore, Karnataka"
                st.rerun()
        with q_col3:
            if st.button("📍 Pune", key="tab_quick_pune", use_container_width=True):
                st.session_state["tab_picked_lat"] = 18.5204
                st.session_state["tab_picked_lng"] = 73.8567
                st.session_state["selected_junction_name_val"] = "Pune, Maharashtra"
                st.session_state["tab_select_junction_dropdown"] = "Pune, Maharashtra"
                st.session_state["sync_dropdown_from_map"] = "Pune, Maharashtra"
                st.rerun()
        with q_col4:
            if st.button("📍 Mumbai", key="tab_quick_mum", use_container_width=True):
                st.session_state["tab_picked_lat"] = 19.0760
                st.session_state["tab_picked_lng"] = 72.8777
                st.session_state["selected_junction_name_val"] = "Mumbai, Maharashtra"
                st.session_state["tab_select_junction_dropdown"] = "Mumbai, Maharashtra"
                st.session_state["sync_dropdown_from_map"] = "Mumbai, Maharashtra"
                st.rerun()

    with c_map:
        st.markdown("##### 📍 Pinpoint Location on Map")
        st.caption("Search area, click map, or use 🎯 Device GPS button to pinpoint hazard spot.")
        render_tab_map_picker()

    with c_form:
        st.markdown("##### 🚨 Hazard Details & Evidence")

        # ── Reset-form callback ──
        def _reset_tab_form():
            for k in [
                "tab_picked_lat", "tab_picked_lng",
                "selected_junction_name_val", "tab_select_junction_dropdown",
            ]:
                st.session_state.pop(k, None)

        # ── Build dynamic location dropdown ──
        all_db_junctions = fetch_all_junctions()
        jnc_names = {j["name"]: j["junction_id"] for j in all_db_junctions}
        current_loc = st.session_state.get("selected_junction_name_val", "")
        catalog_names = list(jnc_names.keys())

        loc_options = []
        if current_loc and current_loc not in catalog_names:
            loc_options.append(current_loc)
        for cname in catalog_names:
            if cname not in loc_options:
                loc_options.append(cname)
        loc_options.append("➕ Type Custom Location Manually...")

        # Sync dropdown from external map click or GPS only when requested
        if "sync_dropdown_from_map" in st.session_state:
            target_val = st.session_state.pop("sync_dropdown_from_map")
            if target_val in loc_options:
                st.session_state["tab_select_junction_dropdown"] = target_val

        # Callback when user explicitly interacts with the dropdown:
        def on_junction_dropdown_change():
            sel = st.session_state.get("tab_select_junction_dropdown")
            if sel and sel in jnc_names:
                sel_jnc = next((j for j in all_db_junctions if j["name"] == sel), None)
                if sel_jnc:
                    st.session_state["tab_picked_lat"] = sel_jnc["lat"]
                    st.session_state["tab_picked_lng"] = sel_jnc["lon"]
                    st.session_state["selected_junction_name_val"] = sel
            elif sel:
                st.session_state["selected_junction_name_val"] = sel

        if "tab_select_junction_dropdown" not in st.session_state or st.session_state["tab_select_junction_dropdown"] not in loc_options:
            if current_loc and current_loc in loc_options:
                st.session_state["tab_select_junction_dropdown"] = current_loc
            elif sidebar_selected_jnc != "All Junctions" and sidebar_selected_jnc in loc_options:
                st.session_state["tab_select_junction_dropdown"] = sidebar_selected_jnc
            else:
                st.session_state["tab_select_junction_dropdown"] = loc_options[0]

        selected_option = st.selectbox(
            "Select Junction / Location*",
            options=loc_options,
            key="tab_select_junction_dropdown",
            on_change=on_junction_dropdown_change
        )

        if selected_option == "➕ Type Custom Location Manually...":
            selected_jnc_name = st.text_input(
                "Enter Custom Location*",
                placeholder="e.g. MG Road & Brigade Junction, Bangalore",
                key="tab_custom_loc_input"
            )
        else:
            selected_jnc_name = selected_option

        rep_name = st.text_input("Reporter Name / Designation", placeholder="e.g. Traffic Marshal / Resident (Optional)")

        issue_categories = [
            "Pothole / Damaged Road Surface",
            "Broken Traffic Signal / Light",
            "Blind Spot / Obstructed View",
            "Frequent Speeding / Illegal U-turn",
            "Near-Miss Pedestrian Crossing",
            "Other (Specify below)"
        ]
        rep_issue_sel = st.selectbox("Issue Category", issue_categories)

        custom_issue = ""
        if rep_issue_sel == "Other (Specify below)":
            custom_issue = st.text_input("Specify Custom Issue Category*", placeholder="e.g. Waterlogging, Fallen Tree, Construction Obstruction...")

        rep_sev = st.slider("Hazard Severity (1 = Minor, 5 = Severe Hazard)", 1, 5, 3)
        rep_desc = st.text_area("Detailed Description", placeholder="Describe exact location, lane blockages, or timing...")

        uploaded_evidence = st.file_uploader(
            "Upload Photo or Video Evidence (Optional)",
            type=["jpg", "png", "jpeg", "mp4", "mov", "avi", "webm"]
        )

        tab_btn1, tab_btn2 = st.columns([3, 1])
        with tab_btn1:
            submit_btn = st.button("🚨 Submit Hazard Report", use_container_width=True, type="primary")
        with tab_btn2:
            st.button("🔄 Reset", use_container_width=True, on_click=_reset_tab_form, key="tab_reset_form_btn")

        if submit_btn:
            if not selected_jnc_name.strip():
                st.error("Please enter or select a junction location.")
            elif rep_issue_sel == "Other (Specify below)" and not custom_issue.strip():
                st.error("Please specify the custom issue category.")
            else:
                final_jnc_name = selected_jnc_name.strip()
                final_desc = rep_desc.strip() if rep_desc.strip() else f"Road hazard reported at {final_jnc_name}."
                target_id = jnc_names.get(final_jnc_name, f"J-CUSTOM-{uuid.uuid4().hex[:6].upper()}")

                # Determine final issue category
                if rep_issue_sel == "Other (Specify below)":
                    final_issue = custom_issue.strip()
                else:
                    final_issue = rep_issue_sel

                saved_filename = None
                saved_relative_path = None
                media_url = None
                
                if uploaded_evidence is not None:
                    file_ext = os.path.splitext(uploaded_evidence.name)[1].lower()
                    saved_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
                    reports_dir = os.path.join("data", "citizen_reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    media_dest = os.path.join(reports_dir, saved_filename)
                    
                    try:
                        # Extract full raw bytes using getvalue() to guarantee full uncorrupted file payload
                        file_bytes = uploaded_evidence.getvalue()
                        with open(media_dest, "wb") as f:
                            f.write(file_bytes)
                        saved_relative_path = os.path.join("data", "citizen_reports", saved_filename)

                        # Determine correct MIME content-type
                        guessed_mime = mimetypes.guess_type(uploaded_evidence.name)[0]
                        if not guessed_mime:
                            guessed_mime = "video/mp4" if file_ext in [".mp4", ".mov", ".avi", ".webm"] else "image/jpeg"

                        # Supabase Storage Upload
                        from src.supabase_client import upload_citizen_media_supabase
                        media_url = upload_citizen_media_supabase(
                            file_bytes,
                            saved_filename,
                            content_type=guessed_mime
                        )
                    except Exception as e:
                        print(f"[Evidence Upload Note] {e}")

                media_type_val = None
                if uploaded_evidence is not None:
                    file_ext = os.path.splitext(uploaded_evidence.name)[1].lower()
                    media_type_val = "video" if file_ext in [".mp4", ".mov", ".avi", ".webm"] else "photo"

                add_citizen_report(
                    target_id, rep_name, final_issue, rep_sev, final_desc,
                    media_filename=saved_filename,
                    media_relative_path=saved_relative_path,
                    media_url=media_url,
                    media_type=media_type_val
                )

                # Immediately trigger Explainable Risk Engine recalculation upon report submission
                try:
                    risk_engine.compute_junction_risk(target_id)
                except Exception as rx:
                    print(f"[Risk Engine Recalculation Note] {rx}")
                
                # Clear/reset picked map location and form session state
                st.session_state.pop("tab_picked_lat", None)
                st.session_state.pop("tab_picked_lng", None)
                st.session_state.pop("selected_junction_name_val", None)
                st.session_state.pop("tab_select_junction_dropdown", None)

                evidence_note = " 📹 Video evidence attached." if uploaded_evidence is not None else ""
                st.session_state["submitted_report_msg"] = f"🎉 **Hazard Report Successfully Submitted for '{final_jnc_name}'!**{evidence_note}"
                st.rerun()

    st.markdown("---")
    st.write("#### 🗂️ Recent Citizen & Officer Reports")
    reports = fetch_citizen_reports()
    if reports:
        for rep in reports[:10]: # Show top 10 recent
            j_id = rep.get("junction_id", "")
            issue = rep.get("issue_type", "Hazard")
            sev = rep.get("severity", 3)
            rep_by = rep.get("reporter_name", "Anonymous")
            ts = rep.get("timestamp", "")
            desc = rep.get("description", "")
            m_url = rep.get("media_url")
            m_rel = rep.get("media_relative_path")
            m_fn = rep.get("media_filename")

            # Check local file existence
            local_path = None
            if m_rel and os.path.exists(m_rel):
                local_path = m_rel
            elif m_fn and os.path.exists(os.path.join("data", "citizen_reports", m_fn)):
                local_path = os.path.join("data", "citizen_reports", m_fn)
            
            sev_badge = "🔴 High Risk" if sev >= 4 else ("🟡 Medium Risk" if sev >= 3 else "🟢 Low Risk")
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>📍 {j_id} - {issue}</strong>
                    <span style="font-size: 0.8rem; background: #1e293b; padding: 2px 8px; border-radius: 4px; color: #94a3b8;">{sev_badge}</span>
                </div>
                <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Reporter: {rep_by} | {ts}</div>
                <div style="font-size: 0.9rem; color: #cbd5e1; margin-top: 6px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Render video / image media preview if present
            if m_url:
                ext = os.path.splitext(m_url.split('?')[0])[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                    st.caption("📹 Video Evidence (Supabase Cloud)")
                    st.video(m_url)
                else:
                    st.image(m_url, caption="Evidence (Supabase Cloud)", use_container_width=True)
            elif local_path:
                ext = os.path.splitext(local_path)[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                    st.caption("📹 Video Evidence (Local Storage)")
                    st.video(local_path)
                else:
                    st.image(local_path, caption="Evidence (Local Storage)", use_container_width=True)
    else:
        st.write("No reports submitted yet.")

# ── Tactical Telemetry Footer ──
render_footer()
