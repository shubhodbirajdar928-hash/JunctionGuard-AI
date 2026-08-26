import streamlit as st
import os
import sys
import json
import uuid
import mimetypes
from datetime import datetime

# Add the 'app' directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_junctions

import folium
from folium.plugins import LocateControl
from streamlit_folium import st_folium
import importlib
import src.geo_utils
importlib.reload(src.geo_utils)
from src.geo_utils import find_nearest_junction, reverse_geocode_location

# Page Config
st.set_page_config(
    page_title="Citizen Safety Reporting | JunctionGuard AI",
    page_icon="📣",
    layout="wide"
)

# ── Comprehensive CSS for Citizen Report Page ──
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

    /* ── Custom Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }

    /* ── Map Container Anti-Flicker & Dark Mode Integration ── */
    iframe[title*="st_folium"], .stFolium iframe {
        background-color: #0a0e1a !important;
        border-radius: 12px;
        border: 1px solid rgba(51, 65, 85, 0.4);
    }
    .leaflet-container {
        background-color: #0a0e1a !important;
    }
    .leaflet-tile-container img {
        transition: opacity 0.15s ease-in-out;
    }

    /* ── Section Headers ── */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #f1f5f9 !important;
    }

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

    /* ── Report Card ── */
    .report-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.75) 100%);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(51, 65, 85, 0.4);
        border-left: 4px solid #6366f1;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.25s ease;
    }
    .report-card:hover {
        border-color: rgba(99, 102, 241, 0.5);
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.1);
        transform: translateY(-1px);
    }
    .report-header {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid rgba(71, 85, 105, 0.3);
        padding-bottom: 0.5rem;
        margin-bottom: 0.75rem;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .report-junction {
        color: #a5b4fc;
        font-weight: 600;
    }
    .report-timestamp {
        color: #64748b;
        font-size: 0.78rem;
        background: rgba(51, 65, 85, 0.3);
        padding: 2px 10px;
        border-radius: 9999px;
        border: 1px solid rgba(71, 85, 105, 0.3);
    }
    .report-reporter {
        font-size: 0.9rem;
        margin-bottom: 0.6rem;
        color: #e2e8f0;
    }
    .report-description {
        font-size: 0.88rem;
        line-height: 1.6;
        color: #94a3b8;
    }

    /* ── Form Styling ── */
    .stForm {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.4);
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

    /* ── Submission Success Animation ── */
    @keyframes slideInUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .stSuccess {
        animation: slideInUp 0.4s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# Define directories
# The script is in app/pages/1_Citizen_Report.py, project root is two levels up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "citizen_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
INDEX_FILE = os.path.join(REPORTS_DIR, "reports.json")

def load_reports():
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_report(report_data):
    reports = load_reports()
    reports.append(report_data)
    try:
        with open(INDEX_FILE, "w") as f:
            json.dump(reports, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save report: {e}")
        return False

# ── Top Navigation Bar ──
st.markdown("""
<div class="cyber-navbar">
    <div class="navbar-brand">
        <div class="brand-radar">
            <span class="radar-icon">📣</span>
            <span class="radar-ring"></span>
        </div>
        <div>
            <div class="brand-title">Citizen Hazard <span class="brand-ai">Sentinel</span></div>
            <div class="brand-sub">Public Safety &amp; Crowdsourced Infrastructure Hazard Reporting</div>
        </div>
    </div>
    <div class="navbar-status-group">
        <div class="status-chip chip-online">
            <span class="live-dot"></span>
            <span>DISPATCH LIVE</span>
        </div>
        <div class="status-chip chip-nodes">
            <span>🛡️ CIVIC SENTINEL</span>
        </div>
    </div>
</div>
<div class="gradient-separator"></div>
""", unsafe_allow_html=True)

# Load the placeholder junctions
junctions = load_junctions()
junction_names = [j.name for j in junctions]

st.markdown("### 📝 File a Safety Report")

if "sentinel_submitted_msg" in st.session_state:
    st.success(st.session_state.pop("sentinel_submitted_msg"))
    st.balloons()

col_map, col_form = st.columns([1, 1])

with col_map:
    st.markdown("##### 📍 Pinpoint Location on Map")
    st.caption("Click anywhere on the map or use 📍 Current Location button to pinpoint the hazard spot.")
    
    default_lat = junctions[0].lat if junctions else 12.9716
    default_lon = junctions[0].lon if junctions else 77.5946
    
    m_picker = folium.Map(location=[default_lat, default_lon], zoom_start=13, tiles="OpenStreetMap")
    LocateControl(auto_start=False).add_to(m_picker)

    # Force precise target crosshair cursor instead of hand icon inside map frame
    custom_cursor_css = """
    <style>
    .leaflet-container, .leaflet-grab, .leaflet-interactive, .leaflet-drag-target {
        cursor: crosshair !important;
    }
    .leaflet-container:active, .leaflet-grab:active {
        cursor: crosshair !important;
    }
    </style>
    """
    m_picker.get_root().html.add_child(folium.Element(custom_cursor_css))

    for jnc in junctions:
        folium.Marker(
            [jnc.lat, jnc.lon],
            popup=jnc.name,
            tooltip=f"Junction: {jnc.name}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m_picker)

    # Render red pinpoint marker if user has selected a location
    if "sentinel_picked_lat" in st.session_state and "sentinel_picked_lng" in st.session_state:
        p_lat = st.session_state["sentinel_picked_lat"]
        p_lng = st.session_state["sentinel_picked_lng"]
        m_picker.location = [p_lat, p_lng]
        folium.Marker(
            [p_lat, p_lng],
            popup=folium.Popup(f"<b>📍 Selected Hazard Location</b><br>({p_lat:.5f}, {p_lng:.5f})", max_width=250),
            tooltip="📍 Selected Hazard Pinpoint",
            icon=folium.Icon(color="red", icon="flag")
        ).add_to(m_picker)

    # Restrict returned_objects to last_clicked to prevent cursor movement reruns and map brightness flicker
    map_data = st_folium(m_picker, width="100%", height=380, key="citizen_sentinel_map_picker", returned_objects=["last_clicked"])

    if map_data and map_data.get("last_clicked"):
        c_lat = map_data["last_clicked"]["lat"]
        c_lng = map_data["last_clicked"]["lng"]
        if st.session_state.get("sentinel_picked_lat") != c_lat or st.session_state.get("sentinel_picked_lng") != c_lng:
            st.session_state["sentinel_picked_lat"] = c_lat
            st.session_state["sentinel_picked_lng"] = c_lng

            near_jnc, dist_km = find_nearest_junction(c_lat, c_lng, junctions, threshold_km=1.0)
            if near_jnc:
                det_val = near_jnc.name
            else:
                det_val = reverse_geocode_location(c_lat, c_lng)

            st.session_state["sentinel_jnc_input"] = det_val
            st.session_state["sentinel_select_junction_dropdown"] = det_val
            st.rerun()

    detected_jnc_name = None
    detected_address = ""

    if "sentinel_picked_lat" in st.session_state and "sentinel_picked_lng" in st.session_state:
        click_lat = st.session_state["sentinel_picked_lat"]
        click_lng = st.session_state["sentinel_picked_lng"]
        near_jnc, dist_km = find_nearest_junction(click_lat, click_lng, junctions, threshold_km=1.0)
        if near_jnc:
            detected_jnc_name = near_jnc.name
            st.success(f"✅ **Cataloged Junction Auto-Detected**: {detected_jnc_name} ({round(dist_km*1000)}m away)")
        else:
            detected_address = reverse_geocode_location(click_lat, click_lng)
            st.success(f"📍 **Pinpoint Location Auto-Detected**: {detected_address}")

with col_form:
    st.markdown("##### 🚨 Hazard Details & Evidence")
    
    # Build dynamic list of location options including map auto-detected location
    current_loc = st.session_state.get("sentinel_jnc_input", "")
    
    loc_options = []
    if current_loc:
        loc_options.append(current_loc)
    for jname in junction_names:
        if jname not in loc_options:
            loc_options.append(jname)
    loc_options.append("➕ Type Custom Location Manually...")

    # Sync current_loc with selectbox widget state key
    if current_loc and st.session_state.get("sentinel_select_junction_dropdown") != current_loc:
        st.session_state["sentinel_select_junction_dropdown"] = current_loc

    selected_val = st.session_state.get("sentinel_select_junction_dropdown", loc_options[0])
    idx = loc_options.index(selected_val) if selected_val in loc_options else 0

    selected_option = st.selectbox(
        "Select Junction / Location*",
        options=loc_options,
        index=idx,
        key="sentinel_select_junction_dropdown"
    )

    if selected_option == "➕ Type Custom Location Manually...":
        selected_junction_name = st.text_input(
            "Enter Custom Location*",
            value="",
            placeholder="Click map or type exact location..."
        )
    else:
        selected_junction_name = selected_option
        st.session_state["sentinel_jnc_input"] = selected_option

    reporter_name = st.text_input("Your Name (Optional)", value="", placeholder="e.g. Anonymous / Traffic Police")

    issue_options = [
        "Pothole / Damaged Road Surface",
        "Broken Traffic Signal / Light",
        "Blind Spot / Obstructed View",
        "Frequent Speeding / Illegal U-turn",
        "Near-Miss Pedestrian Crossing",
        "Other (Specify below)"
    ]
    selected_issue = st.selectbox("Issue Category", options=issue_options)

    custom_issue_type = ""
    if selected_issue == "Other (Specify below)":
        custom_issue_type = st.text_input("Specify Custom Issue Category*", placeholder="e.g. Waterlogging, Broken Street Lamp, Construction Debris...")

    description = st.text_area("Hazard Description (Required)", placeholder="Describe the hazard, issue or accident hazard in detail...")
    
    uploaded_file = st.file_uploader(
        "Upload Photo or Video Evidence (Optional)", 
        type=["jpg", "png", "jpeg", "mp4", "mov", "avi", "webm"]
    )
    
    submit_button = st.button("🚨 Submit Safety Report", use_container_width=True)

# Handle Submission
if submit_button:
    if not description.strip():
        st.error("Please provide a description of the safety hazard.")
    elif not selected_junction_name.strip():
        st.error("Please enter or select a junction location.")
    elif selected_issue == "Other (Specify below)" and not custom_issue_type.strip():
        st.error("Please specify the custom issue category.")
    else:
        # Resolve junction details
        final_jnc_name = selected_junction_name.strip()
        selected_j = next((j for j in junctions if j.name == final_jnc_name), None)
        final_jnc_id = selected_j.junction_id if selected_j else f"J-CUSTOM-{uuid.uuid4().hex[:6].upper()}"

        # Resolve issue category
        if selected_issue == "Other (Specify below)":
            final_issue = custom_issue_type.strip()
        else:
            final_issue = selected_issue
        
        # Save media file
        saved_filename = None
        saved_relative_path = None
        media_url = None
        
        if uploaded_file is not None:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            saved_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
            media_dest = os.path.join(REPORTS_DIR, saved_filename)
            
            try:
                file_bytes = uploaded_file.getvalue()
                with open(media_dest, "wb") as f:
                    f.write(file_bytes)
                saved_relative_path = os.path.join("data", "citizen_reports", saved_filename)

                # Determine MIME type
                guessed_mime = mimetypes.guess_type(uploaded_file.name)[0]
                if not guessed_mime:
                    guessed_mime = "video/mp4" if file_ext in [".mp4", ".mov", ".avi", ".webm"] else "image/jpeg"

                # Upload to Supabase Storage
                from src.supabase_client import upload_citizen_media_supabase
                media_url = upload_citizen_media_supabase(
                    file_bytes,
                    saved_filename,
                    content_type=guessed_mime
                )
            except Exception as e:
                st.error(f"Failed to process media file: {e}")
        
        # Create report record
        new_report = {
            "report_id": uuid.uuid4().hex,
            "junction_id": final_jnc_id,
            "junction_name": final_jnc_name,
            "reporter_name": reporter_name.strip() if reporter_name.strip() else "Anonymous",
            "issue_type": final_issue,
            "description": description.strip(),
            "media_filename": saved_filename,
            "media_relative_path": saved_relative_path,
            "media_url": media_url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Sync to SQLite & Supabase tables
        try:
            from src.database import add_citizen_report
            add_citizen_report(
                junction_id=final_jnc_id,
                reporter=new_report["reporter_name"],
                issue=final_issue,
                severity=3,
                description=description.strip(),
                media_filename=saved_filename,
                media_relative_path=saved_relative_path,
                media_url=media_url
            )
        except Exception as ex:
            print(f"[Database Sync Note] {ex}")
        
        if save_report(new_report):
            # Reset picked location & form state
            st.session_state.pop("sentinel_picked_lat", None)
            st.session_state.pop("sentinel_picked_lng", None)
            st.session_state.pop("sentinel_jnc_input", None)
            st.session_state.pop("sentinel_select_junction_dropdown", None)

            st.session_state["sentinel_submitted_msg"] = f"🎉 **Report for '{final_jnc_name}' successfully submitted!** Map location and form inputs reset for next report."
            st.rerun()

# Feed Section
st.markdown("---")
st.markdown("### 🗂️ Recent Citizen Reports")

all_reports = load_reports()

if not all_reports:
    st.info("No citizen reports have been filed yet.")
else:
    # Filter dropdown
    feed_filter = st.selectbox("Filter Feed by Junction", options=["All Junctions"] + junction_names)
    
    # Apply filter
    filtered_reports = all_reports
    if feed_filter != "All Junctions":
        filtered_reports = [r for r in all_reports if r.get("junction_name") == feed_filter]
        
    if not filtered_reports:
        st.info("No reports found for this junction.")
    else:
        # Display reports (newest first)
        for report in reversed(filtered_reports):
            st.markdown(f"""
            <div class="report-card">
                <div class="report-header">
                    <div>📍 <span class="report-junction">{report.get('junction_name')}</span>
                        <span style="color:#475569; font-size:0.75rem;"> (ID: {report.get('junction_id')})</span></div>
                    <div class="report-timestamp">📅 {report.get('timestamp')}</div>
                </div>
                <div class="report-reporter">
                    <span style="color:#94a3b8; font-size: 0.8rem;">Reporter:</span>
                    <strong>{report.get('reporter_name')}</strong>
                </div>
                <div class="report-description">
                    {report.get('description')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show media inline if available
            rel_path = report.get("media_relative_path")
            media_url = report.get("media_url")

            if media_url:
                ext = os.path.splitext(media_url.split('?')[0])[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".webm"]:
                    st.video(media_url)
                else:
                    st.image(media_url, caption=f"Evidence (Supabase Cloud Storage): {report.get('media_filename', '')}", use_container_width=True)
            elif rel_path:
                full_media_path = os.path.join(PROJECT_ROOT, rel_path)
                if os.path.exists(full_media_path):
                    ext = os.path.splitext(rel_path)[1].lower()
                    if ext in [".jpg", ".png", ".jpeg"]:
                        st.image(full_media_path, caption=f"Evidence: {report.get('media_filename')}", use_container_width=True)
                    elif ext in [".mp4", ".mov", ".avi", ".webm"]:
                        st.video(full_media_path)
                    else:
                        st.write(f"📁 Evidence File: {report.get('media_filename')}")
                else:
                    st.warning("Evidence file not found on disk.")
                    
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ── Modern Branded Cyber Footer ──
st.markdown("""
<div class="cyber-footer">
    <div class="footer-left">
        <div class="footer-logo">📣 Citizen Hazard Sentinel • JunctionGuard AI</div>
        <div class="footer-copy">Crowdsourced Infrastructure Hazards &amp; Vision AI Feedback Loop</div>
    </div>
    <div class="footer-center">
        <span class="footer-tag">Public Sentinel</span>
        <span class="footer-tag">Instant Sync</span>
        <span class="footer-tag">Verified Dispatch</span>
    </div>
    <div class="footer-right">
        <div class="footer-uptime">● 99.98% System Uptime</div>
        <div class="footer-version">v2.4.0 • Public Edition</div>
    </div>
</div>
""", unsafe_allow_html=True)
