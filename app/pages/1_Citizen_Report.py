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
from components import inject_custom_styles, render_navbar, render_footer

import folium
import importlib
import src.geo_utils
importlib.reload(src.geo_utils)
from src.geo_utils import find_nearest_junction, reverse_geocode_location, get_ip_location, forward_geocode_location
import streamlit.components.v1 as components
from streamlit_folium import st_folium

# ── Handle Browser GPS Callback (from HTML5 Geolocation Button) ──
if "geo_lat" in st.query_params and "geo_lng" in st.query_params:
    try:
        g_lat = float(st.query_params["geo_lat"])
        g_lng = float(st.query_params["geo_lng"])
        st.session_state["sentinel_picked_lat"] = g_lat
        st.session_state["sentinel_picked_lng"] = g_lng
        _jnc_list = load_junctions()
        near_j, _ = find_nearest_junction(g_lat, g_lng, _jnc_list)
        addr = near_j.name if near_j else reverse_geocode_location(g_lat, g_lng)
        st.session_state["sentinel_jnc_input"] = addr
        st.session_state["sentinel_select_junction_dropdown"] = addr
        st.query_params.clear()
        st.rerun()
    except Exception as ex:
        print(f"[Query Geolocation Handle Note] {ex}")
def get_safety_recommendation(issue_type: str) -> str:
    """Derives actionable safety recommendations based on reported hazard type."""
    issue_lower = (issue_type or "").lower()
    if "pothole" in issue_lower or "damaged" in issue_lower:
        return "🚧 Action: Priority Road Surface Patching & High-Vis Warning Banners"
    elif "signal" in issue_lower or "light" in issue_lower:
        return "🚦 Action: Emergency Signal Calibration & Traffic Officer Deployment"
    elif "blind spot" in issue_lower or "obstructed" in issue_lower:
        return "👁️ Action: Install Convex Mirror & Prune Sightline Vegetation"
    elif "speeding" in issue_lower or "u-turn" in issue_lower:
        return "🚘 Action: Speed Breaker Installation & Automated CCTV Enforcement"
    elif "pedestrian" in issue_lower or "crossing" in issue_lower:
        return "🚶 Action: Raised Refuge Island & High-Contrast Crossing Markings"
    else:
        return "🛡️ Action: Rapid Civic Safety Patrol & Site Inspection"

# Page Config
st.set_page_config(
    page_title="Citizen Safety Reporting | JunctionGuard AI",
    page_icon="📣",
    layout="wide"
)

# ── Inject Stitch Tactical Vision Interface Design System ──
inject_custom_styles()



