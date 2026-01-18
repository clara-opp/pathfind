# ============================================================
# LOGIN PAGE - With Streamlit Secrets / Environment Variables
# Add this to the TOP of your main app (travel_planner.py)
# ============================================================

import streamlit as st
import hashlib
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================
load_dotenv()

def get_valid_credentials():
    # Try Streamlit secrets first
    try:
        if "credentials" in st.secrets:
            users = st.secrets.credentials.get("users", {})
            if users:
                return users
    except Exception:
        pass
    
    # Fallback to environment variables
    credentials = {}
    for key, value in os.environ.items():
        if key.startswith("LOGIN_"):
            username = key.replace("LOGIN_", "").lower()
            credentials[username] = value
    
    if credentials:
        return credentials


def init_auth_session():
    """Initialize authentication session state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "login_time" not in st.session_state:
        st.session_state.login_time = None


def is_session_valid():
    """Check if session is still valid (24h timeout)"""
    if not st.session_state.authenticated:
        return False
    
    if st.session_state.login_time is None:
        return False
    
    elapsed = datetime.now() - st.session_state.login_time
    timeout = timedelta(hours=24)
    
    if elapsed > timeout:
        st.session_state.authenticated = False
        st.session_state.username = None
        return False
    
    return True


def render_login_page():
    """Render beautiful login page with glassmorphism"""

    
    # CSS for glassmorphism design
    st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            width: 100%;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 3rem 2rem;
            width: 100%;
            max-width: 380px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        
        .login-header h1 {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #1f6e8a 0%, #0d47a1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: #555;
            font-size: 0.95rem;
            font-weight: 500;
        }
        
        .login-form {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .login-input {
            width: 100%;
            padding: 0.875rem 1rem;
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.8);
            font-size: 0.95rem;
            transition: all 0.3s ease;
        }
        
        .login-input:focus {
            outline: none;
            border-color: #1f6e8a;
            box-shadow: 0 0 0 3px rgba(31, 110, 138, 0.1);
        }
        
        .login-button {
            width: 100%;
            padding: 0.875rem 1rem;
            background: linear-gradient(135deg, #1f6e8a 0%, #0d47a1 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .login-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(31, 110, 138, 0.4);
        }
        
        .login-footer {
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.85rem;
        }
        
        .login-footer code {
            background: rgba(0, 0, 0, 0.05);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: monospace;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Center columns
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # Header
        
        # Login form
        with st.form("login_form", border=False):
            st.markdown("""
            <style>
                .stForm {
                    background: rgba(255, 255, 255, 0.15) !important;
                    backdrop-filter: blur(10px) !important;
                    border-radius: 16px !important;
                    padding: 2rem !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )
            
            col_login, col_space = st.columns([1, 0.3])
            
            with col_login:
                submit = st.form_submit_button(
                    "🔓 Login",
                    use_container_width=True,
                    type="primary"
                )
            
            if submit:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                else:
                    valid_creds = get_valid_credentials()
                    
                    if username.lower() in valid_creds:
                        stored_password = valid_creds[username.lower()]
                        
                        if password == stored_password:
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.login_time = datetime.now()
                            st.success(f"✅ Welcome back, {username}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Incorrect password")
                    else:
                        st.error("❌ Username not found")
        


def require_login():
    """
    Protect entire app - call at the VERY START of main app
    """
    init_auth_session()
    
    if not st.session_state.authenticated or not is_session_valid():
        render_login_page()
        st.stop()


def logout():
    """Logout function"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.login_time = None
    st.rerun()


def render_logout_button():
    """Render logout button in sidebar"""
    with st.sidebar:
        st.divider()
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption(f"👤 {st.session_state.username}")
        with col2:
            if st.button("🔓", help="Logout", use_container_width=True):
                logout()
