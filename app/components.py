import streamlit as st
from typing import Optional, List, Dict, Any

def get_risk_badge_html(risk_level: Optional[str]) -> str:
    """Returns the HTML string for a colored risk badge."""
    if risk_level is None:
        return '<span class="badge badge-gray">AWAITING DATA</span>'
    
    lvl = risk_level.upper()
    if lvl == "LOW":
        return '<span class="badge badge-green">LOW</span>'
    elif lvl == "MEDIUM":
        return '<span class="badge badge-amber">MEDIUM</span>'
    elif lvl == "HIGH":
        return '<span class="badge badge-red">HIGH</span>'
    else:
        return f'<span class="badge badge-gray">{lvl}</span>'

def render_risk_badge(risk_level: Optional[str]):
    """Renders the risk badge inline in Streamlit."""
    st.markdown(get_risk_badge_html(risk_level), unsafe_allow_html=True)

def render_contributing_factors(factors: Optional[List[Dict[str, Any]]]):
    """Renders contributing factors as labeled progress bars or displays awaiting data banner."""
    if not factors:
        render_awaiting_data_banner()
        return
        
    st.markdown('<div class="factors-section">', unsafe_allow_html=True)
    for factor_info in factors:
        factor = factor_info.get("factor", "Unknown Factor")
        weight = factor_info.get("weight", 0.0)
        # Ensure weight is within 0.0 and 1.0 bounds
        weight_clamped = max(0.0, min(1.0, float(weight)))
        
        col_label, col_val = st.columns([3, 1])
        with col_label:
            st.markdown(f'<span class="factor-name">{factor}</span>', unsafe_allow_html=True)
        with col_val:
            st.markdown(f'<span class="factor-value">{int(weight_clamped * 100)}% Impact</span>', unsafe_allow_html=True)
            
        st.progress(weight_clamped)
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
                connectors are wired.
            </div>
        </div>
        <div class="radar-sweep"></div>
    </div>
    """, unsafe_allow_html=True)

def inject_custom_styles():
    """Injects custom CSS design system into the app page."""
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
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: #cbd5e1 !important;
        }

        /* ── Custom Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }

        /* ── Badge Styling ── */
        .badge {
            display: inline-block;
            padding: 4px 14px;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-green {
            color: #34d399;
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
        }
        .badge-amber {
            color: #fbbf24;
            background-color: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.25);
        }
        .badge-red {
            color: #f87171;
            background-color: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.3);
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.15);
            animation: badgePulse 2.5s ease-in-out infinite;
        }
        @keyframes badgePulse {
            0%, 100% { box-shadow: 0 0 12px rgba(239, 68, 68, 0.15); }
            50%      { box-shadow: 0 0 22px rgba(239, 68, 68, 0.35); }
        }
        .badge-gray {
            color: #94a3b8;
            background-color: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.2);
        }

        /* ── Awaiting Data Banner ── */
        .awaiting-data-banner {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.6));
            border-left: 4px solid #6366f1;
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-left: 4px solid #6366f1;
            border-radius: 12px;
            padding: 1.25rem;
            margin: 1rem 0;
            display: flex;
            gap: 12px;
            align-items: flex-start;
            position: relative;
            overflow: hidden;
        }
        .awaiting-icon {
            font-size: 1.5rem;
            animation: radarPulse 2s ease-in-out infinite;
        }
        @keyframes radarPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%      { opacity: 0.5; transform: scale(1.1); }
        }
        .awaiting-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #a5b4fc;
            margin-bottom: 0.35rem;
            letter-spacing: 0.06em;
        }
        .awaiting-desc {
            font-size: 0.82rem;
            color: #94a3b8;
            line-height: 1.5;
        }
        .radar-sweep {
            position: absolute;
            top: -50%;
            right: -10%;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
            animation: radarSweep 3s linear infinite;
        }
        @keyframes radarSweep {
            0%   { transform: rotate(0deg); opacity: 0.3; }
            50%  { opacity: 0.6; }
            100% { transform: rotate(360deg); opacity: 0.3; }
        }

        /* ── Factor Section ── */
        .factors-section {
            margin-top: 1rem;
        }
        .factor-name {
            font-size: 0.85rem;
            font-weight: 600;
            color: #f1f5f9;
        }
        .factor-value {
            font-size: 0.78rem;
            color: #94a3b8;
            float: right;
            font-weight: 500;
        }

        /* ── Junction Card Styling ── */
        .junction-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.7) 100%);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(51, 65, 85, 0.4);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.6rem;
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .junction-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.85) 100%);
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.1);
            transform: translateY(-1px);
        }
        .junction-card-selected {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(10, 14, 26, 0.95) 100%);
            border: 1px solid rgba(59, 130, 246, 0.5);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.6rem;
            box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.2), 0 4px 20px rgba(59, 130, 246, 0.1);
        }

        /* ── Section Headers ── */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #f1f5f9 !important;
        }

        /* ── Tab Styling ── */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 4px;
            gap: 4px;
            border: 1px solid rgba(51, 65, 85, 0.4);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            color: #94a3b8;
            font-weight: 600;
            padding: 8px 16px;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #e2e8f0;
            background: rgba(51, 65, 85, 0.3);
        }
        .stTabs [aria-selected="true"] {
            background: rgba(59, 130, 246, 0.15) !important;
            color: #60a5fa !important;
            border-bottom: 2px solid #3b82f6;
        }

        /* ── Form Styling ── */
        .stForm {
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(51, 65, 85, 0.4);
            border-radius: 12px;
            padding: 16px;
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

        /* ── Detail Card ── */
        .detail-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(51, 65, 85, 0.5);
            border-radius: 14px;
            padding: 20px;
            color: #f8fafc;
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
    </style>
    """, unsafe_allow_html=True)
