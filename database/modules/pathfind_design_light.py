# ============================================================
# pathfind_design.py - COMPLETE DESIGN SYSTEM (CORRECTED)
# ============================================================

import streamlit as st
import base64
import os
from pathlib import Path


def get_img_as_base64(file_path: str) -> str:
    """Convert image file to base64."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


def find_background_image(img_file: str = "background_light.png") -> str:
    """Find background image in multiple possible directories."""
    possible_dirs = [
        "personas",
        "./personas",
        os.path.join(os.getcwd(), "personas"),
        os.path.join(os.path.dirname(__file__), "..", "personas"),
        str(Path(__file__).parent.parent / "personas"),
    ]

    for img_dir in possible_dirs:
        try:
            img_path = os.path.join(img_dir, img_file)
            if os.path.exists(img_path) and os.path.isfile(img_path):
                b64_img = get_img_as_base64(img_path)
                if b64_img:
                    return b64_img
        except Exception:
            pass

    return ""


def setup_complete_design() -> None:
    """Setup COMPLETE design with all styles."""
    bin_str = find_background_image("background_light.png")

    complete_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audiowide&family=Space+Mono:wght@700&family=Poppins:wght@400;500;600;700;800&display=swap');

    /* ============================================================
       BACKGROUND & BASE STYLING
       ============================================================ */
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    html, body, .stMarkdown, div[data-testid="stText"], .stButton button {{
        font-family: 'Poppins', sans-serif !important;
        color: var(--text-color);
    }}

    /* ============================================================
       TYPOGRAPHY
       ============================================================ */
    .main-header {{
        font-size: 3rem;
        color: #1a237e;
        font-weight: 700;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }}

    .sub-header {{
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 3rem;
    }}

    @media (prefers-color-scheme: dark) {{
        .main-header {{ color: #2949FF; }}
        .sub-header {{ color: #A1A1A1; }}
    }}

    /* ============================================================
       FLIGHT DISPLAY STYLES
       ============================================================ */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 12px !important;
    }}

    .price-text {{ 
        color: var(--primary-color); 
        font-size: 1.4rem; 
        font-weight: 700; 
    }}
    
    .carrier-text {{ 
        font-size: 1.1rem; 
        font-weight: 600; 
        color: var(--text-color); 
    }}
    
    .route-text {{ 
        color: var(--text-color); 
        opacity: 0.7; 
        font-size: 0.9rem; 
    }}

    .time-badge {{ 
        background-color: #1e1e1e; 
        color: #4caf50; 
        padding: 2px 8px; 
        border-radius: 4px; 
        font-family: monospace; 
        font-weight: 700; 
        margin-right: 10px; 
        border: 1px solid #4caf50; 
    }}
    
    .timeline-row {{ 
        margin: 2px 0; 
        display: flex; 
        align-items: center; 
        font-size: 0.9rem; 
    }}
    
    .duration-info {{ 
        margin-left: 35px; 
        color: var(--text-color); 
        opacity: 0.6; 
        font-style: italic; 
        font-size: 0.8rem; 
    }}
    
    .layover-info {{ 
        margin: 5px 0; 
        text-align: left; 
        padding-left: 50px; 
        color: var(--text-color); 
        opacity: 0.8; 
        font-style: italic; 
        font-size: 0.85rem; 
        border-top: 1px dashed var(--text-color); 
        border-bottom: 1px dashed var(--text-color); 
        padding: 2px 0 2px 50px; 
    }}
    
    .city-name {{ 
        font-weight: 700; 
        color: var(--text-color); 
    }}
    
    .iata-code {{ 
        color: var(--text-color); 
        opacity: 0.6; 
    }}

    /* ============================================================
       SWIPE QUESTION & BUTTONS
       ============================================================ */
    .swipe-question {{
        text-align: center;
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a237e;
        margin-bottom: 2rem;
        padding: 0 !important;
        background: none !important;
        border: none !important;
    }}

    /*  */
    button {{
        background-color: rgba(240, 248, 255, 1) !important;
        color: rgba(20, 40, 80, 1) !important;
        border: 1px solid rgba(100, 180, 255, 0.3) !important;
        transition: all 0.3s ease !important;
        border-radius: 8px !important;
        font-size: 1.1rem !important;         
        padding: 0.8rem 1.5rem !important;
    }}

    button:hover {{
        background-color: rgba(100, 180, 255, 0.15) !important;
        color: rgba(20, 40, 80, 1) !important;
        border-color: rgba(100, 180, 255, 0.6) !important;
        box-shadow: 0 4px 12px rgba(100, 180, 255, 0.2) !important;
        transform: translateY(-2px) !important;
    }}

    button:active {{
        background-color: rgba(100, 180, 255, 0.3) !important;
        color: rgba(20, 40, 80, 1) !important;
    }}

    /* ✅ LARGE SWIPE CARD BUTTONS - ONLY for swipe cards */
    .swipe-card-container button {{
        width: 100% !important;
        border-radius: 14px !important;
        height: 150px !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        transition: all 0.3s ease !important;
        white-space: pre-line !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 10px !important;
        background: linear-gradient(135deg, #f5f7fa 0%, #f0f3f8 100%) !important;
        border: 2px solid #e0e5ed !important;
        padding: 0 !important;
        min-height: 150px !important;
    }}

    .swipe-card-container button:hover {{
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%) !important;
        color: white !important;
        border-color: #1a237e !important;
        box-shadow: 0 8px 24px rgba(26, 35, 126, 0.25) !important;
        transform: translateY(-3px) !important;
    }}

    @media (max-width: 768px) {{
        .swipe-card-container button {{
            height: 120px !important;
            font-size: 1.5rem !important;
            gap: 8px !important;
        }}
        .swipe-question {{
            font-size: 1rem;
        }}
    }}

    @media (max-width: 480px) {{
        .swipe-card-container button {{
            height: 100px !important;
            font-size: 1.2rem !important;
            gap: 6px !important;
        }}
    }}

    /* ============================================================
       PRIDE BADGE
       ============================================================ */
    .pride-badge-top-left {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 1.5rem;
    }}

    .pride-flag-icon {{
        font-size: 48px;
        cursor: pointer;
        transition: all 0.3s ease;
        filter: grayscale(1);
        padding: 0;
        border: 2px solid transparent;
        border-radius: 8px;
        line-height: 1;
    }}

    .pride-flag-icon:hover {{
        transform: scale(1.1);
    }}

    .pride-flag-icon.active {{
        filter: grayscale(0);
        border: 2px solid #FF1493;
        box-shadow: 0 0 15px rgba(255, 20, 147, 0.4);
    }}

    .pride-info-btn {{
        font-size: 20px;
        padding: 0;
        height: auto;
        min-height: auto;
    }}

    /* ============================================================
       LOGO & HEADER
       ============================================================ */
    .pathfind-header {{
        text-align: center;
        margin: 1.5rem 0 2rem 0;
        animation: slide-down 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}

    .pathfind-logo {{
        font-family: 'Audiowide', sans-serif;
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: 5px;
        margin: 0;
        padding: 0;
        color: #FFFFFF;
        text-shadow:
            0 0 30px rgba(100, 180, 255, 0.8),
            0 0 60px rgba(100, 180, 255, 0.4),
            -3px 3px 0 rgba(0, 0, 0, 0.3);
        filter: drop-shadow(0 0 15px rgba(100, 180, 255, 0.6));
        animation: logo-glow 2.5s ease-in-out infinite;
        display: inline-block;
        padding: 1.2rem 2.5rem;
        background: linear-gradient(135deg, rgba(100, 180, 255, 0.15) 0%, rgba(120, 200, 255, 0.08) 100%);
        border: 2px solid rgba(100, 180, 255, 0.4);
        border-radius: 18px;
        backdrop-filter: blur(10px);
    }}

    @keyframes slide-down {{
        from {{ opacity: 0; transform: translateY(-30px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes logo-glow {{
        0%, 100% {{
            filter: drop-shadow(0 0 15px rgba(100, 180, 255, 0.6)) brightness(1);
            text-shadow:
                0 0 30px rgba(100, 180, 255, 0.8),
                0 0 60px rgba(100, 180, 255, 0.4),
                -3px 3px 0 rgba(0, 0, 0, 0.3);
        }}
        50% {{
            filter: drop-shadow(0 0 25px rgba(100, 180, 255, 0.8)) brightness(1.05);
            text-shadow:
                0 0 40px rgba(100, 180, 255, 0.9),
                0 0 80px rgba(100, 180, 255, 0.5),
                -3px 3px 0 rgba(0, 0, 0, 0.3);
        }}
    }}

    .pathfind-icon {{
        font-size: 2.2rem;
        display: inline-block;
        margin-right: 0.8rem;
        animation: float-plane 3s ease-in-out infinite;
        filter: drop-shadow(0 0 12px rgba(100, 180, 255, 0.5));
    }}

    @keyframes float-plane {{
        0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
        25% {{ transform: translateY(-12px) rotate(-5deg); }}
        50% {{ transform: translateY(0px) rotate(0deg); }}
        75% {{ transform: translateY(-12px) rotate(5deg); }}
    }}

    .pathfind-subtitle {{
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        letter-spacing: 3px;
        color: rgba(20, 40, 80, 0.95);
        text-transform: uppercase;
        margin-top: 0.6rem;
        padding: 0.8rem 0;
        border-top: 1px solid rgba(100, 180, 255, 0.25);
        border-bottom: 1px solid rgba(100, 180, 255, 0.25);
        font-weight: 600;
        animation: fade-in 1s ease-out 0.4s backwards;
        text-shadow: 0 1px 2px rgba(255, 255, 255, 0.3) !important;
    }}

    @keyframes fade-in {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    </style>
    """

    st.markdown(complete_css, unsafe_allow_html=True)


def render_pathfind_header() -> None:
    """Render PATHFIND header."""
    st.markdown(
        '''
        <div class="pathfind-header">
            <div class="pathfind-logo">
                <span class="pathfind-icon">✈️</span>
                PATHFIND
            </div>
            <div class="pathfind-subtitle">Your Next Adventure Awaits</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

# Render Footnote
def render_footer() -> None:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 0.3, 0.2])
    
    with col1:
        st.markdown(
            """
            <p style="text-align: left; font-size: 0.85rem; color: rgba(100, 180, 255, 0.6); margin: 0;">
                Student Project @University of Mannheim
            </p>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            """
            <style>
            .footer-about-btn {
                background-color: transparent !important;
                border: none !important;
                padding: 0.3rem 0.6rem !important;
            }
            .footer-about-btn:hover {
                background-color: transparent !important;
                border: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button("About Pathfind", use_container_width=False, key="about_btn"):
            # Speichere den aktuellen step
            st.session_state.previous_step = st.session_state.step
            st.session_state.step = "about"
            st.rerun()