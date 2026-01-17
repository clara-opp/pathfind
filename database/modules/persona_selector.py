# ============================================================================
# PERSONA SELECTOR MODULE (CAROUSEL + AUTO-REDISTRIBUTE WEIGHTS)
# File: modules/persona_selector.py
# Purpose: Smooth carousel with auto-adjusting weight sliders
# ============================================================================

import streamlit as st
import base64
import os
from pathlib import Path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_img_as_base64(file_path):
    """Convert local image file to base64 for HTML embedding."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


def find_image_source(img_file, img_url):
    """
    Find image source: try local file first, then fallback to URL.
    Searches multiple possible directories.
    """
    # Possible directories to search
    possible_dirs = [
        "personas",
        "./personas",
        os.path.join(os.getcwd(), "personas"),
        os.path.join(os.path.dirname(__file__), "..", "personas"),
        str(Path(__file__).parent.parent / "personas"),
    ]
    
    # Try each directory
    for img_dir in possible_dirs:
        try:
            img_path = os.path.join(img_dir, img_file)
            if os.path.exists(img_path) and os.path.isfile(img_path):
                b64_img = get_img_as_base64(img_path)
                if b64_img:  # Successfully encoded
                    return f"data:image/jpeg;base64,{b64_img}"
        except Exception:
            pass
    
    # If no local file found, use URL
    return img_url or "https://via.placeholder.com/600x450?text=No+Image"


def load_carousel_css():
    """Load optimized CSS with smooth animations and centered tooltip."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Poppins:wght@300;400;600&display=swap');
        
        /* Bounce Animation */
        @keyframes bounce-in {
            0% {
                transform: scale(0.85) translateY(20px);
                opacity: 0;
            }
            50% {
                transform: scale(1.05);
            }
            100% {
                transform: scale(1) translateY(0);
                opacity: 1;
            }
        }
        
        /* Continuous Gentle Bounce */
        @keyframes gentle-bounce {
            0%, 100% {
                transform: translateY(0px);
            }
            50% {
                transform: translateY(-8px);
            }
        }
        
        /* 3D Rotation Effect - Smooth */
        @keyframes rotate-smooth {
            0% {
                transform: rotateY(15deg) rotateX(3deg);
                opacity: 0.4;
            }
            100% {
                transform: rotateY(0deg) rotateX(0deg);
                opacity: 1;
            }
        }
        
        /* Smooth Fade Transition */
        @keyframes smooth-fade {
            0% {
                opacity: 0;
                transform: scale(0.98);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        /* Card Design - Full Image Visibility */
        .profile-card {
            background: linear-gradient(145deg, rgba(255,255,255,0.98), rgba(245,247,252,0.95));
            border-radius: 28px;
            border: 1px solid rgba(255,255,255,0.5);
            box-shadow: 0 15px 40px rgba(0,0,0,0.08);
            padding: 12px;
            text-align: center;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            aspect-ratio: 4/3;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: visible;
            perspective: 1000px;
            position: relative;
        }

        /* Active Card (Center) - Continuous Bounce */
        .profile-card.active {
            transform: scale(1.1) rotateY(0deg);
            border: 3px solid #667eea;
            box-shadow: 0 25px 70px rgba(102, 126, 234, 0.35);
            z-index: 2;
            opacity: 1;
            animation: bounce-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards,
                       gentle-bounce 3s ease-in-out 0.5s infinite;
        }

        /* Inactive Cards (Left/Right) - Smooth Transition */
        .profile-card.inactive {
            transform: scale(0.8) rotateY(25deg);
            opacity: 0.35;
            filter: grayscale(0.7) blur(1.2px);
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }

        /* Image Container - CONTAIN mode for full image */
        .card-img-container {
            width: 100%;
            height: 100%;
            border-radius: 20px;
            overflow: visible;
            margin: 0;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #f5f7fa 0%, #f0f3f8 100%);
            position: relative;
        }
        
        .card-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            animation: rotate-smooth 0.6s ease-out forwards;
            border-radius: 16px;
        }

        /* Info Icon Container */
        .info-icon-wrapper {
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 10;
        }

        .info-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(102, 126, 234, 0.95);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 18px;
            box-shadow: 0 2px 12px rgba(102, 126, 234, 0.45);
        }

        .info-icon:hover {
            background: rgba(102, 126, 234, 1);
            transform: scale(1.15);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.6);
        }

        /* Tooltip - Centered below icon */
        .tooltip {
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(8px);
            background: rgba(30, 30, 40, 0.99);
            color: #ffffff;
            padding: 14px 18px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 500;
            opacity: 0;
            pointer-events: none;
            transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 0 10px 32px rgba(0,0,0,0.4);
            z-index: 11;
            max-width: 300px;
            white-space: normal;
            text-align: center;
            line-height: 1.5;
            letter-spacing: 0.3px;
        }

        .info-icon:hover .tooltip {
            opacity: 1;
            pointer-events: auto;
            transform: translateX(-50%) translateY(0px);
        }

        /* Navigation Buttons */
        .nav-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 28px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);
            animation: gentle-bounce 2.5s ease-in-out;
        }

        .nav-button:hover {
            transform: scale(1.15) translateY(-3px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }

        .nav-button:active {
            transform: scale(0.95) translateY(2px);
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
        }

        /* Spacer for button */
        .button-spacer {
            margin-top: 50px;
            margin-bottom: 30px;
        }

        /* Select Button Animation */
        [data-testid="stButton"] button {
            animation: smooth-fade 0.4s ease-out !important;
        }

        /* Remove loading spinner during transitions */
        .stSpinner {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)


def create_card_html(profile_data, is_active=False):
    """Generate HTML for persona card with centered info tooltip."""
    status_class = "active" if is_active else "inactive"
    
    # Find image source (local or URL)
    img_src = find_image_source(profile_data["img_file"], profile_data.get("img_url"))

    # Escape quotes in description
    description = profile_data['description'].replace('"', '&quot;').replace("'", "&#39;")

    html = f"""
    <div class="profile-card {status_class}">
        <div class="card-img-container">
            <img src="{img_src}" class="card-img" alt="{profile_data['display_name']}" loading="lazy">
            <div class="info-icon-wrapper">
                <div class="info-icon">
                    ℹ️
                    <div class="tooltip">{description}</div>
                </div>
            </div>
        </div>
    </div>
    """
    return html


# ============================================================================
# PERSONA DEFINITIONS
# ============================================================================

def get_travel_profiles():
    """Return list of all travel persona profiles with fallback image URLs."""
    return [
        {
            "internal_key": "Story Hunter",
            "display_name": "Story Hunter",
            "img_file": "storyhunter.jpg",
            "img_url": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&h=450&fit=crop",
            "description": "Cultural explorer seeking authentic experiences and hidden narratives.",
            "weights": {
                "safety_tugo": 15, "culture": 22, "hiddengem": 14, "cost": 12, 
                "restaurant": 8, "groceries": 5, "weather": 10, "qol": 7, 
                "cleanair": 5, "purchasingpower": 2, "rent": 0, "healthcare": 0, 
                "luxuryprice": 0, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "Family Fortress",
            "display_name": "Family Fortress",
            "img_file": "familyfortress.jpg",
            "img_url": "https://images.unsplash.com/photo-1511895426328-dc8714191300?w=600&h=450&fit=crop",
            "description": "Safety-focused family travelers prioritizing comfort and security.",
            "weights": {
                "safety_tugo": 28, "healthcare": 14, "qol": 12, "cleanair": 12, 
                "weather": 10, "culture": 6, "cost": 8, "restaurant": 3, 
                "groceries": 3, "purchasingpower": 4, "rent": 0, "hiddengem": 0, 
                "luxuryprice": 0, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "WiFi Goblin",
            "display_name": "Digital Nomad",
            "img_file": "digitalnomad.jpg",
            "img_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&h=450&fit=crop",
            "description": "Location-independent professional balancing work and travel.",
            "weights": {
                "rent": 20, "purchasingpower": 14, "groceries": 10, "restaurant": 6, 
                "cost": 12, "safety_tugo": 14, "qol": 12, "cleanair": 6, 
                "weather": 4, "culture": 2, "hiddengem": 0, "healthcare": 0, 
                "luxuryprice": 0, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "Comfort Snob",
            "display_name": "Honeymoon",
            "img_file": "honeymoon.jpg",
            "img_url": "https://images.unsplash.com/photo-1537571627991-a7ad86a66464?w=600&h=450&fit=crop",
            "description": "Luxury-seeking couples prioritizing premium experiences and romance.",
            "weights": {
                "qol": 20, "safety_tugo": 18, "cleanair": 12, "healthcare": 10, 
                "weather": 10, "culture": 6, "luxuryprice": 10, "restaurant": 4, 
                "purchasingpower": 4, "cost": 0, "groceries": 0, "rent": 0, 
                "hiddengem": 2, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "Budget Goblin",
            "display_name": "Budget Backpacker",
            "img_file": "budgetbackpacker.jpg",
            "img_url": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=600&h=450&fit=crop",
            "description": "Cost-conscious adventurer seeking authentic experiences on a budget.",
            "weights": {
                "cost": 26, "groceries": 12, "restaurant": 10, "purchasingpower": 12, 
                "safety_tugo": 14, "weather": 8, "culture": 6, "cleanair": 6, 
                "qol": 4, "hiddengem": 2, "rent": 0, "healthcare": 0, 
                "luxuryprice": 0, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "Clean Air Calm",
            "display_name": "Clean Air & Calm",
            "img_file": "cleanair.jpg",
            "img_url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&h=450&fit=crop",
            "description": "Wellness-focused traveler prioritizing health, nature, and tranquility.",
            "weights": {
                "cleanair": 24, "safety_tugo": 22, "qol": 12, "healthcare": 10, 
                "weather": 10, "cost": 10, "groceries": 4, "restaurant": 2, 
                "culture": 4, "hiddengem": 2, "purchasingpower": 0, "rent": 0, 
                "luxuryprice": 0, "astro": 0, "jitter": 0
            }
        },
        {
            "internal_key": "Chaos Gremlin but not stupid",
            "display_name": "Chaos Gremlin",
            "img_file": "chaosgremlin.jpg",
            "img_url": "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&h=450&fit=crop",
            "description": "Spontaneous adventurer thriving on unplanned experiences and surprises.",
            "weights": {
                "hiddengem": 24, "culture": 10, "cost": 10, "restaurant": 6, 
                "weather": 4, "safety_tugo": 16, "qol": 6, "cleanair": 4, 
                "purchasingpower": 4, "jitter": 10, "astro": 6, "luxuryprice": 0, 
                "rent": 0, "healthcare": 0, "groceries": 0
            }
        }
    ]


# ============================================================================
# WEIGHT REDISTRIBUTION LOGIC (FIXED)
# ============================================================================

def redistribute_weights(weights_dict, changed_key, new_value, weight_keys):
    """
    Auto-redistribute weights to maintain sum of 100.
    When one weight is changed, proportionally reduce other weights.
    FIXED: Proper rounding to ensure sum = 100
    """
    old_value = weights_dict.get(changed_key, 0)
    diff = new_value - old_value
    
    # Set the new value
    weights_dict[changed_key] = new_value
    
    # Get all other keys and their current sum
    other_keys = [k for k in weight_keys if k != changed_key]
    other_sum = sum(weights_dict.get(k, 0) for k in other_keys)
    
    if other_sum > 0 and diff != 0:
        # Redistribute the difference proportionally
        reduction_remainder = 0
        for idx, other_key in enumerate(other_keys):
            current_val = weights_dict.get(other_key, 0)
            if other_sum > 0:
                proportion = current_val / other_sum
                reduction = diff * proportion
                rounded_reduction = int(round(reduction + reduction_remainder))
                weights_dict[other_key] = max(0, current_val - rounded_reduction)
                reduction_remainder = reduction + reduction_remainder - rounded_reduction
    
    # Final normalization to ensure sum = 100
    current_sum = sum(weights_dict.values())
    if current_sum != 100 and current_sum > 0:
        scale_factor = 100 / current_sum
        for key in weight_keys:
            weights_dict[key] = int(round(weights_dict[key] * scale_factor))
        
        # Final adjustment for rounding errors
        final_sum = sum(weights_dict.values())
        if final_sum != 100:
            diff_needed = 100 - final_sum
            # Find largest value and adjust it
            max_key = max(weight_keys, key=lambda k: weights_dict.get(k, 0))
            weights_dict[max_key] += diff_needed
    
    return weights_dict


# ============================================================================
# MAIN RENDER FUNCTION (FIXED)
# ============================================================================

def render_persona_step(datamanager):
    """
    Render persona carousel with optional advanced customization.
    Auto-redistributes weights to maintain 100 point sum.
    
    Features:
    - Smooth carousel with 3 persona cards
    - Quick next button to proceed immediately
    - Optional fine-tune expander for custom weight adjustments
    - Auto-redistributing weight sliders (single column)
    - Weights always sum to 100 (FIXED)
    - Fallback to Unsplash URLs if local images not found
    """
    
    # Get global functions
    import sys
    main_module = sys.modules['__main__']
    WEIGHT_KEYS = getattr(main_module, 'WEIGHT_KEYS', None)
    normalize_weights_100 = getattr(main_module, 'normalize_weights_100', None)
    
    if WEIGHT_KEYS is None or normalize_weights_100 is None:
        st.error("❌ ERROR: WEIGHT_KEYS or normalize_weights_100 not found in app.py")
        st.stop()
    
    travel_profiles = get_travel_profiles()
    total_profiles = len(travel_profiles)
    
    # ========== INITIALIZATION ==========
    if 'profile_index' not in st.session_state:
        st.session_state.profile_index = 0
    
    if "custom_weights_sliders" not in st.session_state:
        st.session_state.custom_weights_sliders = {k: v for k, v in travel_profiles[0]["weights"].items()}
    
    if "last_profile_idx" not in st.session_state:
        st.session_state.last_profile_idx = 0
    
    # ========== LOAD CSS ==========
    load_carousel_css()
    
    # ========== PAGE TITLE ==========
    st.markdown('<h2 style="text-align: center; margin-bottom: 50px; margin-top: 20px;">Choose Your Travel Persona</h2>', unsafe_allow_html=True)
    
    # ========== CAROUSEL LOGIC ==========
    current_idx = st.session_state.profile_index
    prev_idx = (current_idx - 1) % total_profiles
    next_idx = (current_idx + 1) % total_profiles
    
    # Create layout with navigation buttons
    col_nav_prev, col_prev, col_active, col_next, col_nav_next = st.columns(
        [0.8, 1.6, 2.5, 1.6, 0.8], 
        vertical_alignment="center",
        gap="medium"
    )
    
    # ========== PREVIOUS NAVIGATION BUTTON ==========
    with col_nav_prev:
        if st.button("◀", key="nav_prev", help="Previous Profile", use_container_width=True):
            st.session_state.profile_index = prev_idx
            st.rerun()
    
    # ========== NEXT NAVIGATION BUTTON ==========
    with col_nav_next:
        if st.button("▶", key="nav_next", help="Next Profile", use_container_width=True):
            st.session_state.profile_index = next_idx
            st.rerun()
    
    # ========== PREVIOUS CARD (GREYED OUT) ==========
    with col_prev:
        st.markdown(create_card_html(travel_profiles[prev_idx], is_active=False), unsafe_allow_html=True)
    
    # ========== ACTIVE CARD (CENTER, HIGHLIGHTED) ==========
    with col_active:
        st.markdown(create_card_html(travel_profiles[current_idx], is_active=True), unsafe_allow_html=True)
    
    # ========== NEXT CARD (GREYED OUT) ==========
    with col_next:
        st.markdown(create_card_html(travel_profiles[next_idx], is_active=False), unsafe_allow_html=True)
    
    # ========== STORE CURRENT SELECTED PROFILE ==========
    selected_profile = travel_profiles[current_idx]
    st.session_state.selected_persona = selected_profile["display_name"]
    
    # Initialize custom weights with current profile on first load or when carousel changes
    if st.session_state.last_profile_idx != current_idx:
        st.session_state.custom_weights_sliders = {k: v for k, v in selected_profile["weights"].items()}
        st.session_state.last_profile_idx = current_idx
    
    # ========== MAIN NEXT BUTTON ==========
    st.markdown('<div style="margin-top: 30px; margin-bottom: 30px;"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🎯 Next: Swipe & Refine", key="next_btn", type="primary", use_container_width=True):
            # Commit the weights from custom sliders
            st.session_state.weights = normalize_weights_100(st.session_state.custom_weights_sliders)
            st.session_state.persona_active = selected_profile["display_name"]
            
            # Advance to next step
            st.session_state.step = 3
            st.rerun()
    
    # ========== ADVANCED CUSTOMIZATION EXPANDER ==========
    st.markdown('<div style="margin-top: 40px; margin-bottom: 20px;"></div>', unsafe_allow_html=True)
    with st.expander("⚙️ Fine-Tune Your Persona (Optional)"):
        st.write("Customize the weights for your selected profile. Other values adjust automatically to keep sum = 100.")
        
        if st.button("🔄 Reset to Persona Defaults", use_container_width=True, key="reset_btn"):
            st.session_state.custom_weights_sliders = {k: v for k, v in selected_profile["weights"].items()}
            st.rerun()
        
        # Show current total
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        total_live = sum(st.session_state.custom_weights_sliders.values())
        if total_live == 100:
            st.success(f"✅ Perfect! Sum = {total_live}/100")
        else:
            st.warning(f"⚠️ Current sum: {total_live}/100 (will be auto-corrected on next)")
        
        # Slider labels with descriptions
        slider_labels = {
            "safety_tugo": "Safety (TuGo Advisory)",
            "cost": "Cost (Cheap is good)",
            "restaurant": "Restaurant Value",
            "groceries": "Groceries Value",
            "rent": "Rent (Long stay)",
            "purchasingpower": "Purchasing Power",
            "qol": "Quality of Life",
            "healthcare": "Health Care",
            "cleanair": "Clean Air (Low pollution)",
            "culture": "Culture (UNESCO)",
            "weather": "Weather Fit",
            "luxuryprice": "Luxury Price Vibe (High cost can be good)",
            "hiddengem": "Hidden Gem Spice",
            "astro": "Astro Spice",
            "jitter": "Chaos Jitter"
        }
        
        # Create sliders underlined with auto-redistribution
        for key in WEIGHT_KEYS:
            current_val = st.session_state.custom_weights_sliders.get(key, 0)
            label = slider_labels.get(key, key.replace('_', ' ').title())
            
            new_val = st.slider(
                label,
                min_value=0,
                max_value=100,
                value=current_val,
                step=1,
                key=f"adv_slider_{key}"
            )
            
            # If value changed, redistribute to keep sum = 100
            if new_val != current_val:
                st.session_state.custom_weights_sliders = redistribute_weights(
                    st.session_state.custom_weights_sliders,
                    key,
                    new_val,
                    WEIGHT_KEYS
                )
                st.rerun()
        
        # ========== CUSTOM CONTINUE BUTTON ==========
        st.markdown('<div style="margin-top: 30px; margin-bottom: 15px;"></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("✨ Continue with Custom Settings", key="custom_next_btn", type="primary", use_container_width=True):
                # Commit the custom weights
                st.session_state.weights = normalize_weights_100(st.session_state.custom_weights_sliders)
                st.session_state.persona_active = selected_profile["display_name"]
                
                # Advance to next step
                st.session_state.step = 3
                st.rerun()