import streamlit as st
from modules.about_page import render_about_page

st.set_page_config(
    page_title="About Page Test",
    page_icon="ℹ️",
    layout="wide"
)

render_about_page()
