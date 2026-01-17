# ============================================================
# pathfind_design.py - UNIFIED DARK DESIGN v19
# CLOUD OPTIMIZED - SCALE + BACKGROUND FIX
# ============================================================

import streamlit as st
import base64
import os
from pathlib import Path


def get_img_as_base64(file_path):
    """Convert image file to base64."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


def find_background_image(img_file="background.jpg"):
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


def setup_complete_design():
    """
    ULTIMATE DARK DESIGN v19 - CLOUD OPTIMIZED:
    
    FIXES für Cloud:
    - Zoom entfernt (Cloud mag das nicht!)
    - Transform: scale(0.7) stattdessen (funktioniert überall)
    - background-attachment: scroll (nicht fixed, Cloud-Bug fix)
    - Blur direkt auf Element (nicht pseudo-element)
    - Lokal + Cloud identisch 70% skaliert
    """
    
    st.markdown("""
    <style>
        :root {
            color-scheme: dark !important;
        }
        html, body {
            color-scheme: dark !important;
            transform: scale(0.7);
            transform-origin: top left;
            width: 142.857%;
            height: 142.857%;
        }
    </style>
    """, unsafe_allow_html=True)
    
    bin_str = find_background_image("background.jpg")

    if not bin_str:
        st.warning("⚠️ Background image not found - using gradient fallback")
    
    complete_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audiowide&family=Space+Mono:wght@700&family=Poppins:wght@400;500;600;700;800&display=swap');
    
    /* ========================================
       FORCE DARK MODE EVERYWHERE
       ======================================== */
    :root {{
        color-scheme: dark !important;
    }}
    
    html, body {{
        color-scheme: dark !important;
        transform: scale(0.7);
        transform-origin: top left;
        width: 142.857%;
        height: 142.857%;
        margin: 0;
        padding: 0;
    }}
    
    /* ========================================
       FULL-SCREEN BACKGROUND - DARK
       Cloud-optimized (scroll statt fixed!)
       ======================================== */
    html, body {{
        background-image: url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: scroll;
        background-color: #0a0f1e !important;
    }}
    
    [data-testid="stAppViewContainer"], .stApp {{
        background: linear-gradient(135deg, rgba(10, 15, 30, 0.4) 0%, rgba(26, 42, 58, 0.4) 50%, rgba(15, 21, 32, 0.4) 100%), 
                    url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: scroll;
        background-color: #0a0f1e !important;
        filter: blur(0px);
    }}
    
    [data-testid="stMain"] {{
        background: transparent !important;
    }}
    
    /* ========================================
       UNIVERSAL TEXT - MAXIMUM CONTRAST
       ======================================== */
    * {{
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    body, .stMarkdown, div[data-testid="stText"], .stMarkdown p, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    .stMarkdown h5, .stMarkdown h6, .stMarkdown label, span, 
    [data-testid="stMarkdownContainer"], div[role="alert"],
    div[data-testid="stMetric"], div[data-testid="stMetricDelta"],
    .stSelectbox label, .stTextInput label, .stDateInput label, .stNumberInput label {{
        color: rgba(255, 255, 255, 1) !important;
        font-family: 'Poppins', sans-serif !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6) !important;
    }}
    
    /* Labels & Headings - Super Hell */
    label, h1, h2, h3, h4, h5, h6 {{
        color: rgba(255, 255, 255, 1) !important;
        font-weight: 600 !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8) !important;
    }}
    
    /* Links - Cyan */
    a {{
        color: rgba(100, 200, 255, 1) !important;
        font-weight: 600 !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4) !important;
    }}
    
    a:hover {{
        color: rgba(150, 220, 255, 1) !important;
    }}
    
    /* Alerts & Messages */
    div[data-testid="stAlert"] {{
        background: rgba(20, 25, 40, 0.9) !important;
        border: 1.5px solid rgba(100, 140, 200, 0.5) !important;
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span {{
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    /* ========================================
       METRIC & STAT VALUES
       ======================================== */
    [data-testid="stMetric"] {{
        background: rgba(20, 25, 40, 0.8) !important;
    }}
    
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] span {{
        color: rgba(255, 255, 255, 1) !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5) !important;
    }}
    
    /* ========================================
       PATHFIND LOGO
       ======================================== */
    .pathfind-header {{
        text-align: center;
        margin: 1.5rem 0 2rem 0;
        animation: slide-down 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    
    .pathfind-logo {{
        font-family: 'Audiowide', sans-serif;
        font-size: 4.2rem;
        font-weight: 900;
        letter-spacing: 5px;
        margin: 0;
        padding: 0;
        color: #FFFFFF;
        text-shadow: 
            0 0 30px rgba(255, 215, 0, 0.9),
            0 0 60px rgba(255, 215, 0, 0.5),
            -3px 3px 0 rgba(0, 0, 0, 0.6);
        filter: drop-shadow(0 0 15px rgba(255, 215, 0, 0.7));
        animation: logo-glow 2.5s ease-in-out infinite;
        display: inline-block;
        padding: 1.2rem 2.5rem;
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255, 255, 0, 0.05) 100%);
        border: 2px solid rgba(255, 215, 0, 0.4);
        border-radius: 18px;
        backdrop-filter: blur(10px);
    }}
    
    @keyframes slide-down {{
        from {{
            opacity: 0;
            transform: translateY(-30px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    @keyframes logo-glow {{
        0%, 100% {{
            filter: drop-shadow(0 0 15px rgba(255, 215, 0, 0.7)) brightness(1);
            text-shadow: 
                0 0 30px rgba(255, 215, 0, 0.9),
                0 0 60px rgba(255, 215, 0, 0.5),
                -3px 3px 0 rgba(0, 0, 0, 0.6);
        }}
        50% {{
            filter: drop-shadow(0 0 25px rgba(255, 215, 0, 0.9)) brightness(1.05);
            text-shadow: 
                0 0 40px rgba(255, 215, 0, 1),
                0 0 80px rgba(255, 215, 0, 0.7),
                -3px 3px 0 rgba(0, 0, 0, 0.6);
        }}
    }}
    
    .pathfind-icon {{
        font-size: 3.2rem;
        display: inline-block;
        margin-right: 0.8rem;
        animation: float-plane 3s ease-in-out infinite;
        filter: drop-shadow(0 0 12px rgba(255, 215, 0, 0.6));
    }}
    
    @keyframes float-plane {{
        0%, 100% {{
            transform: translateY(0px) rotate(0deg);
        }}
        25% {{
            transform: translateY(-12px) rotate(-5deg);
        }}
        50% {{
            transform: translateY(0px) rotate(0deg);
        }}
        75% {{
            transform: translateY(-12px) rotate(5deg);
        }}
    }}
    
    .pathfind-subtitle {{
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        letter-spacing: 3px;
        color: rgba(255, 255, 255, 0.9);
        text-transform: uppercase;
        margin-top: 0.6rem;
        padding: 0.8rem 0;
        border-top: 1px solid rgba(255, 215, 0, 0.25);
        border-bottom: 1px solid rgba(255, 215, 0, 0.25);
        font-weight: 600;
        animation: fade-in 1s ease-out 0.4s backwards;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5) !important;
    }}
    
    @keyframes fade-in {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    /* ========================================
       CONTENT MODULES - BLURRED DARK BOXES
       Direct styling (NO wrapper/inner mess!)
       ======================================== */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(15, 20, 40, 0.35) !important;
        backdrop-filter: blur(32px) !important;
        -webkit-backdrop-filter: blur(32px) !important;
        border-radius: 22px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.35),
            inset 0 0 25px rgba(255, 255, 255, 0.08) !important;
        color: rgba(255, 255, 255, 1);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        background: rgba(15, 20, 40, 0.4) !important;
        box-shadow: 
            0 16px 64px rgba(0, 0, 0, 0.45),
            inset 0 0 35px rgba(255, 255, 255, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
    }}
    
    /* ========================================
       DARK BUTTONS - ULTIMATE AGGRESSIVE
       ======================================== */
    button,
    .stButton button,
    .stButton > button,
    input[type="button"],
    input[type="submit"],
    input[type="reset"],
    [role="button"],
    button[kind="primary"],
    button[kind="secondary"],
    [data-testid="stButton"] button,
    [data-testid="stColumn"] > div button,
    [data-testid="stColumn"] button,
    [data-testid="stHorizontalBlock"] button,
    [data-testid="stExpanderContainer"] button {{
        background: rgba(25, 35, 55, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        border: 1.5px solid rgba(80, 120, 180, 0.7) !important;
        color: rgba(255, 255, 255, 0.99) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.7rem 1.5rem !important;
        box-shadow: 
            0 6px 20px rgba(0, 0, 0, 0.4),
            inset 0 0 12px rgba(255, 255, 255, 0.04) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4) !important;
    }}
    
    button:hover,
    .stButton button:hover,
    .stButton > button:hover,
    input[type="button"]:hover,
    input[type="submit"]:hover,
    input[type="reset"]:hover,
    [role="button"]:hover,
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover,
    [data-testid="stButton"] button:hover,
    [data-testid="stColumn"] > div button:hover,
    [data-testid="stColumn"] button:hover,
    [data-testid="stHorizontalBlock"] button:hover,
    [data-testid="stExpanderContainer"] button:hover {{
        background: rgba(50, 70, 100, 0.98) !important;
        border: 1.5px solid rgba(100, 150, 220, 0.9) !important;
        box-shadow: 
            0 10px 30px rgba(0, 0, 0, 0.5),
            inset 0 0 15px rgba(255, 255, 255, 0.06) !important;
        transform: translateY(-2px) !important;
    }}
    
    button:active,
    .stButton button:active,
    .stButton > button:active,
    input[type="button"]:active,
    input[type="submit"]:active,
    input[type="reset"]:active,
    [role="button"]:active,
    button[kind="primary"]:active,
    button[kind="secondary"]:active,
    [data-testid="stButton"] button:active,
    [data-testid="stColumn"] > div button:active,
    [data-testid="stColumn"] button:active,
    [data-testid="stHorizontalBlock"] button:active,
    [data-testid="stExpanderContainer"] button:active {{
        transform: translateY(0px) !important;
        box-shadow: 
            0 4px 12px rgba(0, 0, 0, 0.3),
            inset 0 0 8px rgba(255, 255, 255, 0.03) !important;
    }}
    
    /* ========================================
       INPUT FIELDS - Dark with bright text
       ======================================== */
    input,
    .stTextInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input,
    textarea {{
        background: rgba(10, 15, 35, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        border: 1.5px solid rgba(80, 120, 180, 0.5) !important;
        color: rgba(255, 255, 255, 1) !important;
        border-radius: 10px !important;
        padding: 0.85rem 1.1rem !important;
        transition: all 0.25s ease !important;
        font-weight: 500 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }}
    
    input::placeholder,
    .stTextInput > div > div > input::placeholder,
    .stDateInput > div > div > input::placeholder,
    textarea::placeholder {{
        color: rgba(255, 255, 255, 0.4) !important;
    }}
    
    input:focus,
    .stTextInput > div > div > input:focus,
    .stDateInput > div > div > input:focus,
    textarea:focus {{
        border: 1.5px solid rgba(100, 180, 255, 1) !important;
        box-shadow: 0 0 30px rgba(100, 180, 255, 0.5) !important;
        background: rgba(10, 15, 35, 0.95) !important;
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    /* ========================================
       RADIO & CHECKBOXES - VISIBLE FEEDBACK
       ======================================== */
    [role="radio"], [role="checkbox"], 
    input[type="radio"], input[type="checkbox"] {{
        accent-color: #64C8FF !important;
        cursor: pointer !important;
    }}
    
    input[type="radio"]:checked,
    input[type="checkbox"]:checked {{
        accent-color: #00FFFF !important;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.9) !important;
    }}
    
    input[type="radio"]:checked + label,
    input[type="checkbox"]:checked + label {{
        color: rgba(0, 255, 255, 1) !important;
        font-weight: 700 !important;
        text-shadow: 
            0 0 15px rgba(0, 255, 255, 0.9),
            0 2px 6px rgba(0, 0, 0, 0.7) !important;
    }}
    
    /* ========================================
       PROGRESS BAR
       ======================================== */
    [role="progressbar"] {{
        background: rgba(80, 120, 180, 0.2) !important;
    }}
    
    [role="progressbar"] > div {{
        background: linear-gradient(90deg, #64C8FF 0%, #7ED4FF 50%, #64C8FF 100%) !important;
        box-shadow: 0 0 20px rgba(100, 200, 255, 0.6) !important;
    }}
    
    /* ========================================
       TABS
       ======================================== */
    [data-testid="stTabs"] button {{
        background: transparent !important;
        color: rgba(255, 255, 255, 0.85) !important;
        font-weight: 600 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4) !important;
    }}
    
    [data-testid="stTabs"] button[aria-selected="true"] {{
        color: rgba(100, 200, 255, 1) !important;
        border-bottom: 3px solid rgba(100, 200, 255, 0.95) !important;
    }}
    
    /* ========================================
       SELECT BOX DROPDOWN
       ======================================== */
    .stSelectbox [data-baseweb="select"],
    select {{
        background: rgba(15, 20, 40, 0.8) !important;
        color: rgba(255, 255, 255, 1) !important;
        border: 1.5px solid rgba(80, 120, 180, 0.5) !important;
    }}
    
    /* ========================================
       DROPDOWNS & MENUS
       ======================================== */
    [data-baseweb="popover"],
    [data-baseweb="menu"] {{
        background: rgba(20, 25, 40, 0.95) !important;
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    [data-baseweb="menu"] li {{
        color: rgba(255, 255, 255, 1) !important;
    }}
    
    [data-baseweb="menu"] [aria-selected="true"] {{
        background: rgba(100, 200, 255, 0.3) !important;
        border: 1px solid rgba(100, 200, 255, 0.6) !important;
        color: rgba(0, 255, 255, 1) !important;
    }}
    
    /* ========================================
       SCROLLBAR
       ======================================== */
    ::-webkit-scrollbar {{
        width: 10px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: rgba(255, 255, 255, 0.05);
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: rgba(100, 200, 255, 0.55);
        border-radius: 5px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(100, 200, 255, 0.85);
    }}
    
    /* ========================================
       DIVIDER LINES
       ======================================== */
    hr {{
        border-color: rgba(255, 255, 255, 0.15) !important;
    }}
    
    /* ========================================
       CARDS & CONTAINERS
       ======================================== */
    div[data-testid="stColumn"] {{
        background: rgba(15, 20, 40, 0.1) !important;
    }}
    
    /* ========================================
       DARK MODE SUPPORT
       ======================================== */
    @media (prefers-color-scheme: dark) {{
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(15, 15, 30, 0.35) !important;
        }}
    }}
    
    /* ========================================
       MOBILE RESPONSIVE
       ======================================== */
    @media (max-width: 768px) {{
        .pathfind-logo {{
            font-size: 3rem;
            padding: 1rem 2rem;
        }}
        
        .pathfind-icon {{
            font-size: 2.5rem;
            margin-right: 0.5rem;
        }}
        
        .pathfind-subtitle {{
            font-size: 0.8rem;
            letter-spacing: 2px;
        }}
    }}
    
    @media (max-width: 480px) {{
        .pathfind-logo {{
            font-size: 2.2rem;
            padding: 0.8rem 1.5rem;
            letter-spacing: 2px;
        }}
        
        .pathfind-icon {{
            font-size: 2rem;
            margin-right: 0.3rem;
        }}
        
        .pathfind-subtitle {{
            font-size: 0.7rem;
            letter-spacing: 1px;
        }}
    }}
    </style>
    """
    
    st.markdown(complete_css, unsafe_allow_html=True)


# ============================================================
# HEADER COMPONENT
# ============================================================

def render_pathfind_header():
    """Render the ultra-cool PATHFIND header"""
    st.markdown('''
        <div class="pathfind-header">
            <div class="pathfind-logo">
                <span class="pathfind-icon">✈️</span>
                PATHFIND
            </div>
            <div class="pathfind-subtitle">Your Next Adventure Awaits</div>
        </div>
    ''', unsafe_allow_html=True)