"""
UI Components and Design System for JunctionGuard AI.
Provides reusable modern web components:
  - Glassmorphic top navigation bar & live telemetry ticker
  - Color-coded risk badges & animated radar halos
  - Explainable contributing factor progress bars
  - KPI metric cards with neon accents
  - Global CSS styling injection
"""

import streamlit as st
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
        return f'<span class="badge badge-indigo"><span class="badge-dot"></span>{lvl}</span>'

def render_risk_badge(risk_level: Optional[str]):
    """Renders the risk badge inline in Streamlit."""
    st.markdown(get_risk_badge_html(risk_level), unsafe_allow_html=True)

def render_contributing_factors(factors: Optional[List[Dict[str, Any]]]):
    """Renders contributing factors as labeled progress bars with glowing cyber styling."""
    if not factors:
        render_awaiting_data_banner()
        return
        
    st.markdown('<div class="factors-section">', unsafe_allow_html=True)
    for factor_info in factors:
        factor = factor_info.get("factor", "Unknown Factor")
        weight = factor_info.get("weight", 0.0)
        weight_clamped = max(0.0, min(1.0, float(weight)))
        pct = int(weight_clamped * 100)
        
        # Determine bar color based on impact intensity
        if pct >= 35:
            bar_color = "linear-gradient(90deg, #f87171, #ef4444)"
            text_accent = "#f87171"
        elif pct >= 20:
            bar_color = "linear-gradient(90deg, #fbbf24, #f59e0b)"
            text_accent = "#fbbf24"
        else:
            bar_color = "linear-gradient(90deg, #60a5fa, #3b82f6)"
            text_accent = "#60a5fa"

        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span style="font-size: 0.88rem; font-weight: 600; color: #e2e8f0;">{factor}</span>
                <span style="font-size: 0.82rem; font-weight: 700; color: {text_accent}; font-family: 'JetBrains Mono', monospace;">
                    {pct}% Impact
                </span>
            </div>
            <div style="background: rgba(30, 41, 59, 0.6); height: 8px; border-radius: 9999px; overflow: hidden; border: 1px solid rgba(51, 65, 85, 0.4);">
                <div style="width: {pct}%; height: 100%; background: {bar_color}; border-radius: 9999px; transition: width 0.6s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

