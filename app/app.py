"""
JunctionGuard AI - Geographic Surveillance & Directory Portal
Provides search, filtering, and deep-dive risk diagnostics across all monitored Indian junctions.
"""

import streamlit as st
import folium
from folium.plugins import HeatMap, MiniMap, Fullscreen
from streamlit_folium import st_folium
import pandas as pd
from typing import Optional, List

# Internal imports from components and data loader
from data_loader import load_junctions
from components import (
    render_risk_badge,
    render_contributing_factors,
    render_awaiting_data_banner,
    inject_custom_styles,
    get_risk_badge_html,
    render_navbar,
    render_footer
)

# Page configuration
st.set_page_config(
    page_title="JunctionGuard AI | Civic Safety & GIS Surveillance",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styles for UI layout and styling
inject_custom_styles()

# ── Top Navigation Bar ──
render_navbar("Junction Directory")

# Load real junction records from SQLite database
junctions = load_junctions()

# Sidebar - Filters & Search
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 8px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 16px;">
        <img src="https://img.icons8.com/color/96/traffic-light.png" width="46" style="margin-bottom: 6px;">
        <div style="font-size: 1.1rem; font-weight: 800; color: #f1f5f9;">Surveillance Filters</div>
        <div style="font-size: 0.65rem; color: #34d399; background: rgba(16,185,129,0.12); display: inline-block;
                    padding: 3px 12px; border-radius: 9999px; margin-top: 4px; border: 1px solid rgba(16,185,129,0.25); font-weight:700;">
            ● 12 Active Nodes
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Search input
    search_query = st.text_input("🔍 Search Junctions", placeholder="Enter junction name or ID...").strip()
    
    # City filter
    available_cities = ["All Cities"] + sorted(list(set(j.city for j in junctions if j.city)))
    city_filter = st.selectbox("🏙️ Filter by City", options=available_cities)

    # Risk Level filter
    risk_filter = st.selectbox(
        "🚨 Filter by Risk Level",
        options=["All Levels", "HIGH", "MEDIUM", "LOW"]
    )
    
    # Sort dropdown
    sort_by = st.selectbox(
        "↕️ Sort Order",
        options=[
            "Risk Score (High to Low)",
            "Risk Score (Low to High)",
            "Name (A-Z)",
            "Name (Z-A)"
        ]
    )

# Filter Junctions Logic
filtered_junctions = []
for j in junctions:
    # 1. Search Query Filter
    if search_query:
        query_lower = search_query.lower()
        if query_lower not in j.name.lower() and query_lower not in j.junction_id.lower():
            continue
            
    # 2. City Filter
    if city_filter != "All Cities" and j.city != city_filter:
        continue

    # 3. Risk Level Filter
    if risk_filter != "All Levels":
        actual_level = j.risk_level.upper() if j.risk_level else "AWAITING DATA"
        if actual_level != risk_filter:
            continue
            
    filtered_junctions.append(j)

# Sort Junctions Logic
def get_sort_key(junction):
    if "Name" in sort_by:
        return junction.name
    else:
        score = junction.risk_score
        if score is None:
            return -1.0 if "High to Low" in sort_by else float('inf')
        return score

reverse_sort = "Z-A" in sort_by or "High to Low" in sort_by
filtered_junctions.sort(key=get_sort_key, reverse=reverse_sort)

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
total_jnc = len(junctions)
high_risk_count = sum(1 for j in junctions if j.risk_level == "HIGH")
avg_risk_score = round(sum(j.risk_score for j in junctions if j.risk_score is not None) / max(1, total_jnc), 1)
filtered_count = len(filtered_junctions)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📡 Monitored Nodes</div>
        <div class="metric-value" style="color: #f1f5f9;">{total_jnc}</div>
        <div class="metric-status"><span class="live-dot"></span> LIVE ACROSS 6 CITIES</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🚨 High-Risk Intersections</div>
        <div class="metric-value" style="color: #f87171;">{high_risk_count}</div>
        <div class="metric-status" style="color:#f87171;"><span class="live-dot" style="background:#ef4444; box-shadow:0 0 10px #ef4444;"></span> IMMEDIATE ATTENTION</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📊 Fleet Average Risk</div>
        <div class="metric-value" style="color: #fbbf24;">{avg_risk_score}<span style="font-size:1.1rem; color:#64748b;">/100</span></div>
        <div class="metric-status" style="color:#fbbf24;">● MODERATE BASELINE</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🎯 Active View Filter</div>
        <div class="metric-value" style="color: #38bdf8;">{filtered_count}</div>
        <div class="metric-status" style="color:#38bdf8;">● MATCHED JUNCTIONS</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Main Grid Layout (List panel on left, Folium Map on right)
col_list, col_map = st.columns([2, 3])

# Initial state for selected junction
if "selected_junction_id" not in st.session_state:
    st.session_state.selected_junction_id = junctions[0].junction_id if junctions else None

with col_list:
    st.markdown("### 📍 Junction Surveillance Roster")
    
    if not filtered_junctions:
        st.info("No junctions match the current search or filter criteria.")
    else:
        for j in filtered_junctions:
            is_selected = st.session_state.selected_junction_id == j.junction_id
            card_class = "junction-card-selected" if is_selected else "junction-card"
            
            badge_html = get_risk_badge_html(j.risk_level)

            if j.risk_level and j.risk_level.upper() == "HIGH":
                border_accent = "border-left: 4px solid #ef4444;"
                score_badge_style = "background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);"
            elif j.risk_level and j.risk_level.upper() == "MEDIUM":
                border_accent = "border-left: 4px solid #f59e0b;"
                score_badge_style = "background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);"
            elif j.risk_level and j.risk_level.upper() == "LOW":
                border_accent = "border-left: 4px solid #10b981;"
                score_badge_style = "background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);"
            else:
                border_accent = "border-left: 4px solid #6366f1;"
                score_badge_style = "background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3);"
            
            score_disp = f"{j.risk_score:.1f}" if j.risk_score is not None else "--"

            st.markdown(f"""
            <div class="{card_class}" style="{border_accent}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong style="color: #f1f5f9; font-size: 1rem;">{j.name}</strong>
                        <div style="font-size: 0.76rem; color: #64748b; margin-top: 3px; font-family: 'JetBrains Mono', monospace;">
                            <code>{j.junction_id}</code> &nbsp;•&nbsp; {j.city or 'India'} &nbsp;•&nbsp; {j.lat:.4f}, {j.lon:.4f}
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                        {badge_html}
                        <span style="font-size: 0.85rem; font-weight: 800; padding: 2px 8px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; {score_badge_style}">
                            {score_disp} <span style="font-size:0.68rem; font-weight:500;">/100</span>
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            btn_col_left, btn_col_right = st.columns([3, 1])
            with btn_col_right:
                if st.button("Inspect Node", key=f"btn_{j.junction_id}", width="stretch"):
                    st.session_state.selected_junction_id = j.junction_id
                    st.rerun()
            
            st.markdown("<div style='margin-bottom: 0.4rem;'></div>", unsafe_allow_html=True)

# Get the currently selected junction details
selected_junction = next((j for j in junctions if j.junction_id == st.session_state.selected_junction_id), None)

with col_map:
    st.markdown("### 🗺️ Geographic Surveillance & Radar View")
    
    if selected_junction:
        map_center = [selected_junction.lat, selected_junction.lon]
        map_zoom = 14
    elif filtered_junctions:
        avg_lat = sum(j.lat for j in filtered_junctions) / len(filtered_junctions)
        avg_lon = sum(j.lon for j in filtered_junctions) / len(filtered_junctions)
        map_center = [avg_lat, avg_lon]
        map_zoom = 12
    else:
        map_center = [20.5937, 78.9629]
        map_zoom = 5

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
    
    # 1. Base Tile Layers with no_wrap=True (Guarantees ONE single world map, no horizontal wrapping)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery, Maxar",
        name="🛰️ Real Satellite Imagery (HD)",
        overlay=False,
        control=True,
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenStreetMap contributors",
        name="🛣️ Street View (OpenStreetMap)",
        overlay=False,
        control=True,
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="&copy; CARTO",
        name="🌃 Dark Tactical View",
        overlay=False,
        control=True,
        no_wrap=True,
        bounds=[[-85, -180], [85, 180]]
    ).add_to(m)

    # 2. Add markers for all filtered junctions
    markers_layer = folium.FeatureGroup(name="📍 Junction Hotspots", overlay=True)
    for j in filtered_junctions:
        if j.risk_level is None:
            color = "blue"
            badge_bg = "#6366f1"
        elif j.risk_level.upper() == "LOW":
            color = "green"
            badge_bg = "#10b981"
        elif j.risk_level.upper() == "MEDIUM":
            color = "orange"
            badge_bg = "#f59e0b"
        elif j.risk_level.upper() == "HIGH":
            color = "red"
            badge_bg = "#ef4444"
        else:
            color = "blue"
            badge_bg = "#6366f1"
            
        is_current = (selected_junction and selected_junction.junction_id == j.junction_id)
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={j.lat},{j.lon}"

        popup_content = f"""
        <div style="font-family: 'Plus Jakarta Sans', system-ui, sans-serif; width: 230px; padding: 4px;">
            <h4 style="margin:0 0 4px 0; color:#0f172a; font-size:0.95rem; font-weight:800;">{j.name}</h4>
            <div style="font-size:0.75rem; color:#64748b; margin-bottom:6px;">ID: <code>{j.junction_id}</code> • {j.city or 'India'}</div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px; margin:4px 0;">
                <span style="background:{badge_bg}; color:white; padding:2px 8px; border-radius:9999px; font-size:0.68rem; font-weight:700;">
                    {j.risk_level or 'AWAITING DATA'}
                </span>
                <span style="font-size:0.88rem; font-weight:800; color:#334155; margin-left:6px; font-family:'JetBrains Mono', monospace;">
                    {f"{j.risk_score:.1f}/100" if j.risk_score is not None else "Pending Telemetry"}
                </span>
            </div>
            <div style="margin-top:8px; font-size:0.75rem;">
                <a href="{gmaps_url}" target="_blank" style="color:#2563eb; text-decoration:none; font-weight:700;">
                    📍 Open in Google Maps &rarr;
                </a>
            </div>
        </div>
        """
        
        folium.Marker(
            location=[j.lat, j.lon],
            popup=folium.Popup(popup_content, max_width=260),
            tooltip=f"{j.name} ({j.risk_level or 'Awaiting Data'})",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(markers_layer)
        
        # Danger halo / selection circle
        if is_current or (j.risk_level and j.risk_level.upper() == "HIGH"):
            circle_color = "red" if (j.risk_level and j.risk_level.upper() == "HIGH") else "#3b82f6"
            folium.Circle(
                location=[j.lat, j.lon],
                radius=250,
                color=circle_color,
                fill=True,
                fill_color=circle_color,
                fill_opacity=0.22,
                weight=2,
                dash_array="4, 4" if not is_current else None
            ).add_to(markers_layer)

    markers_layer.add_to(m)

    Fullscreen(position="topright").add_to(m)
    MiniMap(toggle_display=True, tile_layer="OpenStreetMap", position="bottomright", width=120, height=80).add_to(m)
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)
            
    st_folium(
        m,
        width="stretch",
        height=500,
        key=f"junctions_map_{st.session_state.selected_junction_id}",
        returned_objects=["last_object_clicked"],
        return_on_hover=False
    )

# Details Section Below
st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
if selected_junction:
    st.markdown(f"### 📊 Deep-Dive Risk Diagnostics: **{selected_junction.name}** ({selected_junction.city or 'India'})")
    
    col_detail_left, col_detail_right = st.columns([1, 2])
    
    with col_detail_left:
        if selected_junction.risk_level and selected_junction.risk_level.upper() == "HIGH":
            score_color = "#f87171"
        elif selected_junction.risk_level and selected_junction.risk_level.upper() == "MEDIUM":
            score_color = "#fbbf24"
        elif selected_junction.risk_level and selected_junction.risk_level.upper() == "LOW":
            score_color = "#34d399"
        else:
            score_color = "#a5b4fc"

        score_val = f"{selected_junction.risk_score:.1f}" if selected_junction.risk_score is not None else "N/A"

        st.markdown(f"""
        <div class="metric-card" style="padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 0.8rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">NODE ID</span>
                <code style="background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 2px 10px; border-radius: 9999px; font-weight:700;">
                    {selected_junction.junction_id}
                </code>
            </div>
            <div style="font-size: 0.82rem; color: #64748b; margin-bottom: 16px;">
                <b>Coordinates:</b> {selected_junction.lat:.4f}° N, {selected_junction.lon:.4f}° E
            </div>
            <div style="margin: 12px 0;">
                <div style="font-size: 0.78rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">COMPOSITE RISK INDEX</div>
                <div style="font-size: 2.6rem; font-weight: 800; color: {score_color}; font-family: 'JetBrains Mono', monospace; line-height: 1.1;">
                    {score_val}<span style="font-size: 1.2rem; color: #64748b; font-weight: 500;">/100</span>
                </div>
            </div>
            <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.06); display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size: 0.78rem; color: #94a3b8;">Risk Classification:</span>
                {get_risk_badge_html(selected_junction.risk_level)}
            </div>
            <div style="font-size: 0.72rem; color: #64748b; margin-top: 10px;">
                Last Calibrated: {selected_junction.last_updated or 'Just now'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_detail_right:
        st.markdown("""
        <div class="metric-card" style="padding: 20px;">
            <div style="font-size: 0.82rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; margin-bottom: 14px;">
                ⚖️ Explainable Factor Weights & Multi-Source Attribution (Sum = 100%)
            </div>
        """, unsafe_allow_html=True)
        render_contributing_factors(selected_junction.contributing_factors, junction_id=selected_junction.junction_id)
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Select a junction above to view its detailed breakdown.")

# ── Clean Branded Footer ──
render_footer()
