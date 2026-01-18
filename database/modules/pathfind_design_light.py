# ============================================================
# pathfind_design_v2.py - MINIMAL LIGHT DESIGN (ICON-SAFE)
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
    """Setup minimal light design."""
    bin_str = find_background_image("background_light.png")
    if not bin_str:
        st.warning("⚠️ Background image not found")

    complete_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Audiowide&family=Space+Mono:wght@700&family=Poppins:wght@400;500;600;700;800&display=swap');

    /* Background */
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpeg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    /* Buttons - Light hover state */
    button {{
        background-color: rgba(240, 248, 255, 1) !important;
        color: rgba(20, 40, 80, 1) !important;
        border: 1px solid rgba(100, 180, 255, 0.3) !important;
        transition: all 0.3s ease !important;
    }}

    button:hover {{
        background-color: rgba(100, 180, 255, 0.15) !important;
        color: rgba(20, 40, 80, 1) !important;
        border-color: rgba(100, 180, 255, 0.6) !important;
        box-shadow: 0 4px 12px rgba(100, 180, 255, 0.2) !important;
    }}

    button:active {{
        background-color: rgba(100, 180, 255, 0.3) !important;
        color: rgba(20, 40, 80, 1) !important;
    }}

    /* Logo Header */
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