# Define directories
# The script is in app/pages/1_Citizen_Report.py, project root is two levels up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "data", "citizen_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
def load_reports():
    """Fetches reports from unified SQLite/Supabase database with local json fallback."""
    try:
        from src.database import fetch_citizen_reports
        from data_loader import load_junctions as _lj
        db_reports = fetch_citizen_reports()
        if db_reports:
            _jmap = {j.junction_id: j.name for j in _lj()}
            for r in db_reports:
                if not r.get("junction_name"):
                    r["junction_name"] = _jmap.get(r.get("junction_id"), r.get("junction_id", "Custom Location"))
            return db_reports
    except Exception as e:
        print(f"[Load Reports DB Note] {e}")

    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_report(report_data):
    reports = []
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r") as f:
                reports = json.load(f)
        except Exception:
            reports = []
    reports.append(report_data)
    try:
        with open(INDEX_FILE, "w") as f:
            json.dump(reports, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save report: {e}")
        return False

# ── Top Tactical Navigation Bar ──
render_navbar("Reports")

# Load the placeholder junctions
junctions = load_junctions()
junction_names = [j.name for j in junctions]

st.markdown("### 📝 File a Safety Report")

if "sentinel_submitted_msg" in st.session_state:
    st.success(st.session_state.pop("sentinel_submitted_msg"))
    st.balloons()

col_map, col_form = st.columns([1, 1])

@st.fragment
def render_map_picker():
    # 🔍 Quick Search Location Bar
    search_c1, search_c2 = st.columns([3, 1])
    with search_c1:
        search_query = st.text_input(
            "Search location",
            placeholder="🔍 Search area, road, or city (e.g. Kolhapur, Koge, MG Road...)",
            label_visibility="collapsed",
            key="sentinel_map_search_txt"
        )
    with search_c2:
        if st.button("🔍 Find", key="sentinel_map_search_btn", use_container_width=True):
            if search_query and search_query.strip():
                with st.spinner("Searching..."):
                    found = forward_geocode_location(search_query.strip())
                if found:
                    f_lat, f_lon, f_name = found
                    st.session_state["sentinel_picked_lat"] = f_lat
                    st.session_state["sentinel_picked_lng"] = f_lon
                    st.session_state["sentinel_jnc_input"] = f_name
                    st.session_state["sentinel_select_junction_dropdown"] = f_name
                    st.rerun(scope="app")
                else:
                    st.warning("Location not found. Try a nearby landmark or city.")

    default_lat = junctions[0].lat if junctions else 12.9716
    default_lon = junctions[0].lon if junctions else 77.5946

    m_picker = folium.Map(location=[default_lat, default_lon], zoom_start=13, tiles="OpenStreetMap")

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
    </style>
    """
    m_picker.get_root().html.add_child(folium.Element(map_inner_css))

    for jnc in junctions:
        folium.Marker(
            [jnc.lat, jnc.lon],
            popup=jnc.name,
            tooltip=f"Junction: {jnc.name}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m_picker)

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

    # returned_objects=["last_clicked"] + return_on_hover=False: only reacts to clicks, never to hover
    map_data = st_folium(
        m_picker,
        use_container_width=True,
        height=380,
        key="citizen_sentinel_map_picker",
        returned_objects=["last_clicked"],
        return_on_hover=False
    )

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
            # Full page rerun so col_form picks up the new location value
            st.rerun(scope="app")

    # ── Status bar: shows detected name, coordinates, and Reset button ──
    if "sentinel_picked_lat" in st.session_state and "sentinel_picked_lng" in st.session_state:
        click_lat = st.session_state["sentinel_picked_lat"]
        click_lng = st.session_state["sentinel_picked_lng"]
        near_jnc, dist_km = find_nearest_junction(click_lat, click_lng, junctions, threshold_km=1.0)
        if near_jnc:
            st.success(f"✅ **Junction Auto-Detected**: {near_jnc.name} ({round(dist_km*1000)}m away)")
        else:
            addr = reverse_geocode_location(click_lat, click_lng)
            st.success(f"📍 **Pinpoint Auto-Detected**: {addr}")

        st.markdown(
            f'<div style="margin-top:4px; font-size:0.76rem; color:#64748b; font-family:monospace;">'
            f'🌐 Lat: <code style="color:#a5b4fc">{click_lat:.6f}</code>&nbsp;&nbsp;'
            f'Lng: <code style="color:#a5b4fc">{click_lng:.6f}</code></div>',
            unsafe_allow_html=True
        )

        if st.button("🗑️ Reset Location", key="sentinel_reset_loc_btn", use_container_width=True):
            for k in ["sentinel_picked_lat", "sentinel_picked_lng",
                      "sentinel_jnc_input", "sentinel_select_junction_dropdown"]:
                st.session_state.pop(k, None)
            st.rerun()
    else:
        st.caption("🖱️ Click anywhere on the map to drop a hazard pin.")

    # ── Live Device Hardware GPS ──
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
        font-size: 0.9rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35);
        transition: all 0.2s ease;
    }
    .btn-gps:hover { opacity: 0.92; }
    #msg { margin-top: 6px; font-size: 0.78rem; color: #cbd5e1; text-align: center; line-height: 1.35; }
    </style>
    </head>
    <body>
    <button class="btn-gps" id="locate-btn" onclick="getExactLocation()">
        🎯 Get My Exact Device GPS Location
    </button>
    <div id="msg"></div>
    <script>
    function getExactLocation() {
        var btn = document.getElementById("locate-btn");
        var msg = document.getElementById("msg");
        btn.disabled = true;
        btn.style.opacity = "0.7";
        msg.innerHTML = "<span style='color:#38bdf8;'>⏳ Requesting live GPS... Please click <b>Allow</b> when prompted.</span>";

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
                    var pUrl = new URL(window.parent.location.href);
                    pUrl.searchParams.set("geo_lat", lat);
                    pUrl.searchParams.set("geo_lng", lng);
                    window.parent.location.href = pUrl.href;
                }, 200);
            },
            function(err) {
                btn.disabled = false;
                btn.style.opacity = "1.0";
                if (err.code === 1) {
                    msg.innerHTML = "<span style='color:#f87171;'>❌ <b>Permission Denied</b>: Click location/lock icon in Safari/Chrome URL bar and click <b>Allow</b>.</span>";
                } else if (err.code === 2) {
                    msg.innerHTML = "<span style='color:#fbbf24;'>⚠️ <b>Mac Wi-Fi required</b>: Ensure <b>Wi-Fi is ON</b> & Location Services is ON in <i>System Settings → Privacy & Security → Location Services</i>.</span>";
                } else {
                    msg.innerHTML = "<span style='color:#fbbf24;'>⚠️ Request timed out. Ensure Wi-Fi is enabled on your Mac and retry.</span>";
                }
            },
            { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
        );
    }
    </script>
    </body>
    </html>
    """
    components.html(gps_html, height=84)

    # ── Quick City Jump Presets ──
    st.markdown("<div style='font-size:0.8rem; font-weight:600; color:#94a3b8; margin-top:6px; margin-bottom:6px;'>⚡ Quick Jump to City:</div>", unsafe_allow_html=True)
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        if st.button("📍 Kolhapur", key="sentinel_quick_kolhapur", use_container_width=True):
            st.session_state["sentinel_picked_lat"] = 16.7050
            st.session_state["sentinel_picked_lng"] = 74.2433
            st.session_state["sentinel_jnc_input"] = "Kolhapur, Maharashtra"
            st.session_state["sentinel_select_junction_dropdown"] = "Kolhapur, Maharashtra"
            st.rerun()
    with q_col2:
        if st.button("📍 Bangalore", key="sentinel_quick_blr", use_container_width=True):
            st.session_state["sentinel_picked_lat"] = 12.9716
            st.session_state["sentinel_picked_lng"] = 77.5946
            st.session_state["sentinel_jnc_input"] = "Bangalore, Karnataka"
            st.session_state["sentinel_select_junction_dropdown"] = "Bangalore, Karnataka"
            st.rerun()
    with q_col3:
        if st.button("📍 Pune", key="sentinel_quick_pune", use_container_width=True):
            st.session_state["sentinel_picked_lat"] = 18.5204
            st.session_state["sentinel_picked_lng"] = 73.8567
            st.session_state["sentinel_jnc_input"] = "Pune, Maharashtra"
            st.session_state["sentinel_select_junction_dropdown"] = "Pune, Maharashtra"
            st.rerun()
    with q_col4:
        if st.button("📍 Mumbai", key="sentinel_quick_mum", use_container_width=True):
            st.session_state["sentinel_picked_lat"] = 19.0760
            st.session_state["sentinel_picked_lng"] = 72.8777
            st.session_state["sentinel_jnc_input"] = "Mumbai, Maharashtra"
            st.session_state["sentinel_select_junction_dropdown"] = "Mumbai, Maharashtra"
            st.rerun()

with col_map:
    st.markdown("##### 📍 Pinpoint Location on Map")
    st.caption("Search area, click map, or use 🎯 Device GPS button to pinpoint hazard spot.")
    render_map_picker()


with col_form:
    st.markdown("##### 🚨 Hazard Details & Evidence")

    # ── Reset-form callback: clears map pin + all form fields ──
    def _reset_full_form():
        for k in [
            "sentinel_picked_lat", "sentinel_picked_lng",
            "sentinel_jnc_input", "sentinel_select_junction_dropdown",
            "sentinel_reporter_name", "sentinel_description",
            "sentinel_severity", "sentinel_custom_loc_input",
            "sentinel_custom_issue", "sentinel_issue_select",
            "_form_junction_name",
        ]:
            st.session_state.pop(k, None)

    # ── Build dynamic location dropdown ──
    current_loc = st.session_state.get("sentinel_jnc_input", "")
    loc_options = []
    if current_loc and current_loc not in junction_names:
        loc_options.append(current_loc)
    for jname in junction_names:
        if jname not in loc_options:
            loc_options.append(jname)
    loc_options.append("➕ Type Custom Location Manually...")

    stored_sel = st.session_state.get("sentinel_select_junction_dropdown", "")
    # Ensure detected location from map click is actively synced to dropdown (Bug 2 Fix)
    if current_loc and current_loc in loc_options:
        st.session_state["sentinel_select_junction_dropdown"] = current_loc
        idx = loc_options.index(current_loc)
    elif stored_sel and stored_sel in loc_options:
        idx = loc_options.index(stored_sel)
    else:
        idx = 0

    selected_option = st.selectbox(
        "Select Junction / Location ✱",
        options=loc_options,
        index=idx,
        key="sentinel_select_junction_dropdown"
    )

    if selected_option == "➕ Type Custom Location Manually...":
        typed_loc = st.text_input(
            "Enter Custom Location ✱",
            placeholder="e.g. MG Road & Brigade Junction, Bangalore",
            key="sentinel_custom_loc_input"
        )
        st.session_state["_form_junction_name"] = typed_loc
    else:
        st.session_state["_form_junction_name"] = selected_option
        st.session_state["sentinel_jnc_input"] = selected_option

    st.text_input(
        "Your Name (Optional)",
        placeholder="e.g. Anonymous / Traffic Police",
        key="sentinel_reporter_name"
    )

    st.selectbox("Issue Category", options=ISSUE_OPTIONS, key="sentinel_issue_select")

    if st.session_state.get("sentinel_issue_select") == "Other (Specify below)":
        st.text_input(
            "Specify Custom Issue Category ✱",
            placeholder="e.g. Waterlogging, Broken Street Lamp, Construction Debris...",
            key="sentinel_custom_issue"
        )

    st.slider(
        "Hazard Severity Level (1 = Low, 5 = Critical)",
        min_value=1, max_value=5,
        value=st.session_state.get("sentinel_severity", 3),
        key="sentinel_severity"
    )

    st.text_area(
        "Detailed Description (Optional)",
        placeholder="Describe exact hazard location, traffic disruption, or vehicle conflicts...",
        key="sentinel_description"
    )

    st.file_uploader(
        "Upload Photo or Video Evidence (Optional)",
        type=["jpg", "png", "jpeg", "mp4", "mov", "avi", "webm"],
        key="sentinel_uploaded_file"
    )

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        if st.button("🚨 Submit Safety Report", use_container_width=True, type="primary", key="sentinel_submit_btn"):
            st.session_state["_form_submit_requested"] = True
            st.rerun()
    with btn_col2:
        st.button("🔄 Reset", use_container_width=True, on_click=_reset_full_form, key="sentinel_reset_form_btn")

# ── Submission Handler (reads everything from session state) ──
if st.session_state.pop("_form_submit_requested", False):
    selected_junction_name = st.session_state.get("_form_junction_name", "")
    selected_issue         = st.session_state.get("sentinel_issue_select", ISSUE_OPTIONS[0])
    custom_issue_type      = st.session_state.get("sentinel_custom_issue", "").strip()
    rep_severity           = st.session_state.get("sentinel_severity", 3)
    description            = st.session_state.get("sentinel_description", "").strip()
    reporter_name          = st.session_state.get("sentinel_reporter_name", "").strip()
    uploaded_file          = st.session_state.get("sentinel_uploaded_file", None)

    if not selected_junction_name.strip():
        st.error("⚠️ Please select or enter a junction location before submitting.")
    elif selected_issue == "Other (Specify below)" and not custom_issue_type:
        st.error("⚠️ Please specify the custom issue category.")
    else:
        final_jnc_name = selected_junction_name.strip()
        final_desc     = description if description else f"Safety hazard reported at {final_jnc_name}."
        selected_j     = next((j for j in junctions if j.name == final_jnc_name), None)
        final_jnc_id   = selected_j.junction_id if selected_j else f"J-CUSTOM-{uuid.uuid4().hex[:6].upper()}"
        final_issue    = custom_issue_type if selected_issue == "Other (Specify below)" else selected_issue

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
                guessed_mime = mimetypes.guess_type(uploaded_file.name)[0]
                if not guessed_mime:
                    guessed_mime = "video/mp4" if file_ext in [".mp4", ".mov", ".avi", ".webm"] else "image/jpeg"
                from src.supabase_client import upload_citizen_media_supabase
                media_url = upload_citizen_media_supabase(file_bytes, saved_filename, content_type=guessed_mime)
            except Exception as e:
                st.error(f"Failed to process media file: {e}")

        new_report = {
            "report_id": uuid.uuid4().hex,
            "junction_id": final_jnc_id,
            "junction_name": final_jnc_name,
            "reporter_name": reporter_name if reporter_name else "Anonymous",
            "issue_type": final_issue,
            "severity": rep_severity,
            "description": final_desc,
            "media_filename": saved_filename,
            "media_relative_path": saved_relative_path,
            "media_url": media_url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        media_type_val = None
        if uploaded_file is not None:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            media_type_val = "video" if file_ext in [".mp4", ".mov", ".avi", ".webm"] else "photo"

        try:
            from src.database import add_citizen_report
            add_citizen_report(
                junction_id=final_jnc_id,
                reporter=new_report["reporter_name"],
                issue=final_issue,
                severity=rep_severity,
                description=final_desc,
                media_filename=saved_filename,
                media_relative_path=saved_relative_path,
                media_url=media_url,
                media_type=media_type_val
            )
        except Exception as ex:
            print(f"[Database Sync Note] {ex}")

        try:
            from src.analytics.risk_engine import ExplainableRiskEngine
            risk_engine = ExplainableRiskEngine()
            if final_jnc_id:
                risk_engine.compute_junction_risk(final_jnc_id)
        except Exception as rx:
            print(f"[Risk Engine Compute Note] {rx}")

        if save_report(new_report):
            for k in [
                "sentinel_picked_lat", "sentinel_picked_lng",
                "sentinel_jnc_input", "sentinel_select_junction_dropdown",
                "sentinel_reporter_name", "sentinel_description",
                "sentinel_severity", "sentinel_custom_loc_input",
                "sentinel_custom_issue", "sentinel_issue_select",
                "sentinel_uploaded_file", "_form_junction_name", "_form_junction_is_custom",
            ]:
                st.session_state.pop(k, None)
            st.session_state["sentinel_submitted_msg"] = f"🎉 **Report for '{final_jnc_name}' successfully submitted!**"
            st.rerun()

# Feed Section
st.markdown("---")
st.markdown("### 🗂️ Recent Citizen Reports & Safety Intelligence Feed")

all_reports = load_reports()

if not all_reports:
    st.info("No citizen reports have been filed yet.")
else:
    f_col1, f_col2, f_col3 = st.columns([1, 1, 1])
    with f_col1:
        feed_filter = st.selectbox("Filter by Junction", options=["All Junctions"] + junction_names)
    with f_col2:
        cat_filter = st.selectbox("Filter by Category", options=["All Categories"] + ISSUE_OPTIONS)
    with f_col3:
        sev_filter = st.selectbox("Filter by Risk Level", options=["All Levels", "🔴 High Risk", "🟡 Medium Risk", "🟢 Low Risk"])
    
    # Apply multi-criteria filtering
    filtered_reports = all_reports
    if feed_filter != "All Junctions":
        filtered_reports = [r for r in filtered_reports if r.get("junction_name") == feed_filter]
    if cat_filter != "All Categories":
        filtered_reports = [r for r in filtered_reports if r.get("issue_type") == cat_filter]
    if sev_filter != "All Levels":
        if "High" in sev_filter:
            filtered_reports = [r for r in filtered_reports if r.get("severity", 3) >= 4]
        elif "Medium" in sev_filter:
            filtered_reports = [r for r in filtered_reports if r.get("severity", 3) == 3]
        elif "Low" in sev_filter:
            filtered_reports = [r for r in filtered_reports if r.get("severity", 3) <= 2]
        
    if not filtered_reports:
        st.info("No reports found matching the active filter criteria.")
    else:
        # Display reports (newest first)
        for report in reversed(filtered_reports):
            issue_name = report.get("issue_type", "Hazard")
            rec_action = get_safety_recommendation(issue_name)
            m_url = report.get("media_url")
            m_rel = report.get("media_relative_path")
            sev_val = report.get("severity", 3)
            
            if sev_val >= 4:
                sev_tag = f'<span style="color:#ef4444; font-weight:700; font-size:0.8rem; background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.3); padding:2px 8px; border-radius:9999px;">🔴 Severity: {sev_val}/5</span>'
            elif sev_val == 3:
                sev_tag = f'<span style="color:#f59e0b; font-weight:700; font-size:0.8rem; background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.3); padding:2px 8px; border-radius:9999px;">🟡 Severity: {sev_val}/5</span>'
            else:
                sev_tag = f'<span style="color:#10b981; font-weight:700; font-size:0.8rem; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:9999px;">🟢 Severity: {sev_val}/5</span>'

            cloud_badge = '<span style="font-size:0.72rem; background:rgba(6,182,212,0.15); color:#38bdf8; border:1px solid rgba(6,182,212,0.3); padding:2px 8px; border-radius:9999px; font-weight:600;">☁️ Supabase Cloud Synced</span>' if m_url else '<span style="font-size:0.72rem; background:rgba(148,163,184,0.15); color:#94a3b8; border:1px solid rgba(148,163,184,0.3); padding:2px 8px; border-radius:9999px; font-weight:600;">📁 Local Storage</span>'

            st.markdown(f"""
            <div class="report-card">
                <div class="report-header">
                    <div>📍 <span class="report-junction">{report.get('junction_name')}</span>
                        <span style="color:#475569; font-size:0.75rem;"> (ID: {report.get('junction_id')})</span> {cloud_badge}</div>
                    <div class="report-timestamp">📅 {report.get('timestamp')}</div>
                </div>
                <div class="report-reporter">
                    <span style="color:#94a3b8; font-size: 0.8rem;">Reporter:</span>
                    <strong>{report.get('reporter_name')}</strong> | <span style="color:#f59e0b; font-weight:600;">Category: {issue_name}</span> | {sev_tag}
                </div>
                <div class="report-description" style="margin-top: 6px;">
                    {report.get('description')}
                </div>
                <div style="margin-top: 10px; padding: 6px 12px; background: rgba(99, 102, 241, 0.12); border-left: 3px solid #6366f1; border-radius: 4px; font-size: 0.82rem; color: #a5b4fc; font-weight: 600;">
                    {rec_action}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show media inline if available
            if m_url:
                ext = os.path.splitext(m_url.split('?')[0])[1].lower()
                if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                    st.caption("📹 Video Evidence (Supabase Cloud Storage)")
                    st.video(m_url)
                else:
                    st.image(m_url, caption=f"Photo Evidence (Supabase Cloud Storage): {report.get('media_filename', '')}", use_container_width=True)
            elif m_rel:
                full_media_path = os.path.join(PROJECT_ROOT, m_rel)
                if os.path.exists(full_media_path):
                    ext = os.path.splitext(m_rel)[1].lower()
                    if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
                        st.caption("📹 Video Evidence (Local Storage)")
                        st.video(full_media_path)
                    else:
                        st.image(full_media_path, caption=f"Photo Evidence (Local): {report.get('media_filename')}", use_container_width=True)
                else:
                    st.warning("Local evidence file path registered but file not found on disk.")
                    
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ── Tactical Telemetry Footer ──
render_footer()
