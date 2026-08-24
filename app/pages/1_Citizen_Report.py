import streamlit as st
import os
import sys
import json
import uuid
from datetime import datetime

# Add the 'app' directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_junctions

# Page Config
st.set_page_config(
    page_title="Citizen Safety Reporting | JunctionGuard AI",
    page_icon="📣",
    layout="wide"
)

# Custom Style Injection
st.markdown("""
<style>
    .report-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .report-header {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #475569;
        padding-bottom: 0.5rem;
        margin-bottom: 0.75rem;
        font-size: 0.9rem;
        color: #94a3b8;
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

# Header
st.title("📣 Citizen Safety Reporting Portal")
st.markdown("""
Use this form to report hazard situations, traffic violations, or infrastructure issues directly at junctions. 
Submissions are saved locally and used to compute junction safety rankings.
""")

# Load the placeholder junctions
junctions = load_junctions()
junction_names = [j.name for j in junctions]

# Create form
st.markdown("### File a Safety Report")
with st.form("citizen_report_form", clear_on_submit=True):
    col_j, col_n = st.columns(2)
    with col_j:
        selected_junction_name = st.selectbox("Select Junction", options=junction_names)
    with col_n:
        reporter_name = st.text_input("Your Name (Optional)", placeholder="Anonymous")
        
    description = st.text_area("Hazard Description (Required)", placeholder="Describe the hazard, issue or accident hazard in detail...")
    
    uploaded_file = st.file_uploader(
        "Upload Photo or Video Evidence (Optional)", 
        type=["jpg", "png", "jpeg", "mp4", "mov", "avi", "webm"]
    )
    
    submit_button = st.form_submit_button("Submit Safety Report")

# Handle Submission
if submit_button:
    if not description.strip():
        st.error("Please provide a description of the safety hazard.")
    else:
        # Resolve selected junction ID
        selected_j = next(j for j in junctions if j.name == selected_junction_name)
        
        # Save media file
        saved_filename = None
        saved_relative_path = None
        
        if uploaded_file is not None:
            file_ext = os.path.splitext(uploaded_file.name)[1]
            saved_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
            media_dest = os.path.join(REPORTS_DIR, saved_filename)
            
            try:
                with open(media_dest, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                # Use a path relative to project root so Streamlit app can reference it easily
                saved_relative_path = os.path.join("data", "citizen_reports", saved_filename)
            except Exception as e:
                st.error(f"Failed to save media upload: {e}")
        
        # Create report record
        new_report = {
            "report_id": uuid.uuid4().hex,
            "junction_id": selected_j.junction_id,
            "junction_name": selected_j.name,
            "reporter_name": reporter_name.strip() if reporter_name.strip() else "Anonymous",
            "description": description.strip(),
            "media_filename": saved_filename,
            "media_relative_path": saved_relative_path,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if save_report(new_report):
            st.success(f"Report for **{selected_j.name}** successfully submitted!")
            st.balloons()

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
                    <div>📍 <strong>{report.get('junction_name')}</strong> (ID: {report.get('junction_id')})</div>
                    <div>📅 {report.get('timestamp')}</div>
                </div>
                <div style="font-size: 0.95rem; margin-bottom: 0.8rem; color: #f8fafc;">
                    <strong>Reporter:</strong> {report.get('reporter_name')}
                </div>
                <div style="font-size: 0.9rem; line-height: 1.5; color: #cbd5e1; margin-bottom: 1rem;">
                    {report.get('description')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show media inline if available
            rel_path = report.get("media_relative_path")
            if rel_path:
                # Streamlit runs from project root, so rel_path is valid from execution context
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
                    
            st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
