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
        <div class="awaiting-title">📡 AWAITING TELEMETRY DATA</div>
        <div class="awaiting-desc">
            Visual risk analysis and historical accident weighting are currently pending for this junction. 
            Detailed contributing factor scores will be populated automatically when live streams and database 
            connectors are wired.
        </div>
    </div>
    """, unsafe_allow_html=True)

def inject_custom_styles():
    """Injects custom CSS design system into the app page."""
    # We will use theme-aware colors as per streamlit_framework guidance
    st.markdown("""
    <style>
        /* Badge styling */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .badge-green {
            color: #16a34a;
            background-color: rgba(22, 163, 74, 0.1);
            border: 1px solid rgba(22, 163, 74, 0.2);
        }
        .badge-amber {
            color: #d97706;
            background-color: rgba(217, 119, 6, 0.1);
            border: 1px solid rgba(217, 119, 6, 0.2);
        }
        .badge-red {
            color: #dc2626;
            background-color: rgba(220, 38, 38, 0.1);
            border: 1px solid rgba(220, 38, 38, 0.2);
        }
        .badge-gray {
            color: #71717a;
            background-color: rgba(113, 113, 122, 0.1);
            border: 1px solid rgba(113, 113, 122, 0.2);
        }

        /* Banner styling */
        .awaiting-data-banner {
            background-color: rgba(113, 113, 122, 0.05);
            border-left: 4px solid #71717a;
            border-radius: 8px;
            padding: 1.25rem;
            margin: 1rem 0;
        }
        .awaiting-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #71717a;
            margin-bottom: 0.35rem;
            letter-spacing: 0.05em;
        }
        .awaiting-desc {
            font-size: 0.85rem;
            color: #71717a;
            line-height: 1.4;
        }

        /* Factor styling */
        .factors-section {
            margin-top: 1rem;
        }
        .factor-name {
            font-size: 0.85rem;
            font-weight: 600;
            color: #f8fafc;
        }
        .factor-value {
            font-size: 0.8rem;
            color: #94a3b8;
            float: right;
        }

        /* Card layout styling */
        .junction-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .junction-card:hover {
            border-color: #475569;
            background-color: #334155;
        }
        .junction-card-selected {
            background-color: #0f172a;
            border: 1px solid #3b82f6;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }
    </style>
    """, unsafe_allow_html=True)
