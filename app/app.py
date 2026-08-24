import streamlit as st
import folium
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

# Header Section
st.markdown("""
<div style="background-color: #0f172a; padding: 1.5rem; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 2rem;">
    <h1 style="margin: 0; color: #f8fafc; font-size: 2rem;">🚨 JunctionGuard AI</h1>
    <p style="margin: 0.5rem 0 0 0; color: #94a3b8; font-size: 1rem;">
        Explainable AI System for Scoring Accident-Prone Road Junctions. Currently operating in simulation/disconnected mode.
    </p>
</div>
""", unsafe_allow_html=True)

# Load junctions
junctions = load_junctions()

# Sidebar - Filters & Search
with st.sidebar:
    st.markdown("### 🔍 Search & Filters")
    
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
            
            # Render card using markdown
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #f8fafc; font-size: 1.1rem;">{j.name}</strong>
                    {badge_html}
                </div>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.4rem;">
                    ID: {j.junction_id} | Coord: {j.lat:.4f}, {j.lon:.4f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Use columns or small buttons to select details
            btn_col_left, btn_col_right = st.columns([3, 1])
            with btn_col_right:
                if st.button("View details", key=f"btn_{j.junction_id}", use_container_width=True):
                    st.session_state.selected_junction_id = j.junction_id
                    st.rerun()
            
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

# Get the currently selected junction details
selected_junction = next((j for j in junctions if j.junction_id == st.session_state.selected_junction_id), None)

with col_map:
    st.markdown("### 🗺️ Geographic Overview")
    
    # India-centered map coordinates
    map_center = [20.5937, 78.9629]
    m = folium.Map(location=map_center, zoom_start=5, tiles="cartodbpositron")
    
    # Add markers for all filtered junctions
    for j in filtered_junctions:
        # Determine color
        if j.risk_level is None:
            color = "gray"
        elif j.risk_level.upper() == "LOW":
            color = "green"
        elif j.risk_level.upper() == "MEDIUM":
            color = "orange"
        elif j.risk_level.upper() == "HIGH":
            color = "red"
        else:
            color = "gray"
            
        # Tooltip text
        tooltip_text = f"<b>{j.name}</b><br>Risk: {j.risk_level or 'Awaiting Data'}"
        
        # Add primary marker
        folium.Marker(
            location=[j.lat, j.lon],
            tooltip=tooltip_text,
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)
        
        # If risk level is High, add an extra soft red halo circle
        if j.risk_level and j.risk_level.upper() == "HIGH":
            folium.Circle(
                location=[j.lat, j.lon],
                radius=150,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.15,
                weight=1
            ).add_to(m)
            
    # Render map
    st_folium(m, width="100%", height=450, key="junctions_map")

# Details Section Below
st.markdown("---")
if selected_junction:
    st.markdown(f"### 📊 Detailed Risk Diagnostics: {selected_junction.name} ({selected_junction.city or 'Kolhapur'})")
    
    col_detail_left, col_detail_right = st.columns([1, 2])
    
    with col_detail_left:
        st.markdown("<div style='background-color: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;'>", unsafe_allow_html=True)
        st.markdown(f"**Junction ID**: {selected_junction.junction_id}")
        st.markdown(f"**Coordinates**: {selected_junction.lat}, {selected_junction.lon}")
        
        # Display Risk Level & Score
        score_val = f"{selected_junction.risk_score:.1f}/100" if selected_junction.risk_score is not None else "N/A"
        st.markdown(f"**Risk Score**: `{score_val}`")
        st.write("Risk Status:")
        render_risk_badge(selected_junction.risk_level)
        st.markdown(f"**Last Updated**: {selected_junction.last_updated or 'N/A'}")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_detail_right:
        st.markdown("**Risk Weight Contributors**")
        render_contributing_factors(selected_junction.contributing_factors)
else:
    st.info("Select a junction above to view its detailed breakdown.")
