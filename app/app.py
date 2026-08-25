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
    get_risk_badge_html
)

# Page configuration
st.set_page_config(
    page_title="JunctionGuard AI | Explainable Road Safety",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styles for UI layout and styling
inject_custom_styles()

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
                Explainable AI System for Scoring Accident-Prone Road Junctions. Currently operating in simulation/disconnected mode.
            </p>
        </div>
    </div>
</div>
<div class="gradient-separator"></div>
""", unsafe_allow_html=True)

# Load junctions
junctions = load_junctions()

# Sidebar - Filters & Search
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 8px 0 16px 0; border-bottom: 1px solid rgba(51,65,85,0.4); margin-bottom: 16px;">
        <img src="https://img.icons8.com/color/96/traffic-light.png" width="50" style="margin-bottom: 6px;">
        <div style="font-size: 1.1rem; font-weight: 700; color: #f1f5f9;">Search & Filters</div>
        <div style="font-size: 0.65rem; color: #475569; background: rgba(51,65,85,0.3); display: inline-block;
                    padding: 2px 10px; border-radius: 9999px; margin-top: 4px; border: 1px solid rgba(71,85,105,0.3);">
            v1.0 • Simulation Mode
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Search input
    search_query = st.text_input("Search Junctions", placeholder="Enter name or ID...").strip()
    
    # Filter dropdown
    risk_filter = st.selectbox(
        "Filter by Risk Level",
        options=["All", "LOW", "MEDIUM", "HIGH", "AWAITING DATA"]
    )
    
    # Sort dropdown
    sort_by = st.selectbox(
        "Sort Junctions By",
        options=[
            "Name (A-Z)",
            "Name (Z-A)",
            "Risk Score (High to Low)",
            "Risk Score (Low to High)"
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
            
    # 2. Risk Level Filter
    if risk_filter != "All":
        actual_level = j.risk_level.upper() if j.risk_level else "AWAITING DATA"
        if actual_level != risk_filter:
            continue
            
    filtered_junctions.append(j)

# Sort Junctions Logic
def get_sort_key(junction):
    if "Name" in sort_by:
        return junction.name
    else:  # Risk Score Sorting
        # None values are treated as -1 for sorting high-low, or infinity for low-high
        score = junction.risk_score
        if score is None:
            return -1.0 if "High to Low" in sort_by else float('inf')
        return score

reverse_sort = "Z-A" in sort_by or "High to Low" in sort_by
filtered_junctions.sort(key=get_sort_key, reverse=reverse_sort)

# Main Grid Layout (List panel on left, Folium Map on right)
col_list, col_map = st.columns([2, 3])

# Initial state for selected junction
if "selected_junction_id" not in st.session_state:
    st.session_state.selected_junction_id = junctions[0].junction_id if junctions else None

with col_list:
    st.markdown("### 📍 Junction Directory")
    
    if not filtered_junctions:
        st.info("No junctions match the current filter criteria.")
    else:
        for j in filtered_junctions:
            # Check if this junction is currently selected
            is_selected = st.session_state.selected_junction_id == j.junction_id
            card_class = "junction-card-selected" if is_selected else "junction-card"
            
            # Badge html
            badge_html = get_risk_badge_html(j.risk_level)

            # Determine left-border accent color based on risk level
            if j.risk_level and j.risk_level.upper() == "HIGH":
                border_accent = "border-left: 4px solid #ef4444;"
            elif j.risk_level and j.risk_level.upper() == "MEDIUM":
                border_accent = "border-left: 4px solid #f59e0b;"
            elif j.risk_level and j.risk_level.upper() == "LOW":
                border_accent = "border-left: 4px solid #10b981;"
            else:
                border_accent = "border-left: 4px solid #6366f1;"
            
            # Render card using markdown
            st.markdown(f"""
            <div class="{card_class}" style="{border_accent}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #f1f5f9; font-size: 1.05rem;">{j.name}</strong>
                    {badge_html}
                </div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.4rem; font-family: 'Consolas', monospace;">
                    ID: {j.junction_id} &nbsp;•&nbsp; {j.lat:.4f}, {j.lon:.4f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Use columns or small buttons to select details
            btn_col_left, btn_col_right = st.columns([3, 1])
            with btn_col_right:
                if st.button("View details", key=f"btn_{j.junction_id}", use_container_width=True):
                    st.session_state.selected_junction_id = j.junction_id
                    st.rerun()
            
            st.markdown("<div style='margin-bottom: 0.3rem;'></div>", unsafe_allow_html=True)

# Get the currently selected junction details
selected_junction = next((j for j in junctions if j.junction_id == st.session_state.selected_junction_id), None)

with col_map:
    st.markdown("### 🗺️ Geographic Surveillance & GIS Overview")
    
    # Auto-focus on selected junction or center of filtered junctions
    if selected_junction:
        map_center = [selected_junction.lat, selected_junction.lon]
        map_zoom = 14
    elif filtered_junctions:
        avg_lat = sum(j.lat for j in filtered_junctions) / len(filtered_junctions)
        avg_lon = sum(j.lon for j in filtered_junctions) / len(filtered_junctions)
        map_center = [avg_lat, avg_lon]
        map_zoom = 12
    else:
        map_center = [16.7000, 74.2500]
        map_zoom = 12

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
        # Determine color
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
        <div style="font-family: 'Segoe UI', system-ui, sans-serif; width: 230px; padding: 4px;">
            <h4 style="margin:0 0 4px 0; color:#0f172a; font-size:0.9rem;">{j.name}</h4>
            <div style="font-size:0.75rem; color:#64748b; margin-bottom:6px;">ID: <code>{j.junction_id}</code></div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px; margin:4px 0;">
                <span style="background:{badge_bg}; color:white; padding:2px 6px; border-radius:9999px; font-size:0.65rem; font-weight:700;">
                    {j.risk_level or 'AWAITING DATA'}
                </span>
                <span style="font-size:0.8rem; font-weight:700; color:#334155; margin-left:6px;">
                    {f"{j.risk_score:.1f}/100" if j.risk_score is not None else "Pending Telemetry"}
                </span>
            </div>
            <div style="margin-top:6px; font-size:0.75rem;">
                <a href="{gmaps_url}" target="_blank" style="color:#3b82f6; text-decoration:none; font-weight:600;">
                    📍 Open in Google Maps &rarr;
                </a>
            </div>
        </div>
        """
        
        # Add primary marker
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
                fill_opacity=0.2,
                weight=2,
                dash_array="4, 4" if not is_current else None
            ).add_to(markers_layer)

    markers_layer.add_to(m)

    # 3. Interactive plugins
    Fullscreen(position="topright").add_to(m)
    MiniMap(toggle_display=True, tile_layer="OpenStreetMap", position="bottomright", width=120, height=80).add_to(m)
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)
            
    # Render map
    st_folium(m, width="stretch", height=490, key=f"junctions_map_{st.session_state.selected_junction_id}")

# Details Section Below
st.markdown("---")
if selected_junction:
    st.markdown(f"### 📊 Detailed Risk Diagnostics: {selected_junction.name} ({selected_junction.city or 'Kolhapur'})")
    
    col_detail_left, col_detail_right = st.columns([1, 2])
    
    with col_detail_left:
        # Determine score color
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
        <div class="detail-card">
            <p style="margin: 6px 0; font-size: 0.85rem;"><b style="color:#94a3b8;">Junction ID:</b>
                <code style="background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 2px 8px; border-radius: 4px;">{selected_junction.junction_id}</code></p>
            <p style="margin: 6px 0; font-size: 0.85rem;"><b style="color:#94a3b8;">Coordinates:</b>
                <span style="color: #cbd5e1;">{selected_junction.lat}, {selected_junction.lon}</span></p>
            <p style="margin: 10px 0;">
                <b style="color:#94a3b8; font-size: 0.85rem;">Risk Score:</b>
                <span style="font-size: 2rem; font-weight: 800; color: {score_color};">{score_val}<span style="font-size: 1rem; color: #64748b;">/100</span></span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.write("Risk Status:")
        render_risk_badge(selected_junction.risk_level)
        st.markdown(f"<p style='font-size: 0.75rem; color: #475569; margin-top: 8px;'>Last Updated: {selected_junction.last_updated or 'N/A'}</p>", unsafe_allow_html=True)
        
    with col_detail_right:
        st.markdown("**Risk Weight Contributors**")
        render_contributing_factors(selected_junction.contributing_factors)
else:
    st.info("Select a junction above to view its detailed breakdown.")

# ── Professional Footer ──
st.markdown("""
<div class="app-footer">
    <div class="footer-brand">🚨 JunctionGuard AI • Explainable Road Safety Intelligence</div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span class="footer-version">v1.0.0</span>
        <span style="font-size: 0.7rem; color: #475569;">OMNIKON Hackathon</span>
    </div>
</div>
""", unsafe_allow_html=True)
