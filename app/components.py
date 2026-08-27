"""
UI Components and Design System for JunctionGuard AI.
Implements the Stitch Tactical Vision Interface (Ultra-Dark Command Center):
  - Deep charcoal #0a0c0e canvas with subtle 24px tactical grid
  - Glowing safety amber (#f97316) brand, active states, and telemetry
  - Top HUD navigation bar with operational status, AI inference FPS, and node telemetry
  - Dashboard Overview subheader with live timestamp and deploy pill
  - Tactically styled KPI metric cards with status pulses
  - Color-coded risk badges & animated radar halos
  - Explainable contributing factor progress bars
"""

import streamlit as st
from datetime import datetime
from typing import Optional, List, Dict, Any

def get_risk_badge_html(risk_level: Optional[str]) -> str:
    """Returns the HTML string for a colored risk badge."""
    if risk_level is None:
        return '<span class="badge badge-gray"><span class="badge-dot"></span>AWAITING DATA</span>'
    
    lvl = risk_level.upper()
    if lvl == "LOW":
        return '<span class="badge badge-green"><span class="badge-dot"></span>LOW RISK</span>'
    elif lvl == "MEDIUM":
        return '<span class="badge badge-amber"><span class="badge-dot"></span>MEDIUM RISK</span>'
    elif lvl == "HIGH":
        return '<span class="badge badge-red"><span class="badge-dot"></span>HIGH RISK</span>'
    else:
        return f'<span class="badge badge-amber"><span class="badge-dot"></span>{lvl}</span>'

def render_risk_badge(risk_level: Optional[str]):
    """Renders the risk badge inline in Streamlit."""
    st.markdown(get_risk_badge_html(risk_level), unsafe_allow_html=True)

def render_contributing_factors(factors: Optional[List[Dict[str, Any]]], junction_id: Optional[str] = None):
    """Renders contributing factors as labeled progress bars with glowing tactical styling."""
    if not factors:
        render_awaiting_data_banner()
        return
        
    st.markdown('<div class="factors-section">', unsafe_allow_html=True)

    # When "Citizen Reports" is the top contributing factor, show context sub-line
    if len(factors) > 0 and factors[0].get("factor") in ["Citizen Reports", "Citizen Hazard Reports"]:
        sub_line = None
        if junction_id:
            try:
                from src.analytics.risk_engine import get_citizen_cluster_stats
                cluster_stats = get_citizen_cluster_stats(junction_id)
                sub_line = cluster_stats.get("summary_line")
            except Exception:
                pass
        if not sub_line:
            sub_line = "Multiple reports in last 30 days driving citizen incident elevation"

        st.markdown(f"""
        <div style="background: rgba(249, 115, 22, 0.12); border-left: 3px solid #f97316; border-radius: 6px; padding: 8px 14px; margin-bottom: 14px; font-size: 0.82rem; color: #fdba74; display: flex; align-items: center; gap: 8px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span><b>Citizen Alert Cluster:</b> {sub_line}</span>
        </div>
        """, unsafe_allow_html=True)

    for factor_info in factors:
        factor = factor_info.get("factor", "Unknown Factor")
        weight = factor_info.get("weight", 0.0)
        weight_clamped = max(0.0, min(1.0, float(weight)))
        pct = int(weight_clamped * 100)
        
        # Determine bar color based on impact intensity
        if pct >= 35:
            bar_color = "linear-gradient(90deg, #ef4444, #dc2626)"
            text_accent = "#f87171"
        elif pct >= 20:
            bar_color = "linear-gradient(90deg, #f97316, #ea580c)"
            text_accent = "#fb923c"
        else:
            bar_color = "linear-gradient(90deg, #10b981, #059669)"
            text_accent = "#34d399"

        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span style="font-size: 0.88rem; font-weight: 600; color: #e2e8f0;">{factor}</span>
                <span style="font-size: 0.82rem; font-weight: 700; color: {text_accent}; font-family: 'JetBrains Mono', monospace;">
                    {pct}% Impact
                </span>
            </div>
            <div style="background: rgba(18, 20, 24, 0.9); height: 8px; border-radius: 9999px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.08);">
                <div style="width: {pct}%; height: 100%; background: {bar_color}; border-radius: 9999px; transition: width 0.6s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