def render_awaiting_data_banner():
    """Renders the 'Awaiting Data' info banner."""
    st.markdown("""
    <div class="awaiting-data-banner">
        <div class="awaiting-icon">📡</div>
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

def render_navbar(active_page: str = "Surveillance Hub"):
    """Renders a modern top navigation bar with system live telemetry ticker."""
    st.markdown(f"""
    <div class="cyber-navbar">
        <div class="navbar-brand">
            <div class="brand-radar">
                <span class="radar-icon">🚨</span>
                <span class="radar-ring"></span>
            </div>
            <div>
                <div class="brand-title">JunctionGuard <span class="brand-ai">AI</span></div>
                <div class="brand-sub">Civic Safety & Road Risk Intelligence Platform</div>
            </div>
        </div>
        <div class="navbar-status-group">
            <div class="status-chip chip-online">
                <span class="live-dot"></span>
                <span>SYSTEM LIVE</span>
            </div>
            <div class="status-chip chip-inference">
                <span>⚡ YOLOv8n ACTIVE</span>
            </div>
            <div class="status-chip chip-nodes">
                <span>🛰️ 12 MONITORED HUBS</span>
            </div>
        </div>
    </div>
    <div class="gradient-separator"></div>
    """, unsafe_allow_html=True)

def render_footer():
    """Renders a clean, branded modern website footer."""
    st.markdown("""
    <div class="cyber-footer">
        <div class="footer-left">
            <div class="footer-logo">🛡️ JunctionGuard AI</div>
            <div class="footer-copy">Autonomous Vision Analytics & Explainable Road Hazard Intelligence</div>
        </div>
        <div class="footer-center">
            <span class="footer-tag">Python 3.11</span>
            <span class="footer-tag">YOLOv8 Real-time</span>
            <span class="footer-tag">Explainable AI</span>
            <span class="footer-tag">Streamlit GIS</span>
        </div>
        <div class="footer-right">
            <div class="footer-uptime">● 99.98% System Uptime</div>
            <div class="footer-version">v2.4.0 • Enterprise Edition</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def inject_custom_styles():
    """Injects comprehensive CSS design system into the app page."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

        /* ── Global Dark Palette ── */
        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
            background: #070b14 !important;
            color: #f1f5f9 !important;
        }

        [data-testid="stAppViewContainer"] {
            background: #070b14 !important;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.06) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.05) 0px, transparent 50%) !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(7, 11, 20, 0.85) !important;
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1120 0%, #070b14 100%) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        /* ── Top Navigation Bar ── */
        .cyber-navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 8px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
        }
        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-radar {
            position: relative;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
        }
        .radar-icon {
            font-size: 1.4rem;
            z-index: 2;
        }
        .brand-title {
            font-size: 1.45rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #f8fafc;
            line-height: 1.1;
        }
        .brand-ai {
            background: linear-gradient(135deg, #06b6d4 0%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
        }
        .brand-sub {
            font-size: 0.78rem;
            color: #94a3b8;
            margin-top: 2px;
            font-weight: 500;
        }
        .navbar-status-group {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }
        .chip-online {
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }
        .chip-inference {
            background: rgba(6, 182, 212, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(6, 182, 212, 0.25);
        }
        .chip-nodes {
            background: rgba(99, 102, 241, 0.12);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.25);
        }

        /* ── Live Pulsing Dot ── */
        .live-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px #10b981;
            animation: pulseLive 2s infinite;
        }
        @keyframes pulseLive {
            0%   { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70%  { transform: scale(1);    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* ── Animated Gradient Separator ── */
        @keyframes gradientFlow {
            0%   { background-position: 0% 50%; }
            50%  { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .gradient-separator {
            height: 3px;
            background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981, #06b6d4, #6366f1, #ef4444);
            background-size: 300% 100%;
            animation: gradientFlow 5s ease infinite;
            border-radius: 2px;
            margin: 0.4rem 0 1.2rem 0;
        }

        /* ── Metric / KPI Cards ── */
        .metric-card {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.8) 0%, rgba(11, 17, 32, 0.9) 100%);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 18px 20px;
            color: #f8fafc;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 12px 36px rgba(99, 102, 241, 0.15);
        }
        .metric-title {
            font-size: 0.78rem;
            color: #94a3b8;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.1;
            font-family: 'JetBrains Mono', monospace;
        }
        .metric-status {
            font-size: 0.72rem;
            color: #64748b;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 600;
        }

        /* ── Badge Styling ── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
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
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .badge-amber {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .badge-red {
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.35);
        }
        .badge-indigo {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .badge-gray {
            background: rgba(100, 116, 139, 0.15);
            color: #94a3b8;
            border: 1px solid rgba(100, 116, 139, 0.3);
        }

        /* ── Junction Cards ── */
        .junction-card {
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(51, 65, 85, 0.4);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 8px;
            transition: all 0.2s ease;
        }
        .junction-card:hover {
            background: rgba(30, 41, 59, 0.6);
            border-color: rgba(99, 102, 241, 0.5);
            transform: translateX(2px);
        }
        .junction-card-selected {
            background: rgba(30, 41, 59, 0.85) !important;
            border: 1px solid rgba(99, 102, 241, 0.6) !important;
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 8px;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.2);
        }

        /* ── Footer ── */
        .cyber-footer {
            margin-top: 2.5rem;
            padding: 20px 24px;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .footer-logo {
            font-weight: 700;
            font-size: 0.92rem;
            color: #e2e8f0;
        }
        .footer-copy {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 2px;
        }
        .footer-tag {
            background: rgba(51, 65, 85, 0.3);
            border: 1px solid rgba(71, 85, 105, 0.3);
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.68rem;
            color: #94a3b8;
            font-weight: 600;
            margin: 0 3px;
        }
        .footer-uptime {
            font-size: 0.76rem;
            color: #34d399;
            font-weight: 600;
            text-align: right;
        }
        .footer-version {
            font-size: 0.7rem;
            color: #64748b;
            text-align: right;
            margin-top: 2px;
        }

        /* ── Streamlit Tabs Upgrade ── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 10px 18px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #94a3b8;
            border: none;
            background: transparent;
            transition: all 0.2s ease;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0.15) 100%) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(99, 102, 241, 0.4) !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }

        /* ── Streamlit Button Upgrade ── */
        .stButton > button {
            background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
            padding: 8px 18px !important;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3) !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.45) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
