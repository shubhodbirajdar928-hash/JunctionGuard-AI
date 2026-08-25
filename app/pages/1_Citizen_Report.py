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

# ── Branded Page Header ──
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(10, 14, 26, 0.95) 100%);
            border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 16px; padding: 24px 28px;
            position: relative; overflow: hidden;">
    <div style="position: absolute; top: 12px; right: 16px;
                background: rgba(245, 158, 11, 0.15); color: #fbbf24; padding: 3px 12px;
                border-radius: 9999px; font-size: 0.65rem; font-weight: 700;
                border: 1px solid rgba(245, 158, 11, 0.25); letter-spacing: 0.08em;">
        PUBLIC PORTAL
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 2.2rem;">📣</span>
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800;
                        background: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        background-clip: text;">
                Citizen Safety Reporting Portal
            </h1>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.9rem; font-weight: 400;">
                Report hazard situations, traffic violations, or infrastructure issues directly at junctions.
                Submissions are saved locally and used to compute junction safety rankings.
            </p>
        </div>
    </div>
</div>
<div class="gradient-separator"></div>
""", unsafe_allow_html=True)

# Load the placeholder junctions
junctions = load_junctions()
junction_names = [j.name for j in junctions]

# Create form
st.markdown("### 📝 File a Safety Report")
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
    
    submit_button = st.form_submit_button("🚨 Submit Safety Report")

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
                    
            st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ── Professional Footer ──
st.markdown("""
<div class="app-footer">
    <div class="footer-brand">🚨 JunctionGuard AI • Citizen Safety Reporting Portal</div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span class="footer-version">v1.0.0</span>
        <span style="font-size: 0.7rem; color: #475569;">OMNIKON Hackathon</span>
    </div>
</div>
""", unsafe_allow_html=True)