def render_awaiting_data_banner():
    """Renders the 'Awaiting Data' info banner."""
    st.markdown("""
    <div class="awaiting-data-banner">
        <div class="awaiting-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>
        </div>
        <div>
            <div class="awaiting-title">AWAITING TELEMETRY DATA</div>
            <div class="awaiting-desc">
                Visual risk analysis and historical accident weighting are currently pending for this junction. 
                Detailed contributing factor scores will be populated automatically when live streams and database 
                connectors are active.
            </div>
        </div>
        <div class="radar-sweep"></div>
    </div>
    """, unsafe_allow_html=True)

def render_navbar(active_page: str = "Dashboard"):
    """Renders the ultra-dark tactical command center header matching the reference image."""
    navbar_html = (
        '<div class="tactical-navbar">'
        '<div class="navbar-brand-group">'
        '<div class="brand-shield-logo">'
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<circle cx="12" cy="12" r="2" fill="#f97316"/>'
        '<path d="M12 7v3m0 4v3m-5-5h3m4 0h3"/>'
        '</svg>'
        '</div>'
        '<div>'
        '<div class="brand-title">JunctionGuard <span class="brand-ai">AI</span></div>'
        '<div class="brand-sub">Autonomous Vision Analytics &amp; Road Hazard Intelligence</div>'
        '</div>'
        '</div>'
        '<div class="navbar-status-badges">'
        '<div class="status-pill status-pill-operational">'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
        '<div class="pill-meta">'
        '<span class="pill-label">SYSTEM STATUS</span>'
        '<span class="pill-val" style="color: #10b981;">OPERATIONAL</span>'
        '</div>'
        '</div>'
        '<div class="status-pill status-pill-inference">'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.5"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/></svg>'
        '<div class="pill-meta">'
        '<span class="pill-label">AI INFERENCE</span>'
        '<span class="pill-val" style="color: #f97316;">28 FPS</span>'
        '</div>'
        '</div>'
        '<div class="status-pill status-pill-uptime">'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
        '<div class="pill-meta">'
        '<span class="pill-label">UPTIME</span>'
        '<span class="pill-val" style="color: #10b981;">99.98%</span>'
        '</div>'
        '</div>'
        '<div class="status-pill status-pill-nodes">'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2.5"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>'
        '<div class="pill-meta">'
        '<span class="pill-label">MONITORED NODES</span>'
        '<span class="pill-val" style="color: #f97316;">12</span>'
        '</div>'
        '</div>'
        '</div>'
        '<div class="navbar-actions">'
        '<div class="action-icon-wrap" title="Notifications">'
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
        '<span class="notification-badge">3</span>'
        '</div>'
        '<div class="action-icon-wrap" title="Settings">'
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
        '</div>'
        '<div class="user-avatar" title="Commander Profile">'
        '<div class="avatar-inner"></div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.html(navbar_html)

def render_dashboard_overview_header(title: str = "Dashboard", subtitle: str = "Real-time Junction Risk Surveillance System"):
    """Renders the subheader bar with active page title, subtitle, and live date/time widget."""
    now = datetime.now()
    date_str = now.strftime("%b %d, %Y")
    time_str = now.strftime("%I:%M:%S %p")
    
    st.html(f"""
    <div class="overview-header-bar">
        <div>
            <div class="overview-title">{title}</div>
            <div class="overview-sub">{subtitle}</div>
        </div>
        <div class="overview-right-actions">
            <div class="datetime-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                <span>{date_str}</span>
                <span class="dt-divider">|</span>
                <span class="dt-time">{time_str}</span>
            </div>
            <div class="deploy-pill-btn">
                <span>Deploy</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
        </div>
    </div>
    """)

def render_footer():
    """Renders the bottom status bar matching the reference image."""
    st.html("""
    <div class="tactical-footer">
        <div class="footer-stat">
            <span class="live-dot-green"></span>
            <span>Data Source: Live Sensors + CCTV + IoT</span>
        </div>
        <div class="footer-stat">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>AI Model: <b>JunctionGuard v2.1</b></span>
        </div>
        <div class="footer-stat">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            <span>Data Refresh: <b>2 sec ago</b></span>
        </div>
        <div class="footer-stat footer-copyright">
            &copy; 2025 JunctionGuard AI. All Rights Reserved.
        </div>
    </div>
    """)

def inject_custom_styles():
    """Injects the Stitch Tactical Vision Interface design system."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700;800&display=swap');

        /* ── Ultra-Dark Canvas (#0a0c0e) with Subtle 24px Tactical Grid ── */
        html, body, [class*="css"], .stApp {
            font-family: 'Geist', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            background-color: #0a0c0e !important;
            background-image: 
                linear-gradient(rgba(249, 115, 22, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(249, 115, 22, 0.02) 1px, transparent 1px) !important;
            background-size: 24px 24px !important;
            color: #e2e2e5 !important;
        }

        /* ── Confident Technical Typography Hierarchy ── */
        h1, h2, h3, h4, h5, h6, .brand-title, .overview-title, .card-label, .panel-title {
            font-family: 'Space Grotesk', system-ui, sans-serif !important;
            letter-spacing: -0.02em !important;
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #f8fafc !important;
        }

        [data-testid="stAppViewContainer"] {
            background-color: #0a0c0e !important;
            background-image: 
                linear-gradient(rgba(249, 115, 22, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(249, 115, 22, 0.02) 1px, transparent 1px) !important;
            background-size: 24px 24px !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(10, 12, 14, 0.95) !important;
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        }

        /* ── Ultra-Dark Sidebar with Tactical Styling ── */
        [data-testid="stSidebar"] {
            background: #0d0f12 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.07);
        }
        div[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
            gap: 5px !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stRadio"] label {
            background: #12151a !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            padding: 9px 12px !important;
            color: #9ca3af !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            margin-bottom: 0px !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
            border-color: rgba(249, 115, 22, 0.4) !important;
            color: #ffffff !important;
            background: #161b22 !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
            background: rgba(249, 115, 22, 0.14) !important;
            border: 1px solid rgba(249, 115, 22, 0.5) !important;
            color: #ffedd5 !important;
            font-weight: 700 !important;
            box-shadow: 0 0 14px rgba(249, 115, 22, 0.18) !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        /* ── Tactical Panels & HUD Glass Containers ── */
        .tactical-panel,
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            background: #12151a !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 16px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
            position: relative !important;
            overflow: hidden !important;
            transition: all 0.2s ease !important;
        }
        .tactical-panel:hover,
        [data-testid="stVerticalBlockBorderWrapper"] > div:hover {
            border-color: rgba(249, 115, 22, 0.3) !important;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5) !important;
        }

        /* ── Top Tactical Navigation Bar ── */
        .tactical-navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0d0f12;
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 10px 20px;
            margin-bottom: 12px;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5);
        }
        .navbar-brand-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-shield-logo {
            width: 38px;
            height: 38px;
            background: rgba(249, 115, 22, 0.12);
            border: 1px solid rgba(249, 115, 22, 0.35);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 12px rgba(249, 115, 22, 0.2);
        }
        .brand-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
        }
        .brand-ai {
            color: #f97316;
            font-weight: 800;
        }
        .brand-sub {
            font-size: 0.72rem;
            color: #9ca3af;
            margin-top: 2px;
            font-weight: 500;
        }

        .navbar-status-badges {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #14171d;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 5px 12px;
        }
        .pill-meta {
            display: flex;
            flex-direction: column;
            line-height: 1.1;
        }
        .pill-label {
            font-size: 0.58rem;
            font-weight: 700;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-family: 'JetBrains Mono', monospace;
        }
        .pill-val {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            font-family: 'JetBrains Mono', monospace;
        }

        .navbar-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .action-icon-wrap {
            position: relative;
            width: 34px;
            height: 34px;
            border-radius: 8px;
            background: #14171d;
            border: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .action-icon-wrap:hover {
            border-color: rgba(249, 115, 22, 0.4);
            color: #f97316;
        }
        .notification-badge {
            position: absolute;
            top: -3px;
            right: -3px;
            background: #f97316;
            color: #0a0c0e;
            font-size: 0.60rem;
            font-weight: 800;
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'JetBrains Mono', monospace;
        }
        .user-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: #14171d;
            border: 2px solid #f97316;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }
        .avatar-inner {
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
        }

        /* ── Subheader Overview Bar ── */
        .overview-header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 12px 0 16px 0;
            padding-bottom: 4px;
        }
        .overview-title {
            font-size: 1.55rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
        }
        .overview-sub {
            font-size: 0.80rem;
            color: #9ca3af;
            margin-top: 3px;
        }
        .overview-right-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .datetime-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #12151a;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 0.76rem;
            font-family: 'JetBrains Mono', monospace;
            color: #d1d5db;
        }
        .dt-divider {
            color: #4b5563;
        }
        .dt-time {
            color: #f97316;
            font-weight: 700;
        }
        .deploy-pill-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #12151a;
            border: 1px solid #f97316;
            border-radius: 8px;
            padding: 7px 16px;
            font-size: 0.78rem;
            font-weight: 700;
            color: #f97316;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .deploy-pill-btn:hover {
            background: #f97316;
            color: #0a0c0e;
        }

        /* ── Top 4 KPI Cards Matching Reference Image ── */
        .kpi-tactical-card {
            background: #12151a;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 16px 18px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            transition: all 0.2s ease;
        }
        .kpi-tactical-card:hover {
            border-color: rgba(249, 115, 22, 0.4);
            transform: translateY(-1px);
        }
        .kpi-card-critical {
            border-color: rgba(239, 68, 68, 0.35) !important;
            background: linear-gradient(180deg, rgba(239, 68, 68, 0.06) 0%, #12151a 100%) !important;
        }
        .kpi-label {
            font-size: 0.68rem;
            font-weight: 700;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 4px;
        }
        .kpi-num {
            font-size: 1.95rem;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.1;
            font-family: 'Space Grotesk', sans-serif;
        }
        .kpi-denom {
            font-size: 0.85rem;
            color: #6b7280;
            font-weight: 500;
        }
        .kpi-sub {
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            font-family: 'JetBrains Mono', monospace;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .kpi-icon-wrap {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        /* ── Status Pulse Animations ── */
        .live-dot-green {
            width: 7px;
            height: 7px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10b981;
        }
        .live-dot-red {
            width: 7px;
            height: 7px;
            background: #ef4444;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #ef4444;
            animation: pulseCritical 1.8s infinite;
        }
        @keyframes pulseCritical {
            0%   { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70%  { transform: scale(1);    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        /* ── Navigation Tabs Command Deck ── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: #0d0f12 !important;
            padding: 6px 8px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
            margin-bottom: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 18px;
            font-family: 'Space Grotesk', system-ui, sans-serif;
            font-weight: 600;
            font-size: 0.86rem;
            color: #9ca3af;
            border: 1px solid transparent;
            background: transparent;
            transition: all 0.2s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.04);
        }
        .stTabs [aria-selected="true"] {
            background: rgba(249, 115, 22, 0.15) !important;
            color: #ffedd5 !important;
            border: 1px solid rgba(249, 115, 22, 0.5) !important;
            box-shadow: 0 0 14px rgba(249, 115, 22, 0.2) !important;
        }

        /* ── Map Container Anti-Flicker & Dark Mode Integration ── */
        iframe[title*="st_folium"], .stFolium iframe, [data-testid="stCustomComponentV1"], .stFolium {
            background-color: #0a0c0e !important;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
        }
        .leaflet-container, .leaflet-pane, .leaflet-tile-pane, .leaflet-tile {
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
            opacity: 1 !important;
        }
        .leaflet-tile-container img {
            filter: none !important;
            -webkit-filter: none !important;
            transition: none !important;
            opacity: 1 !important;
        }
        .leaflet-container:hover, .leaflet-tile:hover, .stFolium:hover, iframe:hover {
            filter: none !important;
            -webkit-filter: none !important;
            opacity: 1 !important;
        }

        /* ── Distinct Placeholder Styling ── */
        input::placeholder, textarea::placeholder,
        [data-baseweb="input"] input::placeholder,
        [data-baseweb="textarea"] textarea::placeholder,
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: rgba(156, 163, 175, 0.40) !important;
            -webkit-text-fill-color: rgba(156, 163, 175, 0.40) !important;
            font-style: italic !important;
            font-weight: 400 !important;
            font-size: 0.86rem !important;
            opacity: 1 !important;
        }

        /* ── Segmented Control Filter Chips with True Risk Colors ── */
        [data-baseweb="tag"] {
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            letter-spacing: 0.04em !important;
            padding: 4px 10px !important;
            transition: all 0.2s ease !important;
        }
        [data-baseweb="tag"]:has([title*="HIGH"]), [data-baseweb="tag"]:has(span:contains("HIGH")) {
            background: rgba(239, 68, 68, 0.20) !important;
            border: 1px solid rgba(239, 68, 68, 0.6) !important;
            color: #f87171 !important;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.2) !important;
        }
        [data-baseweb="tag"]:has([title*="HIGH"]) svg, [data-baseweb="tag"]:has(span:contains("HIGH")) svg {
            fill: #f87171 !important;
        }
        [data-baseweb="tag"]:has([title*="MEDIUM"]), [data-baseweb="tag"]:has(span:contains("MEDIUM")) {
            background: rgba(245, 158, 11, 0.20) !important;
            border: 1px solid rgba(245, 158, 11, 0.6) !important;
            color: #fbbf24 !important;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.2) !important;
        }
        [data-baseweb="tag"]:has([title*="MEDIUM"]) svg, [data-baseweb="tag"]:has(span:contains("MEDIUM")) svg {
            fill: #fbbf24 !important;
        }
        [data-baseweb="tag"]:has([title*="LOW"]), [data-baseweb="tag"]:has(span:contains("LOW")) {
            background: rgba(16, 185, 129, 0.20) !important;
            border: 1px solid rgba(16, 185, 129, 0.6) !important;
            color: #34d399 !important;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.2) !important;
        }
        [data-baseweb="tag"]:has([title*="LOW"]) svg, [data-baseweb="tag"]:has(span:contains("LOW")) svg {
            fill: #34d399 !important;
        }

        /* ── Reserved Risk Badges (LOW / MEDIUM / HIGH ONLY) ── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.74rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 0.05em;
        }
        .badge-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }
        .badge-green {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
        }
        .badge-amber {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }
        .badge-red {
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.45);
        }
        .badge-gray {
            background: rgba(100, 116, 139, 0.15);
            color: #94a3b8;
            border: 1px solid rgba(100, 116, 139, 0.3);
        }

        /* ── Tactical Action Buttons ── */
        .stButton > button {
            background: #14171d !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.86rem !important;
            padding: 8px 18px !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            background: #1e222a !important;
            border-color: #f97316 !important;
            color: #f97316 !important;
            transform: translateY(-1px) !important;
        }

        /* ── Tactical Footer ── */
        .tactical-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 20px;
            background: #0d0f12;
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 10px;
            margin-top: 2rem;
            font-size: 0.74rem;
            color: #9ca3af;
            flex-wrap: wrap;
            gap: 12px;
        }
        .footer-stat {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-family: 'JetBrains Mono', monospace;
        }
        .footer-copyright {
            color: #6b7280;
        }

        /* ── Custom Scrollbars ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0a0c0e; }
        ::-webkit-scrollbar-thumb { background: #1f242d; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #374151; }
    </style>
    """, unsafe_allow_html=True)
